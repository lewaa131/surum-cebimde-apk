"""Android Storage Access Framework import/export; no broad storage permission."""
from pathlib import Path
from threading import Thread
from uuid import uuid4
from kivy.clock import Clock
from backup_store import LIMIT


class BackupDocument:
    REQUEST=4810

    def __init__(self,folder):
        self.folder=Path(folder); self.busy=False

    def open(self,on_file,on_error,source=None):
        if self.busy: return
        from android import activity
        from android.runnable import run_on_ui_thread
        from jnius import autoclass
        self.busy=True; self.on_file=on_file; self.on_error=on_error; self.source=source
        activity.bind(on_activity_result=self.result)
        @run_on_ui_thread
        def launch():
            try:
                Intent=autoclass('android.content.Intent')
                intent=Intent(Intent.ACTION_CREATE_DOCUMENT if source else Intent.ACTION_OPEN_DOCUMENT)
                intent.setType('application/zip' if source else '*/*')
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                if source: intent.putExtra(Intent.EXTRA_TITLE,Path(source).name)
                autoclass('org.kivy.android.PythonActivity').mActivity.startActivityForResult(intent,self.REQUEST)
            except Exception:
                activity.unbind(on_activity_result=self.result); self.busy=False
                Clock.schedule_once(lambda _:on_error('Dosya seçici açılamadı.'))
        launch()

    def result(self,request,result,intent):
        if request!=self.REQUEST: return
        from android import activity
        activity.unbind(on_activity_result=self.result)
        if result!=-1 or intent is None or intent.getData() is None:
            self.busy=False; return
        uri=intent.getData(); export=self.source
        def copy():
            from jnius import autoclass
            opened=[]; target=None
            try:
                resolver=autoclass('org.kivy.android.PythonActivity').mActivity.getContentResolver()
                Channels=autoclass('java.nio.channels.Channels')
                if export:
                    stream=autoclass('java.io.FileInputStream')(str(export)); opened.append(stream)
                    output=resolver.openOutputStream(uri,'wt'); opened.append(output)
                    source=stream.getChannel(); sink=Channels.newChannel(output); opened.extend([source,sink])
                    total=0; length=source.size()
                    while total<length:
                        count=source.transferTo(total,min(1024*1024,length-total),sink)
                        if count<=0: raise IOError('Eksik kopyalama')
                        total+=count
                    target=str(export)
                else:
                    self.folder.mkdir(parents=True,exist_ok=True)
                    target=self.folder/(uuid4().hex+'.zip')
                    stream=resolver.openInputStream(uri); opened.append(stream)
                    output=autoclass('java.io.FileOutputStream')(str(target)); opened.append(output)
                    source=Channels.newChannel(stream); sink=output.getChannel(); opened.extend([source,sink])
                    total=0
                    while True:
                        count=sink.transferFrom(source,total,1024*1024)
                        if count<=0: break
                        total+=count
                        if total>LIMIT: raise ValueError('Yedek çok büyük')
                for handle in reversed(opened): handle.close()
                opened=[]
                Clock.schedule_once(lambda _:self.on_file(str(target)))
            except Exception:
                if not export and target: Path(target).unlink(missing_ok=True)
                Clock.schedule_once(lambda _:self.on_error('Yedek kopyalanamadı; dosyayı ve boş alanı kontrol et.'))
            finally:
                for handle in reversed(opened):
                    try: handle.close()
                    except Exception: pass
                self.busy=False
        Thread(target=copy,daemon=True).start()
