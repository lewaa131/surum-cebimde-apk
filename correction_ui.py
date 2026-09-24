from datetime import date
import sqlite3
from corrections import undo,loss,snapshot,record

def undo_screen(app,cow_id):
    from main import button,paragraph
    popup,body,error,actions=app.dialog('Yanlış işlemi geri al')
    body.add_widget(paragraph('Bu sürümde onaylanan işlemler geri alınabilir. Sonraki bağlı kayıtlar varsa önce onlar düzeltilir.'))
    rows=app.herd.db.execute('SELECT id,title FROM corrections WHERE cow_id=? ORDER BY id DESC',(cow_id,)).fetchall()
    if not rows: body.add_widget(paragraph('Geri alınabilir işlem yok. Eski sürüm kayıtlarının işlem öncesi bilgisi saklanmamış.'))
    for row in rows:
        def ask(_,i=row['id'],title=row['title']):
            confirm,content,message,controls=app.dialog('İşlem geri alınsın mı?')
            content.add_widget(paragraph(title+' kaydı kaldırılacak; önceki duruma dönülecek.'))
            if title=='Doğum yaptı': content.add_widget(paragraph('Bu doğumda otomatik eklenen buzağılar da kaldırılır; sonradan değiştirilmişlerse işlem engellenir.'))
            def save(*_):
                try: undo(app.herd,i)
                except (ValueError,sqlite3.Error) as exc: message.text=str(exc); return
                confirm.dismiss(); app.sync_reminders(force=True); app.profile(cow_id)
            controls.add_widget(button('Evet, geri al',save))
        body.add_widget(button(row['title']+' · Geri al',ask,48,variant='secondary'))

def loss_screen(app,cow_id):
    from main import button,paragraph
    from kivy.uix.spinner import Spinner
    from kivy.metrics import dp
    popup,body,error,actions=app.dialog('Gebelik kaybı / düşük')
    body.add_widget(paragraph('Gebelik kapanır, doğum takvimi kaldırılır. Hayvanın sağmal/kuruda durumu korunur.'))
    day=app.field(body,'Olay tarihi',date.today().strftime('%d.%m.%Y'),date_input=True)
    kind=Spinner(text='Gebelik kaybı',values=('Gebelik kaybı','Düşük'),size_hint_y=None,height=dp(48));body.add_widget(kind)
    def save(*_):
        try: loss(app.herd,cow_id,day.text,kind.text)
        except (ValueError,sqlite3.Error) as exc: error.text=str(exc); return
        popup.dismiss(); app.sync_reminders(force=True); app.profile(cow_id)
    actions.add_widget(button('Kaybı onayla',save))

def recovery_screen(app,cow_id):
    from cycle_ui import confirmed
    def save():
        cow=app.herd.get(cow_id)
        if not cow.get('_loss_pending'): raise ValueError('Bu kontrol artık beklemiyor.')
        before=snapshot(app.herd.db,cow_id)
        with app.herd.db:
            app.herd.db.execute("INSERT INTO events(cow_id,kind,day) VALUES (?,'Kayıp sonrası kontrol edildi',?)",(cow_id,date.today().isoformat()))
            record(app.herd.db,cow_id,'Kayıp sonrası kontrol',before)
    return confirmed(app,'Kontrol sonrası devam',cow_id,
        'Veteriner kontrolü sonrası yeniden tohumlama değerlendirmesine dönmek istediğini onayla.',save)
