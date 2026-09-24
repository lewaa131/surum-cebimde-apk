"""Dokunmatik ekran için geniş kontroller ve hayvan kimliği."""
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse
from kivy.uix.widget import Widget
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import BooleanProperty

GREEN=(.06,.42,.27,1)
INK=(.05,.25,.17,1)
MUTED=(.40,.47,.44,1)


class GreenSwitch(Button):
    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (.45, None))
        kwargs.setdefault('height', dp(44))
        kwargs.setdefault('pos_hint', {'center_y': .5})
        super().__init__(background_normal='',background_down='',
                         background_color=(0,0,0,0),font_size=sp(14),bold=True,**kwargs)
        self.tint = surface(self, GREEN, 22)
        self.bind(active=self.repaint,on_release=self.toggle)
        self.repaint()

    def toggle(self, *_):
        self.active = not self.active

    def repaint(self, *_):
        self.text = 'Evet' if self.active else 'Hayır'
        self.color = (1,1,1,1) if self.active else GREEN
        self.tint.rgba = GREEN if self.active else (.84,.93,.87,1)

def surface(widget,color,radius=18):
    with widget.canvas.before:
        tint=Color(*color)
        shape=RoundedRectangle(pos=widget.pos,size=widget.size,radius=[dp(radius)])
    widget.bind(pos=lambda w,p:setattr(shape,'pos',p),size=lambda w,s:setattr(shape,'size',s))
    return tint

def big_button(text,action,height=56,variant='primary'):
    colors={'primary':GREEN,'secondary':(.86,.94,.88,1),'danger':(.98,.89,.88,1)}
    base=colors[variant]
    w=Button(text=text,size_hint_y=None,height=dp(max(48,height)),font_size=sp(16),
             bold=True,background_normal='',background_down='',background_color=(0,0,0,0))
    w.color=(1,1,1,1) if variant=='primary' else ((.68,.16,.14,1) if variant=='danger' else GREEN)
    tint=surface(w,base,14)
    def repaint(*_):
        factor=.86 if w.state=='down' else 1
        tint.rgba=tuple(c*factor for c in base[:3])+( .4 if w.disabled else 1,)
    w.bind(state=repaint,disabled=repaint)
    w.bind(size=lambda w,s:setattr(w,'text_size',(max(1,s[0]-dp(24)),None)))
    w.halign='center'
    w.bind(on_release=action)
    return w

class Identity(BoxLayout):
    """İsim ve küpe ayrı sütunlardır; uzun isim küpeyi yerinden çıkarmaz."""
    def __init__(self,cow,**kwargs):
        super().__init__(orientation='vertical',spacing=dp(4),size_hint_y=None,**kwargs)
        self.name_label=Label(text=cow.get('name','').strip() or 'Hayvanım',color=INK,bold=True,
                              font_size=sp(18),size_hint_y=None,halign='left',valign='middle')
        self.tag_label=Label(text=cow['tag'],color=MUTED,font_size=sp(14),
                             size_hint_y=None,halign='left',valign='middle')
        for item in (self.name_label,self.tag_label):
            item.bind(width=lambda w,v:setattr(w,'text_size',(max(1,v),None)))
            item.bind(texture_size=self.fit)
            self.add_widget(item)
        self.height=dp(56)
    def fit(self,*_):
        for item in (self.name_label,self.tag_label):
            item.height=max(dp(22),item.texture_size[1])
        self.height=self.name_label.height+self.tag_label.height+dp(4)

class AnimalCard(ButtonBehavior,BoxLayout):
    def __init__(self,cow,portrait,description,action,**kwargs):
        super().__init__(orientation='vertical',spacing=dp(8),padding=dp(14),size_hint_y=None,**kwargs)
        surface(self,(1,1,1,1))
        self.bind(minimum_height=self.setter('height'))
        self.add_widget(Identity(cow))
        row=BoxLayout(size_hint_y=None,height=dp(66),spacing=dp(14))
        if portrait is not None:
            portrait.size_hint_x=.24
            row.add_widget(portrait)
        info=Label(text=description,color=INK,font_size=sp(13),halign='left',valign='middle')
        info.bind(size=lambda w,s:setattr(w,'text_size',(s[0],None)))
        info.bind(texture_size=lambda w,s:setattr(row,'height',max(dp(66),s[1]+dp(12))))
        row.add_widget(info); self.add_widget(row)
        self.bind(on_release=action)


