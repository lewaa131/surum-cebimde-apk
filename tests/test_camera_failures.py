import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch


class CameraFailures(TestCase):
    def run_case(self,missing=False,revoke_error=False,cancel=False):
        modules={'kivy':Mock(),'kivy.clock':Mock(),'kivy.logger':Mock(),'android':SimpleNamespace(activity=Mock())}
        with patch.dict('sys.modules',modules),TemporaryDirectory() as folder:
            spec=importlib.util.spec_from_file_location('camera_under_test',Path(__file__).resolve().parents[1]/'android_camera.py')
            module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            camera=module.AndroidCamera()
            camera.busy=True
            camera.host=Mock()
            if revoke_error: camera.host.revokeUriPermission.side_effect=RuntimeError('revocation failed')
            camera.path=Path(folder)/'photo.jpg'
            if not missing: camera.path.write_bytes(b'photo')
            camera.uri=Mock()
            camera.on_file=Mock(); camera.on_error=Mock()
            camera.finish(not cancel)
            self.assertFalse(camera.busy)
            self.assertFalse(camera.path.exists())
            modules['android'].activity.unbind.assert_called_once()
            return camera

    def test_missing_capture_reports_error_without_crash(self):
        camera=self.run_case(missing=True)
        camera.on_error.assert_called_once()
        camera.on_file.assert_not_called()

    def test_permission_cleanup_failure_still_deletes_temporary_photo(self):
        camera=self.run_case(revoke_error=True)
        camera.on_file.assert_called_once()
        camera.on_error.assert_not_called()

    def test_cancel_does_not_replace_photo(self):
        camera=self.run_case(cancel=True)
        camera.on_file.assert_not_called()
        camera.on_error.assert_not_called()
