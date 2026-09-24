"""Date-derived stages and tasks; never invent births or pregnancy results."""
from datetime import date, timedelta
from herd import can_reproduce, due_date


def category(cow, today=None):
    today=today or date.today()
    born=date.fromisoformat(cow['born'])
    months=(today.year-born.year)*12+today.month-born.month-(today.day<born.day)
    known=int(cow.get('calved_before',-1))
    if cow.get('last_birth'): known=1
    if cow.get('sex')=='Dişi' and known==1: return 'İnek'
    if months<6: return 'Buzağı'
    if months<12: return 'Dana'
    if cow.get('sex')=='Erkek': return 'Tosun' if months<24 else 'Boğa'
    if cow.get('sex')=='Dişi': return 'Düve' if known==0 else 'Dişi · doğum bilgisi eksik'
    return 'Cinsiyet bilgisi eksik'


def snapshot(cow, settings, today=None):
    today=today or date.today()
    born=date.fromisoformat(cow['born'])
    group=category(cow,today)
    result=dict(category=group,stage=group,tasks=[])
    if cow.get('record_status','Aktif')!='Aktif' or cow.get('registry_status','') not in ('','Canlı'):
        result['stage']='Takip kapalı'
        return result
    marks=cow.get('_cycle_marks',[])
    def task(kind,title,day,anchor,action,description,enabled=True,until=None):
        mark=next((m for m in marks if m['kind']==kind and m['anchor']==anchor),None)
        if mark and mark['done_day']: return
        if mark and mark['snooze_until']:
            day=max(day,date.fromisoformat(mark['snooze_until']))
        if until and (day>=until or today>=until): return
        result['tasks'].append(dict(kind=kind,title=title,day=day.isoformat(),anchor=anchor,
            action=action,description=description,notify=enabled,until=until.isoformat() if until else '',
            due=day<=today,cow_id=cow['id']))
    # Weaning belongs to the calf, never to the mother's postpartum clock.
    if int(cow.get('calved_before',-1))!=1 and (today-born).days<365:
        task('weaning','Sütten kesmeyi değerlendir',born+timedelta(days=settings['weaning_days']),cow['born'],
             'Sütten kesildi','Yem tüketimi ve gelişimi uygunsa onayla.',settings['weaning_enabled'],born+timedelta(days=365))
    if not can_reproduce(cow): return result
    known=int(cow.get('calved_before',-1))
    last=date.fromisoformat(cow['last_birth']) if cow.get('last_birth') else None
    ins=date.fromisoformat(cow['insemination']) if cow.get('insemination') else None
    if cow.get('pregnant'):
        result['stage']='Gebe' + (' · Kuruda' if cow['state']=='Kuru dönemde' else ' · Sağmal' if cow['state']=='Sağmal' else '')
        due=due_date(cow)
        if due:
            if group=='İnek' and cow['state']=='Sağmal':
                task('dry','Kuruya ayırma zamanı',due-timedelta(days=settings['dry_days']),cow['insemination'],
                     'Kuruya ayırdım','Sağımın sonlandırıldığını onayla.',settings['dry_enabled'],due)
            task('birth','Buzağı doğdu mu?',due,cow['insemination'],'Doğdu',
                 'Doğduysa onayla; annenin yeni döngüsü başlasın.')
            if due<=today: result['stage']='Doğum kontrolü' if due==today else 'Doğum tarihi geçti'
        else: result['stage']='Gebe · tohumlama tarihi eksik'
        return result
    if ins:
        result['stage']='Tohumlandı · sonuç bekleniyor'
        check=ins+timedelta(days=settings['pregnancy_check_days'])
        task('heat','Kızgınlık dönüşünü kontrol et',ins+timedelta(days=settings['heat_days']),cow['insemination'],
             'Kontrol sonucu','Gözlem sonucunu kaydet; tarih tek başına gebelik göstermez.',settings['heat_enabled'],check)
        task('pregnancy','Gebelik kontrol zamanı',check,cow['insemination'],
             'Gebelik sonucu','Muayene sonucuna göre gebe veya gebe değil seç.',settings['pregnancy_check_enabled'])
        if check<=today: result['stage']='Gebelik kontrolü bekleniyor'
        return result
    loss_day=cow.get('_loss_day','')
    if loss_day and cow.get('_loss_pending'):
        result['stage']='Gebelik kaybı sonrası kontrol'
        task('recovery','Yeniden tohumlama öncesi kontrol',date.fromisoformat(loss_day),loss_day,
             'Kontrol edildi','Kontrol sonrası yeniden tohumlama değerlendirmesine dön.')
        return result
    if known==-1 and (today-born).days>=365:
        result['stage']='Durum belirtilmedi'
    elif known==1 and not last:
        result['stage']='Kuruda' if cow['state']=='Kuru dönemde' else 'Sağmal' if cow['state']=='Sağmal' else 'İnek'
    else:
        ready=last+timedelta(days=settings['postpartum_days']) if last else born+timedelta(days=settings['heifer_days'])
        result['stage']='Tohumlama değerlendirmesi' if ready<=today else 'Doğum sonrası bekleme' if last else 'Büyüme dönemi'
        task('breed','Yeniden tohumlama değerlendirmesi' if last else 'İlk tohumlama değerlendirmesi',ready,last.isoformat() if last else cow['born'],
             'Tohumlandı','Kızgınlık, gelişim ve sağlık uygunsa yapılan tohumlamayı kaydet.')
    return result


def tasks_for(cows, settings, today=None, upcoming=False):
    tasks=[]
    for cow in cows:
        for task in snapshot(cow,settings,today)['tasks']:
            if upcoming or task['due']: tasks.append(task|{'cow':cow})
    return sorted(tasks,key=lambda t:(t['day'],t['cow']['tag'],t['kind']))


def notification_plan(cows,settings,clock='09:00',today=None):
    events=[]
    for task in tasks_for(cows,settings,today,True):
        if not task['notify']: continue
        cow=task['cow']
        identity=f'{cow["name"]} · {cow["tag"]}' if cow['name'] else cow['tag']
        events.append(dict(key=f'cycle:{cow["id"]}:{task["kind"]}:{task["anchor"]}:{task["day"]}',
            cow_id=cow['id'],identity=identity,day=task['day'],until=task['until'],time=clock,
            kind=task['kind'],title=task['title'],body=f'{identity} — {task["description"]}'))
    return events
