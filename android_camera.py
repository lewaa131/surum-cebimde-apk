"""Use the device's full-screen camera and preserve EXIF orientation."""
from pathlib import Path
from uuid import uuid4
from kivy.clock import Clock
from kivy.logger import Logger


class AndroidCamera:
    REQUEST = 4808

    def __init__(self):
        self.busy = False

    def open(self, on_file, on_error):
        if self.busy: return
        from android import activity
        from android.runnable import run_on_ui_thread
        from jnius import autoclass, cast
        self.host = autoclass('org.kivy.android.PythonActivity').mActivity
        self.path = Path(str(self.host.getCacheDir().getAbsolutePath()))/'captures'/f'{uuid4().hex}.jpg'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch()
        self.uri = autoclass('android.net.Uri').parse('content://' + str(self.host.getPackageName()) + '.camera/' + self.path.name)
        self.on_file, self.on_error = on_file, on_error
        self.busy = True
        activity.bind(on_activity_result=self.result)

        @run_on_ui_thread
        def launch():
            try:
                Intent = autoclass('android.content.Intent')
                intent = Intent('android.media.action.IMAGE_CAPTURE')
                intent.putExtra('output', cast('android.os.Parcelable', self.uri))
                intent.addFlags(3)  # temporary read/write grants, also on ClipData for OEM cameras
                intent.setClipData(autoclass('android.content.ClipData').newRawUri('photo', self.uri))
                self.host.startActivityForResult(intent, self.REQUEST)
            except Exception:
                Clock.schedule_once(lambda _:self.finish(False, 'Kamera açılamadı. Galeriden fotoğraf seçebilirsin.'))
        launch()

    def result(self, request, result, intent):
        if request == self.REQUEST:
            Clock.schedule_once(lambda _:self.finish(result == -1))

    def finish(self, success, message=None):
        if not self.busy: return
        from android import activity
        activity.unbind(on_activity_result=self.result)
        self.busy = False
        try:
            if success:
                if self.path.stat().st_size:
                    self.on_file(str(self.path))
                else: message = 'Fotoğraf kaydedilemedi. Tekrar çek.'
        except Exception:
            Logger.exception('Surum: Kamera fotoğrafı alınamadı')
            message = 'Fotoğraf alınamadı. Tekrar çek veya galeriden seç.'
        finally:
            try: self.host.revokeUriPermission(self.uri, 3)
            except Exception: Logger.exception('Surum: Geçici kamera izni kaldırılamadı')
            try: self.path.unlink(missing_ok=True)
            except OSError: Logger.exception('Surum: Geçici kamera dosyası temizlenemedi')
        if message: self.on_error(message)
