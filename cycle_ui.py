"""Short confirmations for the real events that advance automatic tracking."""
from datetime import date, timedelta
import sqlite3
from kivy.metrics import dp
from kivy.uix.spinner import Spinner
from kivy.uix.boxlayout import BoxLayout
from mobile_ui import big_button
from settings_ui import card, text
from text_entry import TagNumberInput
from lifecycle import snapshot, tasks_for
from herd import parse_date, can_reproduce


def show_day(day):
    return date.fromisoformat(day).strftime('%d.%m.%Y')


def finish(app,popup,cow_id):
    popup.dismiss()
    app.sync_reminders(force=True)
    if app.current_id is not None: app.profile(cow_id)
    else: app.home()


def confirmed(app,title,cow_id,description,operation,label='Onayla'):
    popup,body,error,actions=app.dialog(title)
    cow=app.herd.get(cow_id)
    body.add_widget(text(cow['name'] or cow['tag'],19,True))
    body.add_widget(text(description))
    def save(*_):
        if getattr(popup,'_saved',False): return
        try: operation()
        except (ValueError,sqlite3.Error) as exc: error.text=str(exc); return
        popup._saved=True
        finish(app,popup,cow_id)
    actions.add_widget(big_button(label,save))
    return popup


def birth(app,cow_id):
    popup,body,error,actions=app.dialog('Buzağı doğdu')
    body.add_widget(text('Annenin yeni döngüsü ve buzağının takibi birlikte başlar.'))
    day=app.field(body,'Doğum tarihi',date.today().strftime('%d.%m.%Y'),date_input=True)
    body.add_widget(text('Sürüye eklenecek canlı buzağı'))
    count=Spinner(text='1',values=('1','2','Canlı buzağı yok'),size_hint_y=None,height=dp(48))
    body.add_widget(count)
    sexes=[]
    sex_rows=[]
    for title in ('Buzağının cinsiyeti','İkiz varsa ikinci buzağı'):
        row=BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(6))
        row.bind(minimum_height=row.setter('height'))
        row.add_widget(text(title))
        control=Spinner(text='Bilinmiyor',values=('Dişi','Erkek','Bilinmiyor'),size_hint_y=None,height=dp(48))
        row.add_widget(control); sexes.append(control); sex_rows.append(row)
    holder=BoxLayout(orientation='vertical',size_hint_y=None,spacing=dp(8))
    holder.bind(minimum_height=holder.setter('height')); body.add_widget(holder)
    def show_sexes(*_):
        holder.clear_widgets()
        for row in sex_rows[:0 if count.text=='Canlı buzağı yok' else int(count.text)]: holder.add_widget(row)
    count.bind(text=show_sexes); show_sexes()
    body.add_widget(text('Küpeyi sonra ekleyebilirsin; buzağı annesine bağlı kaydedilir.',13))
    def save(*_):
        if getattr(popup,'_saved',False): return
        try:
            values=[] if count.text=='Canlı buzağı yok' else [w.text for w in sexes[:int(count.text)]]
            app.herd.record_birth(cow_id,day.text,calves=values)
        except (ValueError,sqlite3.Error) as exc: error.text=str(exc); return
        popup._saved=True
        finish(app,popup,cow_id)
    actions.add_widget(big_button('Doğumu kaydet',save))
    popup.birth_day=day; popup.birth_count=count; popup.birth_sexes=sexes
    return popup


def history(app,cow_id):
    cow=app.herd.get(cow_id)
    popup,body,error,actions=app.dialog('Doğum geçmişi')
    body.add_widget(text('Tarihi hatırlıyorsan yaz; bilmiyorsan boş bırak.'))
    day=app.field(body,'Son doğum tarihi · isteğe bağlı', '',date_input=True)
    def save(calved):
        try:
            app.herd.set_birth_history(cow_id,calved,day.text if calved else '')
        except (ValueError,sqlite3.Error) as exc: error.text=str(exc); return
        finish(app,popup,cow_id)
    body.add_widget(big_button('Hiç doğurmadı · düve',lambda *_:save(False),48,'secondary'))
    actions.add_widget(big_button('Doğurdu · kaydet',lambda *_:save(True)))
    return popup