class NavIcon(Widget):
    def __init__(self,kind,tint=GREEN,**kwargs):
        super().__init__(**kwargs)
        self.kind = kind
        self.icon_tint = tint
        self.bind(pos=self.draw,size=self.draw)

    def draw(self,*_):
        self.canvas.clear()
        size = min(self.width,self.height,dp(30))
        x,y = self.center_x-size/2,self.center_y-size/2
        def line(points,close=False):
            Line(points=[v for px,py in points for v in (x+px*size,y+py*size)],width=dp(1.4),close=close)
        with self.canvas:
            Color(*self.icon_tint)
            if self.kind in ('herd','birth'):
                line([(.25,.7),(.25,.3),(.4,.15),(.6,.15),(.75,.3),(.75,.7)],True)
                line([(.25,.65),(.05,.85),(.2,.85),(.35,.7)])
                line([(.75,.65),(.95,.85),(.8,.85),(.65,.7)])
                for px in (.38,.58): Ellipse(pos=(x+px*size,y+.49*size),size=(size*.06,size*.06))
                line([(.35,.3),(.65,.3)])
                if self.kind=='birth':
                    line([(.5,.78),(.5,1)])
                    line([(.4,.9),(.6,.9)])
            elif self.kind=='milk':
                line([(.3,.15),(.7,.15),(.75,.63),(.25,.63)],True)
                line([(.35,.63),(.35,.85),(.65,.85),(.65,.63)])
                line([(.35,.48),(.65,.48)])
            elif self.kind in ('dry','seed'):
                Line(circle=(x+.5*size,y+.5*size,.34*size),width=dp(1.4))
                if self.kind=='dry':
                    line([(.43,.32),(.43,.68)]); line([(.57,.32),(.57,.68)])
                else:
                    line([(.5,.22),(.5,.62),(.3,.75)])
                    line([(.5,.49),(.7,.68)])
            elif self.kind=='today':
                line([(.15,.15),(.85,.15),(.85,.8),(.15,.8)],True)
                line([(.15,.65),(.85,.65)])
                line([(.3,.72),(.3,.95)]); line([(.7,.72),(.7,.95)])
                line([(.3,.4),(.45,.25),(.7,.55)])
            elif self.kind=='special':
                line([(.5,.95),(.05,.1),(.95,.1)],True)
                line([(.5,.65),(.5,.4)])
                Ellipse(pos=(x+.47*size,y+.23*size),size=(.06*size,.06*size))
            else:
                line([(.15,.15),(.85,.15),(.85,.65),(.15,.65)],True)
                line([(.1,.65),(.9,.65),(.9,.85),(.1,.85)],True)
                line([(.4,.5),(.6,.5)])


class NavButton(ButtonBehavior,BoxLayout):
    def __init__(self,kind,title,action,**kwargs):
        super().__init__(orientation='vertical',padding=dp(4),spacing=dp(2),**kwargs)
        self.tint = surface(self,(1,1,1,1),12)
        self.add_widget(NavIcon(kind))
        self.add_widget(Label(text=title,color=GREEN,font_size=sp(11),size_hint_y=None,height=dp(18)))
        self.bind(on_release=action)

    def select(self,active):
        self.tint.rgba = (.84,.93,.87,1) if active else (1,1,1,1)


PALETTES = {
    'blue': ((.85,.94,.88,1),(.07,.40,.25,1)),
    'mint': ((.86,.96,.92,1),(.06,.48,.36,1)),
    'coral': ((.91,.95,.80,1),(.30,.42,.12,1)),
    'violet': ((.82,.93,.89,1),(.04,.39,.32,1)),
}

class MetricCard(ButtonBehavior, BoxLayout):
    """Compact counters with a quiet surface and colored icon badge."""
    def __init__(self,title,value,kind,tone,action,**kwargs):
        super().__init__(orientation='vertical',padding=dp(10),spacing=dp(4),
                         size_hint_y=None,height=dp(114),**kwargs)
        bg,fg=PALETTES[tone]
        tint=surface(self,(1,1,1,1),18)
        top=BoxLayout(spacing=dp(4))
        self.value=Label(text=str(value),bold=True,color=INK,font_size=sp(27),halign='left')
        self.value.bind(size=lambda w,s:setattr(w,'text_size',s))
        top.add_widget(self.value)
        badge=BoxLayout(size_hint=(None,None),size=(dp(30),dp(32)),padding=dp(5),pos_hint={'center_y':.5})
        surface(badge,bg,10)
        badge.add_widget(NavIcon(kind,tint=fg))
        top.add_widget(badge)
        self.add_widget(top)
        caption=Label(text=title,color=MUTED,font_size=sp(12),size_hint_y=None,height=dp(36),halign='left',valign='middle')
        caption.bind(size=lambda w,s:setattr(w,'text_size',s))
        self.add_widget(caption)
        self.bind(state=lambda w,state:setattr(tint,'rgba',bg if state=='down' else (1,1,1,1)))
        self.bind(on_release=action)
