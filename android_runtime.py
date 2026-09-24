"""Small retained bridge between the Android UI thread and Kivy's event loop."""
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method


class BackAction(PythonJavaClass):
    __javainterfaces__ = ['java/lang/Runnable']
    __javacontext__ = 'app'

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.host = autoclass('org.kivy.android.PythonActivity').mActivity

    @java_method('()V')
    def run(self):
        Clock.schedule_once(self.dispatch)

    def dispatch(self, *_):
        if not self.app.go_back():
            autoclass('org.surutakip.mobile.BackNavigation').background(self.host)

    def notification_intent(self, intent):
        if intent and intent.getBooleanExtra('surum_open_today', False):
            intent.removeExtra('surum_open_today')
            Clock.schedule_once(self.open_today)

    def open_today(self, *_):
        for popup in list(self.app.popup_stack):
            popup.dismiss()
        self.app.open_tab('today')


def install(app):
    bridge = BackAction(app)
    autoclass('org.surutakip.mobile.SafeArea').install(bridge.host)
    autoclass('org.surutakip.mobile.BackNavigation').install(bridge.host, bridge)
    from android import activity
    activity.bind(on_new_intent=bridge.notification_intent)
    bridge.notification_intent(bridge.host.getIntent())
    return bridge
