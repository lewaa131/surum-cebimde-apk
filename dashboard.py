"""Sekmelerin ortak filtreleri. Arşiv kayıtları aktif işlere karışmaz."""
from datetime import date, timedelta
from herd import due_date


def sections(cows, tab, today=None, dry_days=60):
    today = today or date.today()
    active = [c for c in cows if c.get('record_status','Aktif') == 'Aktif']
    active.sort(key=lambda c:(due_date(c) or date.max,c['tag']))
    due = [c for c in active if due_date(c) and due_date(c) <= today]
    overdue = [c for c in due if due_date(c) < today]
    dry = [c for c in active if c['state'] == 'Kuru dönemde']
    dry_tasks = [c for c in active if due_date(c) and today < due_date(c) <= today+timedelta(days=dry_days) and c['state'] == 'Sağmal']
    if tab == 'today': return [('Doğum kontrolü',due),('Kuruya ayrılacaklar',dry_tasks)]
    if tab == 'birth': return [('Bugün doğum beklenenler',[c for c in due if due_date(c)==today]),('Doğumu gecikenler',overdue)]
    if tab == 'special': return [('Bugün doğum beklenenler',[c for c in due if due_date(c)==today]),('Kurular',dry),('Doğumu gecikenler',overdue)]
    if tab == 'archive':
        return [(title,sorted([c for c in cows if c.get('record_status')==status], key=lambda c:c['tag']))
                for title,status in [('Satılanlar','Satıldı'),('Ölenler','Öldü'),('Arşivlenenler','Arşiv')]]
    return [('Sürüm',active)]
