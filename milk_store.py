"""One milk record per animal and day; integer millilitres avoid rounding drift."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re


def litres(value):
    if value is None or not str(value).strip(): return None
    text=str(value).strip().replace(',','.')
    if not re.fullmatch(r'\d{1,3}(?:\.\d{1,3})?',text): raise ValueError('Litreyi sayı olarak yaz. Örnek: 12,5')
    amount=Decimal(text)
    if amount>999: raise ValueError('Litre 0–999 arasında olmalı.')
    return int(amount*1000)


def display(amount):
    if amount is None: return ''
    return format(Decimal(amount)/1000,'f').rstrip('0').rstrip('.') if amount%1000 else str(amount//1000)


class MilkStore:
    def __init__(self,db):
        self.db=db
        db.execute('''CREATE TABLE IF NOT EXISTS milk (
            cow_id INTEGER NOT NULL, day TEXT NOT NULL, mode TEXT NOT NULL,
            morning INTEGER, evening INTEGER, daily INTEGER,
            PRIMARY KEY(cow_id,day))''')
        db.commit()

    def get(self,cow_id,day):
        row=self.db.execute('SELECT * FROM milk WHERE cow_id=? AND day=?',(cow_id,day)).fetchone()
        return dict(row) if row else None

    def can_enter(self,cow,day):
        if cow['sex']!='Dişi' or cow['record_status']!='Aktif' or cow['registry_status'] not in ('','Canlı'): return False
        events=self.db.execute("SELECT kind,day FROM events WHERE cow_id=? AND kind IN ('Doğum yaptı','Kuruya ayrıldı') ORDER BY day,id",(cow['id'],)).fetchall()
        if cow['state']=='Kuru dönemde' and not any(r['kind']=='Kuruya ayrıldı' and r['day']>day for r in events): return False
        previous=[r for r in events if r['day']<=day]
        if previous: return previous[-1]['kind']=='Doğum yaptı'
        if events:
            # A recorded dry-off proves milking immediately before that first boundary.
            return events[0]['kind']=='Kuruya ayrıldı' and day<events[0]['day']
        return cow['state']=='Sağmal'

    def save(self,cow,day,mode,morning='',evening='',daily='',today=None):
        today=today or date.today()
        parsed=date.fromisoformat(day)
        if not date.fromisoformat(cow['born'])<=parsed<=today: raise ValueError('Tarih doğumdan önce veya gelecekte olamaz.')
        existing=self.get(cow['id'],day)
        if not existing and not self.can_enter(cow,day):
            raise ValueError('Bu tarihte sağım kaydı uygun değil. Doğum ve kuruya ayırma tarihlerini kontrol et.')
        if mode not in ('separate','daily'): raise ValueError('Süt giriş biçimi geçersiz.')
        am,pm,total=(litres(morning),litres(evening),None) if mode=='separate' else (None,None,litres(daily))
        if am is None and pm is None and total is None: raise ValueError('En az bir süt miktarı yaz.')
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO milk(cow_id,day,mode,morning,evening,daily) VALUES (?,?,?,?,?,?)',
                (cow['id'],day,mode,am,pm,total))

    def history(self,cow_id):
        return [dict(r) for r in self.db.execute('SELECT * FROM milk WHERE cow_id=? ORDER BY day DESC',(cow_id,))]

    def delete(self,cow_id,day):
        with self.db: self.db.execute('DELETE FROM milk WHERE cow_id=? AND day=?',(cow_id,day))

    def summary(self,day):
        row=self.db.execute('''SELECT COALESCE(SUM(COALESCE(morning,0)+COALESCE(evening,0)+COALESCE(daily,0)),0),
            COUNT(*),COALESCE(SUM(CASE WHEN mode='separate' AND (morning IS NULL OR evening IS NULL) THEN 1 ELSE 0 END),0)
            FROM milk WHERE day=?''',(day,)).fetchone()
        return tuple(row)


def total(row):
    return sum(row[key] or 0 for key in ('morning','evening','daily'))
