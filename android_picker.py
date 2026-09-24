"""Android sistem seçicisi: yalnızca kullanıcının seçtiği fotoğrafa erişir."""
from pathlib import Path
from uuid import uuid4
from threading import Thread
from kivy.clock import Clock

class AndroidPicker:
    REQUEST = 4807

    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.busy = False

    def open(self, on_file, on_error):
        if self.busy:
            return
        from android import activity
        from android.runnable import run_on_ui_thread
        from jnius import autoclass
        self.on_file, self.on_error = on_file, on_error
        self.busy = True
        activity.bind(on_activity_result=self.result)
        @run_on_ui_thread
        def start():
            try:
                Intent = autoclass('android.content.Intent')
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.setType('image/*')
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                autoclass('org.kivy.android.PythonActivity').mActivity.startActivityForResult(intent,self.REQUEST)
            except Exception:
                activity.unbind(on_activity_result=self.result)
                self.busy = False
                Clock.schedule_once(lambda _: on_error('Fotoğraf seçici açılamadı.'))
        start()

    def result(self, request, result, intent):
        if request != self.REQUEST:
            return
        from android import activity
        activity.unbind(on_activity_result=self.result)
        self.busy = False
        if result != -1 or intent is None:
            return
        uri = intent.getData()
        if uri is None:
            return
        on_file, on_error = self.on_file, self.on_error
        def copy():
            from jnius import autoclass
            self.cache_dir.mkdir(parents=True,exist_ok=True)
            target = self.cache_dir/(uuid4().hex+'.image')
            source = output = channel = None
            try:
                resolver = autoclass('org.kivy.android.PythonActivity').mActivity.getContentResolver()
                source = resolver.openInputStream(uri)
                output = autoclass('java.io.FileOutputStream')(str(target))
                channel = autoclass('java.nio.channels.Channels').newChannel(source)
                file_channel = output.getChannel()
                total = 0
                while True:
                    count = file_channel.transferFrom(channel,total,1024*1024)
                    if count <= 0: break
                    total += count
                    if total > 30*1024*1024: raise ValueError('Fotoğraf çok büyük.')
                output.close(); output = None
                Clock.schedule_once(lambda _: on_file(str(target)))
            except Exception:
                target.unlink(missing_ok=True)
                Clock.schedule_once(lambda _: on_error('Seçilen fotoğraf okunamadı. JPG veya PNG deneyin.'))
            finally:
                if channel is not None: channel.close()
                if source is not None: source.close()
                if output is not None: output.close()
        Thread(target=copy,daemon=True).start()