def inseminate(app,cow_id):
    cow=app.herd.get(cow_id)
    popup,body,error,actions=app.dialog('Tohumlandı')
    day=app.field(body,'Tohumlama tarihi',date.today().strftime('%d.%m.%Y'),date_input=True)
    body.add_widget(text('Yapılan işlemi kaydet; gebelik sonucu kontrol sonrası onaylanır.'))
    warning=text('',13); body.add_widget(warning)
    def describe(*_):
        try:
            chosen=parse_date(day.text)
            start=date.fromisoformat(cow['last_birth'] or cow['born'])
            threshold=app.cycle['postpartum_days'] if cow['last_birth'] else app.cycle['heifer_days']
            messages=[]
            if (chosen-start).days<threshold: messages.append('Planlanan bekleme süresinden erken; yalnızca yapılmış işlemi kaydet.')
            dates=app.herd.history(cow_id)
            if dates and 0<=(chosen-date.fromisoformat(dates[0])).days<app.cycle['insemination_gap_days']:
                messages.append('Önceki tohumlamaya yakın; tarihi kontrol et.')
            warning.text='\n'.join(messages)
        except ValueError: warning.text='Tarihi tamamla.'
    day.bind(text=describe); describe()
    def save(*_):
        if getattr(popup,'_saved',False): return
        try: app.herd.record_insemination(cow_id,day.text,app.cycle)
        except (ValueError,sqlite3.Error) as exc: error.text=str(exc); return
        popup._saved=True
        finish(app,popup,cow_id)
        app.request_notifications()
    actions.add_widget(big_button('Tohumlamayı kaydet',save))
    return popup


def result(app,cow_id,heat=False):
    cow=app.herd.get(cow_id)
    popup,body,error,actions=app.dialog('Kızgınlık gözlemi' if heat else 'Gebelik sonucu')
    body.add_widget(text('Gözlemi kaydet; gebelik sonucu kontrol sonrası belirlenir.' if heat else 'Veteriner kontrolünde belirlenen sonucu seç.'))
    def save(positive):
        if getattr(popup,'_saved',False): return
        try:
            if heat:
                app.herd.cycle_mark(cow_id,'heat',cow['insemination'],app.cycle,heat_observed=positive)
            else: app.herd.pregnancy_result(cow_id,positive,cow['insemination'])
        except (ValueError,sqlite3.Error) as exc: error.text=str(exc); return
        popup._saved=True
        finish(app,popup,cow_id)
    body.add_widget(big_button('Kızgınlık var' if heat else 'Gebe',lambda *_:save(True),48))
    body.add_widget(big_button('Gözlenmedi' if heat else 'Gebe değil',lambda *_:save(False),48,'secondary'))
    return popup


def act(app,task):
    cow_id=task['cow_id']; kind=task['kind']
    if kind=='birth': return birth(app,cow_id)
    if kind=='breed': return inseminate(app,cow_id)
    if kind=='history': return history(app,cow_id)
    if kind in ('pregnancy','heat'): return result(app,cow_id,kind=='heat')
    if kind=='dry': return app.record_action(cow_id,'Kuruya ayrıldı')
    if kind=='recovery':
        from correction_ui import recovery_screen
        return recovery_screen(app,cow_id)
    return confirmed(app,task['action'],cow_id,task['description'],
        lambda:app.herd.cycle_mark(cow_id,kind,task['anchor'],app.cycle))


def task_card(app,parent,task,identity=False):
    cow=app.herd.get(task['cow_id'])
    title=(cow['name'] or cow['tag']) if identity else task['title']
    description=(task['title']+' · ' if identity else '')+show_day(task['day'])
    box=card(parent,title,description)
    box.add_widget(big_button(task['action'],lambda *_:act(app,task),48))
    if task['kind'] in ('birth','pregnancy','breed') and task['due']:
        box.add_widget(big_button('Henüz doğmadı · yarın sor' if task['kind']=='birth' else 'Yarın hatırlat',
            lambda *_:confirmed(app,'Yarın hatırlat',cow['id'],'Bu görev yarın yeniden gösterilecek.',
                lambda:app.herd.cycle_mark(cow['id'],task['kind'],task['anchor'],app.cycle,snooze=True)),44,'secondary'))
    if identity: box.add_widget(big_button('Hayvanı aç',lambda *_:app.profile(cow['id']),44,'secondary'))
    return box


