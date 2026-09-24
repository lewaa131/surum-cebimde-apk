"""Farklı silüet, yüz, boynuz ve beneklerle kod tabanlı temsili çizimler."""
import random
from kivy.graphics import Canvas, Color, Ellipse, RoundedRectangle, Line, Triangle
from kivy.uix.stencilview import StencilView
from portrait_model import portrait_traits, pattern_seed

class CowPortrait(StencilView):
    def __init__(self,cow,**kwargs):
        super().__init__(**kwargs)
        self.cow=cow
        self.art=Canvas()
        self.canvas.add(self.art)
        self.bind(pos=self.draw,size=self.draw)
        self.draw()

    def draw(self,*_):
        family,age,sex=portrait_traits(self.cow)
        rng=random.Random(pattern_seed(self.cow))
        self.art.clear()
        scale=min(self.width/400,self.height/240)
        ox=self.x+(self.width-400*scale)/2
        oy=self.y+(self.height-240*scale)/2
        calf,young=age=='calf',age=='young'
        bull=sex=='Erkek' and age=='adult'
        coat={
            'holstein':(.95,.95,.89),'red_holstein':(.94,.91,.81),'simmental':(.61,.28,.13),
            'jersey':(.76,.53,.27),'brown':(.44,.38,.31),'buffalo':(.24,.28,.30),
            'angus':(.14,.16,.17),'red_angus':(.50,.20,.12),'charolais':(.91,.87,.72),
            'limousin':(.67,.33,.12),'native_black':(.22,.23,.23),'grey':(.65,.66,.62),'generic':(.60,.57,.49)
        }[family]
        dark=tuple(v*.65 for v in coat)
        outline=(.19,.23,.20)
        # Each age has a distinct silhouette; a bull also has heavier shoulders/head.
        bw,bh=(133,67) if calf else ((175,80) if young else ((207,109) if bull else (204,88)))
        bx,by=(104,91) if calf else ((80,89) if young else (62,83))
        legw=12 if calf else (23 if bull else 15)
        hx=bx+bw-4
        hy=by+bh-(60 if bull else 44)
        hw,hh=(59,61) if calf else ((62,66) if young else ((80,82) if bull else (59,72)))
        if family=='jersey': hw-=6
        if family=='buffalo': hw+=7
        def color(c): Color(*c,1)
        def ellipse(x,y,w,h): Ellipse(pos=(ox+x*scale,oy+y*scale),size=(w*scale,h*scale))
        def rect(x,y,w,h,r=6): RoundedRectangle(pos=(ox+x*scale,oy+y*scale),size=(w*scale,h*scale),radius=[r*scale])
        def line(points,width=2): Line(points=[value for x,y in points for value in (ox+x*scale,oy+y*scale)],width=width*scale)
        def tri(points): Triangle(points=[value for x,y in points for value in (ox+x*scale,oy+y*scale)])
        with self.art:
            color((.89,.93,.87)); rect(0,0,400,240,20)
            color((.97,.93,.72)); ellipse(33,180,32,32)
            color((.82,.88,.76)); ellipse(-30,-45,470,109)
            color((.69,.78,.64)); ellipse(bx-7,41,bw+hw+20,21)
            # Tail and far legs.
            color(dark); line([(bx+8,by+bh*.70),(bx-12,by+30),(bx-20,by-18)],3)
            ellipse(bx-26,by-24,13,18)
            for x in (bx+43,bx+bw-35): rect(x,49,legw,by-36)
            # Udder only on the adult female illustration; never on male/calf/unknown.
            if sex=='Dişi' and age=='adult':
                color((.82,.58,.48)); ellipse(bx+39,by-15,49,28)
                rect(bx+47,by-22,6,15,2); rect(bx+70,by-22,6,15,2)
            color(coat); ellipse(bx,by,bw,bh)
            ellipse(hx-25,by+bh*.25,44,bh*.75)
            if bull:
                ellipse(bx+bw-88,by+20,91,bh-4)
                ellipse(hx-28,by-3,42,bh)
            # A unique but explicitly representative marking layout for each tag.
            if family in ('holstein','red_holstein'):
                color((.13,.18,.19) if family=='holstein' else (.60,.25,.13))
                for fraction in (.20,.48,.76):
                    px=bx+bw*fraction+rng.uniform(-8,7)
                    py=by+bh*.30+rng.uniform(-8,5)
                    pw=rng.uniform(25,43)*(0.78 if calf else 1)
                    ph=rng.uniform(28,47)*(0.75 if calf else 1)
                    ellipse(px-pw/2,py,pw,ph)
                    ellipse(px-pw*.35,py-5,pw*.80,ph*.60)
            elif family=='simmental':
                color((.96,.94,.84)); ellipse(bx+13,by+12,bw*.24,bh*.62)
                ellipse(bx+bw*.57,by+7,bw*.20,bh*.67)
            elif family in ('brown','jersey'):
                color(tuple(min(1,v*1.12) for v in coat)); line([(bx+35,by+bh-8),(bx+bw-40,by+bh-9)],4)
            # Near legs, with white stockings on Simmental.
            color(coat)
            for x in (bx+22,bx+bw-22):
                rect(x,47,legw,by-27)
                if family=='simmental': color((.94,.93,.85)); rect(x,47,legw,26); color(coat)
            color(outline)
            for x in (bx+22,bx+bw-22,bx+43,bx+bw-35): rect(x,45,legw+2,9,3)
            # Breed-specific ear shapes.
            color(coat)
            ellipse(hx-17,hy+hh*.60,36 if family=='jersey' else 27,14)
            ellipse(hx+hw-11,hy+hh*.58,38 if family=='jersey' else 28,14)
            color((.66,.44,.33)); ellipse(hx-11,hy+hh*.62,19,7)
            ellipse(hx+hw-4,hy+hh*.60,19,7)
            color(coat); ellipse(hx,hy,hw,hh)
            if family=='simmental':
                color((.97,.95,.85)); ellipse(hx+hw*.15,hy+3,hw*.74,hh-2)
            elif family in ('holstein','red_holstein'):
                color((.18,.22,.20) if family=='holstein' else (.56,.24,.12))
                ellipse(hx+hw*.06,hy+hh*.39,hw*.46,hh*.54)
                color((.96,.95,.88)); rect(hx+hw*.43,hy+hh*.32,hw*.14,hh*.55,4)
            # Buffalo horns are swept sideways; Angus silhouettes have no horns.
            if not calf and family=='buffalo':
                color((.65,.65,.57)); line([(hx+12,hy+hh-4),(hx-15,hy+hh+5),(hx-27,hy+hh+26)],6)
                line([(hx+hw-12,hy+hh-4),(hx+hw+15,hy+hh+5),(hx+hw+23,hy+hh+26)],6)
            elif not calf and family not in ('angus','red_angus'):
                color((.88,.84,.68))
                horn=25 if bull else (12 if young else 16)
                tri([(hx+9,hy+hh-3),(hx+2,hy+hh+horn),(hx+20,hy+hh-1)])
                tri([(hx+hw-21,hy+hh-1),(hx+hw-1,hy+hh+horn),(hx+hw-10,hy+hh-3)])
            # Jersey's pale muzzle ring, dark muzzle on buffalo/Angus, pink on alaca.
            muzzle=(.74,.49,.40) if family in ('holstein','red_holstein','simmental','charolais') else (.22,.24,.22)
            if family in ('jersey','brown','limousin'):
                color((.88,.79,.60)); ellipse(hx+2,hy-3,hw-3,29)
            color(muzzle); ellipse(hx+6,hy-1,hw-11,24)
            color(outline)
            eye=7 if calf else 5
            ellipse(hx+hw*.22,hy+hh*.45,eye,eye+1); ellipse(hx+hw*.70,hy+hh*.45,eye,eye+1)
            color((1,1,1)); ellipse(hx+hw*.22+1,hy+hh*.45+3,2,2); ellipse(hx+hw*.70+1,hy+hh*.45+3,2,2)
            color(outline); ellipse(hx+hw*.29,hy+8,4,3); ellipse(hx+hw*.65,hy+8,4,3)
            color((.89,.65,.18)); rect(hx+hw+4,hy+hh*.47,9,15,2)
