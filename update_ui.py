"""Download in the background; Android always owns installation consent."""
from threading import Thread, Event
from kivy.clock import Clock
from kivy.utils import platform
from mobile_ui import big_button
from settings_ui import text
from update_service import check, download
from update_prompt import should_offer, remind_later
import time


def native_updates():
    from jnius import autoclass
    return (autoclass('org.surutakip.mobile.UpdateJob'),
            autoclass('org.kivy.android.PythonActivity').mActivity)


def schedule_background():
    if platform!='android': return
    try:
        bridge,activity=native_updates()
        bridge.schedule(activity)
    except Exception:
        from kivy.logger import Logger
        Logger.exception('Surum: Arka plan güncelleme kontrolü planlanamadı')


def offer_pending(app,*_):
    app.update_offer_event=None
    result=getattr(app,'pending_update',None)
    if app.closed or not result: return
    if platform=='android':
        try:
            bridge,activity=native_updates()
            if bridge.deferred(activity,result['version']):
                app.pending_update=None
                return
        except Exception: pass
    if not should_offer(app.user_data_dir,result['version']):
        app.pending_update=None
        return
    if getattr(app,'backgrounded',False): return
    if app.editor or app.popup_stack or getattr(app,'update_busy',False):
        app.update_offer_event=Clock.schedule_once(lambda _:offer_pending(app),15)
        return
    app.pending_update=None
    popup,body,error,actions=app.dialog('Yeni sürüm var')
    body.add_widget(text(f'Sürüm {result["version"]} hazır. Şimdi güncellemek ister misin?'))
    body.add_widget(text('Daha sonra seçersen yarın tekrar hatırlatılır.',13))
    # app.dialog already supplies one dismissal button; reuse it.
    later=actions.children[0]
    later.text='Daha sonra'
    accepted=False
    def dismissed(*_):
        if not accepted:
            try: remind_later(app.user_data_dir,result['version'])
            except OSError: pass
            if platform=='android':
                try:
                    bridge,activity=native_updates()
                    bridge.defer(activity,result['version'])
                except Exception: pass
    popup.bind(on_dismiss=dismissed)
    def accept(*_):
        nonlocal accepted
        if accepted: return
        accepted=True
        popup.dismiss()
        Clock.schedule_once(lambda _:open_updates(app,result,start_immediately=True) if not app.closed else None,.1)
    actions.add_widget(big_button('Güncelle',accept,48))
    return popup


def check_on_start(app):
    if platform!='android' or app.closed or getattr(app,'backgrounded',False): return
    if getattr(app,'pending_update',None) and not getattr(app,'update_offer_event',None): offer_pending(app)
    if getattr(app,'update_check_busy',False) or time.monotonic()<getattr(app,'update_check_after',0): return
    app.update_check_busy=True
    app.update_check_after=time.monotonic()+3600
    def worker():
        try: result=check(app.version)
        except Exception:
            app.update_check_after=time.monotonic()+60
            return  # Retry soon after connectivity returns.
        finally: app.update_check_busy=False
        def ready(*_):
            if result and not app.closed:
                app.pending_update=result
                if not getattr(app,'update_offer_event',None): offer_pending(app)
        Clock.schedule_once(ready,0)
    Thread(target=worker,daemon=True).start()


def open_updates(app,available=None,start_immediately=False):
    if getattr(app,'update_busy',False):
        app.notice('Önceki indirme kapanıyor; biraz sonra tekrar dene.'); return
    popup,body,error,actions=app.dialog('Uygulama güncellemesi')
    body.add_widget(text('Yüklü sürüm · '+app.version))
    status=text('Güncellemeler kontrol ediliyor…'); body.add_widget(status)
    cancel=Event(); popup.bind(on_dismiss=lambda *_:cancel.set())
    alive=lambda:not app.closed and not cancel.is_set() and not getattr(popup,'_closing',False)
    def deliver(callback,*args):
        Clock.schedule_once(lambda _:callback(*args) if alive() else None,0)
    def failed(message):
        status.text=message
        control.text='Tekrar kontrol et'; control.disabled=False
        control.unbind(on_release=install)
        control.unbind(on_release=start_download)
        control.unbind(on_release=start_check)
        control.bind(on_release=start_check)
    data=None; apk=None
    def install(*_):
        try:
            from jnius import autoclass
            activity=autoclass('org.kivy.android.PythonActivity').mActivity
            bridge=autoclass('org.surutakip.mobile.UpdateInstaller')
            message=bridge.install(activity,str(apk))
            status.text=str(message)
        except Exception:
            status.text='Kurulum ekranı açılamadı. Yeniden dene.'
    def downloaded(path):
        nonlocal apk
        apk=path
        control.unbind(on_release=start_download)
        control.bind(on_release=install)
        control.text='Kurulumu aç'; control.disabled=False
        status.text='İndirme tamamlandı. Android kurulumunu onayla.'
        install()
    def start_download(*_):
        if getattr(app,'update_busy',False): return
        if platform!='android':
            status.text='APK kurulumu Android telefonda kullanılabilir.'; return
        app.update_busy=True; control.disabled=True
        status.text='İndiriliyor · %0'
        def worker():
            try:
                from jnius import autoclass
                activity=autoclass('org.kivy.android.PythonActivity').mActivity
                folder=str(activity.getCacheDir().getAbsolutePath())+'/updates'
                path=download(data,folder,cancel,lambda n:deliver(setattr,status,'text',f'İndiriliyor · %{n}'))
                deliver(downloaded,path)
            except Exception:
                deliver(failed,'İndirme tamamlanamadı. İnternet bağlantını kontrol edip tekrar dene.')
            finally: app.update_busy=False
        Thread(target=worker,daemon=True).start()
    def found(result):
        nonlocal data
        control.disabled=False
        if result is None:
            status.text='Daha yeni yayımlanmış sürüm bulunamadı.'; control.text='Tekrar kontrol et'; return
        data=result
        status.text=f'Yeni sürüm · {data["version"]}\nBoyut · {data["size"]/1024/1024:.1f} MB\nKayıtların korunarak güncellenir; Android kurulum için onay ister.'
        control.text='Güncelle · indir'
        control.unbind(on_release=start_check); control.bind(on_release=start_download)
    def start_check(*_):
        control.disabled=True; status.text='Güncellemeler kontrol ediliyor…'
        def worker():
            try: deliver(found,check(app.version))
            except Exception: deliver(failed,'Kontrol yapılamadı. İnternet bağlantını kontrol et.')
        Thread(target=worker,daemon=True).start()
    control=big_button('Kontrol et',start_check,48); actions.add_widget(control)
    if available:
        found(available)
        if start_immediately: start_download()
    else: start_check()