def today_view(app,parent):
    tasks=tasks_for(app.herd.all(),app.cycle,upcoming=True)
    due=[t for t in tasks if t['due']]
    parent.add_widget(text(f'Bekleyen işler · {len(due)}',20,True))
    if not due: parent.add_widget(text('Bugün bekleyen iş yok.'))
    for task in due: task_card(app,parent,task,True)
    days={'week':7,'fortnight':14,'month':30}[app.cycle['calendar_view']]
    limit=(date.today()+timedelta(days=days)).isoformat()
    upcoming=[t for t in tasks if not t['due'] and t['day']<=limit]
    parent.add_widget(text(f'Önümüzdeki {days} gün · {len(upcoming)}',18,True))
    for task in upcoming:
        box=card(parent,task['cow']['name'] or task['cow']['tag'],task['title']+' · '+show_day(task['day']))
        box.add_widget(big_button('Hayvanı aç',lambda _,i=task['cow_id']:app.profile(i),44,'secondary'))


def identity(app,cow_id):
    cow=app.herd.get(cow_id)
    popup,body,error,actions=app.dialog('Buzağının bilgileri')
    body.add_widget(text('TR küpe · 12 rakam; henüz yoksa boş bırak.'))
    tag=TagNumberInput(size_hint_y=None,height=dp(56)); body.add_widget(tag)
    sex=Spinner(text=cow['sex'],values=('Dişi','Erkek','Bilinmiyor'),size_hint_y=None,height=dp(48)); body.add_widget(sex)
    def save(*_):
        try: app.herd.assign_calf_identity(cow_id,('TR'+tag.text) if tag.text else '',sex.text)
        except (ValueError,sqlite3.Error) as exc: error.text=str(exc); return
        finish(app,popup,cow_id)
    actions.add_widget(big_button('Kaydet',save))
    return popup


def profile_cycle(app,parent,cow,compact=False):
    status=snapshot(cow,app.cycle)
    box=card(parent,'DÖNGÜ · '+status['category'],status['stage'])
    if cow['mother_id'] and not compact:
        try: mother=app.herd.get(cow['mother_id'])
        except ValueError: mother=None
        if mother: box.add_widget(big_button('Annesi · '+(mother['name'] or mother['tag']),lambda *_:app.profile(mother['id']),44,'secondary'))
    if not compact and (cow['local_tag'] or cow['mother_id']):
        box.add_widget(big_button('Küpe / cinsiyet bilgisi',lambda *_:identity(app,cow['id']),48,'secondary'))
    for task in status['tasks']:
        if task['due']: task_card(app,box,task)
    next_tasks=[t for t in status['tasks'] if not t['due']]
    for task in sorted(next_tasks,key=lambda t:t['day']):
        box.add_widget(text(task['title']+' · '+show_day(task['day']),13))
    ready_age=(date.today()-date.fromisoformat(cow['born'])).days>=app.cycle['heifer_days']
    if not compact and not cow['pregnant'] and can_reproduce(cow) and (cow['calved_before']==1 or ready_age or cow['insemination']):
        box.add_widget(big_button('Tohumlama kaydet',lambda *_:inseminate(app,cow['id']),48,'secondary'))
    from main import detail_page
    family=detail_page(parent,'Anne ve buzağılar') if compact and (cow['mother_id'] or app.herd.children(cow['id'])) else box
    if compact and cow['mother_id']:
        try:
            mother=app.herd.get(cow['mother_id'])
            family.add_widget(big_button('Annesi · '+(mother['name'] or mother['tag']),lambda *_:app.profile(mother['id']),44,'secondary'))
        except ValueError: pass
    for child in app.herd.children(cow['id']):
        family.add_widget(big_button('Buzağı · '+(child['name'] or 'İsimsiz')+' · '+child['tag'][-4:],lambda _,i=child['id']:app.profile(i),44,'secondary'))
