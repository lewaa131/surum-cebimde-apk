from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
from kivy.utils import platform
from kivy.metrics import dp
from backup_store import create_backup, read_backup, restore_backup, SETTINGS


def preferences(app):
    return dict(zip(SETTINGS,(app.farm,app.cycle,app.reminder_settings)))


def open_backups(app):
    from main import button, paragraph
    popup,body,error,actions=app.dialog('Yedekleme')
    body.add_widget(paragraph('Hayvanların, fotoğrafların ve ayarların tek dosyada.'))
    body.add_widget(paragraph('Telefon değişimi için yedeğin bir kopyasını Drive’da veya bilgisayarda sakla.'))
    def export_existing(path):
        choose(app,lambda _:app.notice('Yedek seçtiğin konuma kaydedildi.'),source=path)
    def backup(*_):
        try: path=create_backup(app.herd,Path(app.user_data_dir)/'backups',preferences(app))
        except Exception:
            app.notice('Yedek oluşturulamadı. Boş alanı ve hayvan fotoğraflarını kontrol et.'); return
        export_existing(path)
    def last_backup(*_):
        files=sorted((Path(app.user_data_dir)/'backups').glob('Surum-*.zip'),key=lambda p:p.stat().st_mtime)
        if not files: app.notice('Henüz yerel yedek yok.'); return
        export_existing(files[-1])
    body.add_widget(button('Yedek oluştur ve kaydet',backup))
    body.add_widget(button('Yedekten geri yükle',lambda *_:choose(app,lambda path:confirm_restore(app,path)),variant='secondary'))
    body.add_widget(button('Son yerel yedeği dışarı kaydet',last_backup,variant='secondary'))


def choose(app,on_file,source=None):
    if platform=='android':
        from backup_document import BackupDocument
        if not hasattr(app,'backup_picker'): app.backup_picker=BackupDocument(Path(app.user_data_dir)/'backup-cache')
        app.backup_picker.open(on_file,app.notice,source)
        return
    from main import button
    from kivy.uix.filechooser import FileChooserListView
    popup,body,error,actions=app.dialog('Yedeği kaydet' if source else 'Yedek seç')
    chooser=FileChooserListView(path=str(Path.home()),dirselect=bool(source),
        filters=[] if source else ['*.zip'],size_hint_y=None,height=dp(360))
    body.add_widget(chooser)
    def selected(*_):
        try:
            if source:
                folder=Path(chooser.selection[0]) if chooser.selection else Path(chooser.path)
                if not folder.is_dir(): raise ValueError('Bir klasör seç.')
                target=folder/Path(source).name
                if target.resolve()!=Path(source).resolve():
                    if target.exists(): raise ValueError('Bu konumda aynı adlı yedek var.')
                    shutil.copyfile(source,target)
                path=str(target)
            else:
                if not chooser.selection: raise ValueError('Bir yedek seç.')
                path=chooser.selection[0]
        except Exception as exc: error.text=str(exc); return
        popup.dismiss(); on_file(path)
    actions.add_widget(button('Bu klasöre kaydet' if source else 'Yedeği kontrol et',selected))


def confirm_restore(app,path):
    from main import button, paragraph
    try:
        with TemporaryDirectory(dir=app.user_data_dir) as stage: info=read_backup(path,stage)
    except Exception:
        app.notice('Yedek okunamadı veya uyumsuz. Mevcut kayıtların değiştirilmedi.'); return
    popup,body,error,actions=app.dialog('Yedeği geri yükle?')
    body.add_widget(paragraph(f'{info["animals"]} hayvan · {info["created"][:19].replace("T"," ")}'))
    body.add_widget(paragraph('Bu yedek mevcut hayvanların ve ayarların yerine geçecek; kayıtlar birleştirilmez.'))
    body.add_widget(paragraph('Devam etmeden önce mevcut kayıtların ayrıca yedeklenir.'))
    def restore(*_):
        try:
            safety,restored=restore_backup(app.herd,app.user_data_dir,path,preferences(app))
        except Exception:
            error.text='Geri yükleme tamamlanamadı. Boş alanı ve yedeği kontrol et.'; return
        app.farm=restored['preferences'][SETTINGS[0]]
        app.cycle=restored['preferences'][SETTINGS[1]]
        app.reminder_settings=restored['preferences'][SETTINGS[2]]
        app.query=''; app.selection='Tüm hayvanlar'
        popup.dismiss(); app.open_tab('herd'); app.sync_reminders(force=True)
        app.notice('Yedek yüklendi. Önceki kayıtların yerel yedeği de saklandı; Yedekleme’den dışarı kaydedebilirsin.')
    actions.add_widget(button('Evet, geri yükle',restore))
