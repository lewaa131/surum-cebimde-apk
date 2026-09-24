"""Green, compact preference cards for the next stage of cycle tracking."""
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from mobile_ui import big_button, surface, GREEN, INK, GreenSwitch
from text_entry import MobileTextInput
from cycle_settings import DAY_SETTINGS, load_cycle, save_cycle
from pathlib import Path


def text(value, size=14, bold=False):
    widget=Label(text=value,color=INK,font_size=dp(size),bold=bold,
                 size_hint_y=None,halign='left',valign='middle')
    widget.bind(width=lambda w,v:setattr(w,'text_size',(v,None)),
                texture_size=lambda w,v:setattr(w,'height',v[1]+dp(6)))
    return widget


def card(parent,title,description):
    box=BoxLayout(orientation='vertical',size_hint_y=None,padding=dp(12),spacing=dp(8))
    box.bind(minimum_height=box.setter('height'))
    surface(box,(1,1,1,1),18)
    box.add_widget(text(title,17,True))
    box.add_widget(text(description,13))
    parent.add_widget(box)
    return box


class DayStepper(BoxLayout):
    def __init__(self,value,low,high,**kwargs):
        super().__init__(size_hint_y=None,height=dp(48),spacing=dp(8),**kwargs)
        self.low,self.high=low,high
        self.entry=MobileTextInput(text=str(value),multiline=False,input_filter='int',input_type='number',
                                  font_size=dp(19),halign='center',padding=[dp(4),dp(11)])
        for sign,delta in [('−',-1),('+',1)]:
            control=big_button(sign,lambda _,delta=delta:self.step(delta),48,'secondary')
            control.size_hint_x=None; control.width=dp(48)
            if delta==-1: self.add_widget(control)
            else:
                self.add_widget(self.entry)
                self.add_widget(control)
        self.add_widget(Label(text='gün',color=GREEN,size_hint_x=None,width=dp(32),font_size=dp(13)))

    def step(self,delta):
        try: value=int(self.entry.text)
        except ValueError: value=self.low
        self.entry.text=str(max(self.low,min(self.high,value+delta)))


class Choices(BoxLayout):
    def __init__(self,options,value,**kwargs):
        super().__init__(size_hint_y=None,height=dp(48),spacing=dp(6),**kwargs)
        self.options=options
        self.value=value
        self.render()

    def render(self):
        self.clear_widgets()
        for key,title in self.options:
            control=big_button(title,lambda _,key=key:self.select(key),48,
                               'primary' if key==self.value else 'secondary')
            control.font_size=dp(13)
            self.add_widget(control)

    def select(self,key):
        self.value=key
        self.render()


def open_cycle_settings(app):
    path=Path(app.user_data_dir)/'cycle-settings.json'
    try: values=load_cycle(path,app.farm,app.reminder_settings)
    except (ValueError,OSError) as exc:
        app.notice(str(exc)); return
    popup,body,error,actions=app.dialog('Ayarlar')
    intro=card(body,'Otomatik döngü','Günler işleri planlar; doğum ve kontrol sonuçlarını sen onaylarsın.')
    intro.add_widget(text('Sürüm Cebimde · '+app.version,13))
    intro.add_widget(text('Bildirim açık olan işler seçtiğin saatte tek günlük özette toplanır.',13))
    intro.add_widget(text('Gebelik süresi yeni tohumlamalara uygulanır; mevcut gebelik tarihleri korunur.',13))
    intro.add_widget(big_button('Bildirim saati ve izin',lambda *_:app.reminder_options(),48,'secondary'))
    from backup_ui import open_backups
    intro.add_widget(big_button('Yedekle / Geri yükle',lambda *_:open_backups(app),48,'secondary'))
    from update_ui import open_updates
    intro.add_widget(big_button('Güncellemeleri kontrol et',lambda *_:open_updates(app),48,'secondary'))
    inputs={}
    toggles={}
    for key,title,description,default,low,high,toggle in DAY_SETTINGS:
        if key=='fresh_days': continue
        box=card(body,title,description)
        control=DayStepper(values[key],low,high)
        inputs[key]=control.entry
        box.add_widget(control)
        if toggle:
            row=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(8))
            row.add_widget(Label(text='Telefon bildirimi',color=INK,font_size=dp(13),halign='left'))
            switch=GreenSwitch(active=values[toggle])
            toggles[toggle]=switch
            row.add_widget(switch)
            box.add_widget(row)
    box=card(body,'Süt kaydı','Yeni süt kayıtlarını sabah–akşam veya günlük toplam olarak gir.')
    milk=Choices([('separate','Sabah / akşam'),('daily','Günlük toplam')],values['milk_mode'])
    box.add_widget(milk)
    box=card(body,'Yaklaşan işler','Bugün ekranında kaç günlük gelecek planın gösterileceğini seç.')
    calendar=Choices([('week','Hafta'),('fortnight','2 hafta'),('month','Ay')],values['calendar_view'])
    box.add_widget(calendar)
    box=card(body,'Hayvan görselleri','Hayvan listelerinde fotoğraf ve temsili görsel gösterimini seç.')
    photos=GreenSwitch(active=values['show_photos'])
    box.add_widget(photos)

    def save(*_):
        draft=dict(values)
        draft.update({key:entry.text for key,entry in inputs.items()})
        draft['fresh_days']=draft['postpartum_days']
        draft.update({key:switch.active for key,switch in toggles.items()})
        draft.update(milk_mode=milk.value,calendar_view=calendar.value,show_photos=photos.active)
        try: app.cycle=save_cycle(path,draft)
        except (ValueError,OSError) as exc:
            error.text=str(exc); return
        popup.dismiss()
        app.sync_reminders(force=True)
        if app.current_id is not None: app.profile(app.current_id)
        else: app.home()
        app.notice('Ayarlar kaydedildi; işler ve bildirim takvimi güncellendi.')
    actions.add_widget(big_button('Tercihleri kaydet',save))
    # Public handles support focused interaction checks without production data.
    popup.setting_inputs=inputs
    popup.setting_toggles=toggles
    popup.setting_choices={'milk_mode':milk,'calendar_view':calendar}
    popup.setting_photos=photos
    return popup
