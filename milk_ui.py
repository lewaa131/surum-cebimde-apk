from datetime import date
import sqlite3
from kivy.metrics import dp
from milk_store import MilkStore,display,total
from herd import parse_date


def milk_screen(app,day=None):
    from main import button,paragraph
    day=day or date.today().isoformat()
    store=MilkStore(app.herd.db)
    popup,body,error,actions=app.dialog('Süt takibi')
    entry=app.field(body,'Gün',date.fromisoformat(day).strftime('%d.%m.%Y'),date_input=True)
    def change(*_):
        try:
            chosen=parse_date(entry.text)
            if chosen>date.today(): raise ValueError('Gelecek gün seçilemez.')
        except ValueError as exc: error.text=str(exc); return
        milk_screen(app,chosen.isoformat())
    body.add_widget(button('Günü göster',change,44,'secondary'))
    amount,count,partial=store.summary(day)
    body.add_widget(paragraph(f'{display(amount)} L · {count} hayvanda kayıt'))
    if partial: body.add_widget(paragraph(f'{partial} hayvanda sabah veya akşam girişi eksik.'))
    cows=[c for c in app.herd.all() if store.can_enter(c,day) or store.get(c['id'],day)]
    if not cows: body.add_widget(paragraph('Bu gün için kayıt veya aktif sağmal hayvan yok.'))
    for cow in cows:
        row=store.get(cow['id'],day)
        text=(cow['name'] or cow['tag'])+' · '+(display(total(row))+' L' if row else 'Girilmedi')
        body.add_widget(button(text,lambda _,i=cow['id']:milk_form(app,i,day),52,'secondary'))


def milk_form(app,cow_id,day):
    from main import button,paragraph
    store=MilkStore(app.herd.db); cow=app.herd.get(cow_id); row=store.get(cow_id,day)
    mode=row['mode'] if row else app.cycle['milk_mode']
    popup,body,error,actions=app.dialog('Süt kaydı')
    body.add_widget(paragraph((cow['name'] or cow['tag'])+' · '+date.fromisoformat(day).strftime('%d.%m.%Y')))
    if row: body.add_widget(paragraph('Mevcut kaydı düzenliyorsun; tekrar eklenmez.'))
    inputs={}
    for key,title in ([('morning','Sabah · litre'),('evening','Akşam · litre')] if mode=='separate' else [('daily','Günlük toplam · litre')]):
        inputs[key]=app.field(body,title,display(row[key]) if row else '')
        inputs[key].input_type='number'
        inputs[key].hint_text='Örnek: 12,5'
    def save(*_):
        try: store.save(app.herd.get(cow_id),day,mode,**{key:w.text for key,w in inputs.items()})
        except (ValueError,TypeError,sqlite3.Error) as exc: error.text=str(exc); return
        milk_screen(app,day)
    actions.add_widget(button('Kaydet',save))
    if row:
        def ask(*_):
            confirm,content,message,controls=app.dialog('Süt kaydı silinsin mi?')
            content.add_widget(paragraph((cow['name'] or cow['tag'])+' · '+day))
            def remove(*_):
                try: store.delete(cow_id,day)
                except sqlite3.Error: message.text='Kayıt silinemedi. Tekrar dene.'; return
                milk_screen(app,day)
            controls.add_widget(button('Evet, sil',remove))
        body.add_widget(button('Kaydı sil',ask,44,'secondary'))
    body.add_widget(button('Süt geçmişi',lambda *_:milk_history(app,cow_id),44,'secondary'))
    popup.milk_inputs=inputs


def milk_history(app,cow_id):
    from main import button,paragraph
    cow=app.herd.get(cow_id)
    popup,body,error,actions=app.dialog('Süt geçmişi')
    body.add_widget(paragraph(cow['name'] or cow['tag']))
    rows=MilkStore(app.herd.db).history(cow_id)
    if not rows: body.add_widget(paragraph('Henüz süt kaydı yok.'))
    for row in rows:
        detail=(f'Sabah {display(row["morning"]) or "—"} · Akşam {display(row["evening"]) or "—"}' if row['mode']=='separate' else 'Günlük toplam')
        body.add_widget(button(date.fromisoformat(row['day']).strftime('%d.%m.%Y')+' · '+display(total(row))+' L\n'+detail,
            lambda _,day=row['day']:milk_form(app,cow_id,day),68,'secondary'))
    body.add_widget(button('Gün seç / süt gir',lambda *_:milk_screen(app),48,'secondary'))
