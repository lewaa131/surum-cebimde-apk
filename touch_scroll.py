"""Retain drag ownership on cards; preserve text selection in input fields."""
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock


class TouchScrollView(ScrollView):
    def _gesture_key(self):
        return 'surum.drag.'+str(self.uid)

    def on_touch_down(self,touch):
        if not self.collide_point(*touch.pos) or self.disabled:
            return super().on_touch_down(touch)
        if not self.do_scroll_y or (getattr(touch,'button','') or '').startswith('scroll'):
            return super().on_touch_down(touch)
        if getattr(self,'_direct_touch',None) is not None:
            touch.ud[self._gesture_key()]=dict(ended=True)
            return True
        # Text fields keep Kivy's keyboard, cursor and selection handling.
        x,y=touch.sx*Window.width,touch.sy*Window.height
        search_touch=False
        if self._viewport:
            for widget in self._viewport.walk():
                if isinstance(widget,TextInput):
                    left,bottom=widget.to_window(*widget.pos)
                    right,top=widget.to_window(widget.right,widget.top)
                    if left<=x<=right and bottom<=y<=top:
                        if getattr(widget,'drag_to_scroll',False): search_touch=True
                        else: return super().on_touch_down(touch)
        if self._touch:
            return super().on_touch_down(touch)
        self._direct_touch=touch
        touch.ud[self._gesture_key()]=dict(x=x,y=y,scroll=self.scroll_y,moved=False,ended=False,
            search=search_touch,started=Clock.get_time())
        if self.effect_y:
            self.effect_y.cancel()
            self.effect_y.velocity=0
            self._update_effect_y_bounds()
            self.effect_y.trigger_velocity_update.cancel()
        touch.grab(self)
        return True

    def on_touch_move(self,touch):
        gesture=touch.ud.get(self._gesture_key())
        if gesture is None: return super().on_touch_move(touch)
        if gesture['ended']: return True
        distance=touch.sy*Window.height-gesture['y']
        if max(abs(distance),abs(touch.sx*Window.width-gesture['x']))>dp(8): gesture['moved']=True
        if gesture['moved'] and self._viewport:
            travel=self._viewport.height-self.height
            if travel>0:
                self.scroll_y=max(0,min(1,gesture['scroll']-distance/travel))
                if self.effect_y:
                    self.effect_y.velocity=0
                    self._update_effect_y_bounds()
                    self.effect_y.trigger_velocity_update.cancel()
        return True

    def on_touch_up(self,touch):
        gesture=touch.ud.get(self._gesture_key())
        if gesture is None: return super().on_touch_up(touch)
        if gesture['ended']: return True
        # Some Android providers batch motion; include the final position.
        self.on_touch_move(touch)
        if gesture['search'] and Clock.get_time()-gesture['started']>=.45:
            gesture['moved']=True
        gesture['ended']=True
        self._direct_touch=None
        touch.ungrab(self)
        if self.parent and not gesture['moved'] and self.collide_point(*touch.pos):
            self.simulate_touch_down(touch)
            Clock.schedule_once(lambda _:self._do_touch_up(touch),0)
        return True

    def cancel_gesture(self):
        touch=getattr(self,'_direct_touch',None)
        if touch is not None:
            touch.ud[self._gesture_key()]['ended']=True
            touch.ungrab(self)
            self._direct_touch=None

    def _change_touch_mode(self, *args):
        touch = self._touch
        if touch and self._viewport is not None:
            # A card includes labels, drawings and empty space. Do not hand
            # its touch to a child after the timeout: that child would grab
            # the finger and prevent a later drag. Ordinary taps are still
            # delivered by ScrollView.on_scroll_stop after finger release.
            for widget in self._viewport.walk():
                if isinstance(widget, TextInput) and widget.collide_point(*widget.to_widget(*touch.pos)):
                    return super()._change_touch_mode(*args)
            return
        return super()._change_touch_mode(*args)
