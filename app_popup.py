"""All dialogs share the same theme and Android back behavior."""
from kivy.app import App
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock


class AppPopup(Popup):
    def open(self, *args, **kwargs):
        kwargs.setdefault('animation', False)
        return super().open(*args, **kwargs)

    def dismiss(self, *args, **kwargs):
        kwargs.setdefault('animation', False)
        # Remove only after the current input dispatch finishes, so the same
        # finger cannot release onto a newly exposed button.
        if getattr(self,'_closing',False): return
        self._closing=True
        Clock.schedule_once(lambda _:self._finish_dismiss(args,kwargs),0)

    def _finish_dismiss(self,args,kwargs):
        super().dismiss(*args,**kwargs)
        self._closing=False

    def fit_keyboard(self):
        app=App.get_running_app()
        inset=getattr(app,'keyboard_inset',0)
        if not hasattr(self,'_normal_height'):
            self._normal_height=self.height
            self._normal_hint=self.size_hint_y
        self.size_hint_y=None
        normal=Window.height*self._normal_hint if self._normal_hint else self._normal_height
        self.height=min(normal,max(120,(Window.height-inset)*.94))
        self._align_center()
        Clock.schedule_once(self.reveal_field,.05)

    def reveal_field(self,*_):
        from kivy.uix.textinput import TextInput
        from kivy.uix.scrollview import ScrollView
        for field in self.walk():
            if isinstance(field,TextInput) and field.focus:
                parent=field.parent
                while parent is not None and parent is not self:
                    if isinstance(parent,ScrollView):
                        parent.scroll_to(field,padding=12,animate=False)
                        return
                    parent=parent.parent

    def _align_center(self,*args):
        if not self._is_open: return
        inset=getattr(App.get_running_app(),'keyboard_inset',0)
        self.center=(Window.width/2,(Window.height+inset)/2)

    def __init__(self, **kwargs):
        kwargs.setdefault('background', '')
        kwargs.setdefault('background_color', (.94, .98, .95, 1))
        kwargs.setdefault('title_color', (.05, .28, .19, 1))
        kwargs.setdefault('separator_color', (.10, .48, .32, 1))
        kwargs.setdefault('auto_dismiss', False)
        super().__init__(**kwargs)

    def on_open(self):
        app = App.get_running_app()
        if app:
            app.popup_stack.append(self)
            self.fit_keyboard()

    def on_dismiss(self):
        app = App.get_running_app()
        if app and self in app.popup_stack:
            app.popup_stack.remove(self)
        for widget in self.walk():
            if hasattr(widget, 'focus'): widget.focus = False

    def _handle_keyboard(self, window, key, *args):
        if key in (27, 1001):
            App.get_running_app().go_back()
            return True
        return super()._handle_keyboard(window, key, *args)
