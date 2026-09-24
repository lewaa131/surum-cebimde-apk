"""Download in the background; Android always owns installation consent."""
from threading import Thread, Event
from kivy.clock import Clock
from kivy.utils import platform
from mobile_ui import big_button
from settings_ui import text
from update_service import check, download


def check_on_start(app):
    if platform!='android' or app.closed: return
    def worker():
        try: result=check(app.version)
        except Exception: return  # Offline startup must remain usable.
        def ready(*_):
            if result and not app.closed and not app.editor:
                open_updates(app,result)
        Clock.schedule_once(ready,0)
    Thread(target=worker,daemon=True).start()


def open_updates(app,available=None):
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
    if available: found(available)
    else: start_check()
