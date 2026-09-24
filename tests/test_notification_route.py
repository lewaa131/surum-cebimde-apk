import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class NotificationRouteTest(unittest.TestCase):
    def test_notification_opens_today_once_and_closes_overlay(self):
        queued=[]
        clock=SimpleNamespace(schedule_once=lambda callback:queued.append(callback))
        jnius=SimpleNamespace(autoclass=Mock(),PythonJavaClass=object,
                              java_method=lambda *_:lambda f:f)
        spec=importlib.util.spec_from_file_location('route_under_test',Path(__file__).resolve().parents[1]/'android_runtime.py')
        module=importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules',{'kivy.clock':SimpleNamespace(Clock=clock),'jnius':jnius}):
            spec.loader.exec_module(module)
        bridge=object.__new__(module.BackAction)
        popup=Mock()
        bridge.app=SimpleNamespace(popup_stack=[popup],open_tab=Mock())
        extras={'surum_open_today':True}
        intent=SimpleNamespace(getBooleanExtra=lambda key,default:extras.get(key,default),
                               removeExtra=lambda key:extras.pop(key,None))
        bridge.notification_intent(intent)
        bridge.notification_intent(intent)
        self.assertEqual(len(queued),1)
        queued[0]()
        popup.dismiss.assert_called_once()
        bridge.app.open_tab.assert_called_once_with('today')
        bridge.notification_intent(None)
        self.assertEqual(len(queued),1)


if __name__=='__main__': unittest.main()
