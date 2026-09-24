"""İnternetsiz sürü kayıtları ve tarih hesapları."""
import sqlite3
import json
from datetime import date, datetime, timedelta
from cycle_store import CycleStore

STATES = ('Sağmal', 'Kuru dönemde', 'Düve', 'Buzağı', 'Diğer')

def can_reproduce(cow):
    return cow.get('record_status', 'Aktif') == 'Aktif' and cow.get('sex') == 'Dişi' and cow.get('registry_status', '') in ('', 'Canlı')

def reproduction_reason(cow):
    if cow.get('record_status', 'Aktif') != 'Aktif':
        return 'Arşivdeki hayvanlarda üreme takibi kapalı.'
    if cow.get('sex') == 'Erkek':
        return 'Erkek hayvanlarda tohumlama ve gebelik kaydı yapılamaz.'
    if cow.get('sex') != 'Dişi':
        return 'Cinsiyet doğrulanmadı. Önce resmi bilgileri yenileyin.'
    return 'Canlı olmayan hayvanlarda yeni üreme kaydı yapılamaz.'

def parse_date(value):
    try:
        return datetime.strptime(value.strip(), '%d.%m.%Y').date()
    except ValueError:
        raise ValueError('Tarihi gün.ay.yıl olarak yazın. Örnek: 09.09.2026') from None

def age_text(born, today=None):
    today = today or date.today()
    months = (today.year-born.year)*12 + today.month-born.month
    months -= today.day < born.day
    return f'{months//12} yaş {months%12} ay' if months >= 12 else f'{max(0, months)} aylık'

def due_date(cow):
    return (date.fromisoformat(cow['insemination']) + timedelta(days=cow['gestation_days'])) if can_reproduce(cow) and cow['pregnant'] and cow['insemination'] else None


def card_status(cow):
    status = cow['state']
    if can_reproduce(cow):
        if cow['pregnant']:
            status += ' · Gebe'
        elif cow['insemination']:
            status += '\nTohumlandı · Gebelik bekleniyor'
        if cow['insemination']:
            status += '\nTohumlama: '+date.fromisoformat(cow['insemination']).strftime('%d.%m.%Y')
    return status

def due_text(cow, today=None):
    if not can_reproduce(cow):
        return 'Üreme takibi kapalı'
    due = due_date(cow)
    if not cow['pregnant']:
        return 'Gebelik kaydı yok'
    if not due:
        return 'Gebe · Tohumlama tarihi bilinmiyor'
    days = (due - (today or date.today())).days
    remaining = f'{days} gün kaldı' if days > 0 else ('Tahmini doğum bugün' if days == 0 else f'Tahmini tarih {abs(days)} gün geçti')
    return f'{remaining} · {due:%d.%m.%Y}'

class Herd(CycleStore):
    def __init__(self, path):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS cows (
            id INTEGER PRIMARY KEY, tag TEXT NOT NULL UNIQUE COLLATE NOCASE,
            name TEXT NOT NULL, born TEXT NOT NULL, state TEXT NOT NULL,
            pregnant INTEGER NOT NULL, insemination TEXT NOT NULL,
            gestation_days INTEGER NOT NULL, notes TEXT NOT NULL)''')
        self.db.commit()
        columns = {row['name'] for row in self.db.execute('PRAGMA table_info(cows)')}
        additions = {'sex': 'Bilinmiyor', 'breed': '', 'species': '', 'registry_status': '',
                     'photo_path': '', 'vaccinations': '[]', 'checked_at': '',
                     'record_status': 'Aktif', 'status_date': ''}
        with self.db:
            for key, default in additions.items():
                if key not in columns:
                    self.db.execute(f"ALTER TABLE cows ADD COLUMN {key} TEXT NOT NULL DEFAULT '{default}'")
            self.db.execute('''CREATE TABLE IF NOT EXISTS inseminations (
                id INTEGER PRIMARY KEY, cow_id INTEGER NOT NULL REFERENCES cows(id),
                day TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
            self.db.execute('''INSERT INTO inseminations(cow_id,day)
                SELECT id,insemination FROM cows WHERE insemination <> ''
                AND NOT EXISTS(SELECT 1 FROM inseminations WHERE cow_id=cows.id)''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY, cow_id INTEGER NOT NULL REFERENCES cows(id),
                kind TEXT NOT NULL, day TEXT NOT NULL)''')
            self.db.execute('''DELETE FROM inseminations WHERE id NOT IN
                (SELECT MIN(id) FROM inseminations GROUP BY cow_id,day)''')
            self.db.execute('CREATE UNIQUE INDEX IF NOT EXISTS insemination_day ON inseminations(cow_id,day)')
        self.init_cycle()
        from milk_store import MilkStore
        MilkStore(self.db)
        from corrections import init
        init(self.db); self.db.commit()

    def all(self):
        return [self.cycle_data(dict(row)) for row in self.db.execute('SELECT * FROM cows ORDER BY tag')]

    def get(self, cow_id):
        row = self.db.execute('SELECT * FROM cows WHERE id=?', (cow_id,)).fetchone()
        if row is None:
            raise ValueError('Hayvan kaydı bulunamadı.')
        return self.cycle_data(dict(row))

    def delete(self, cow_id):
        with self.db:
            self.get(cow_id)
            self.db.execute('DELETE FROM inseminations WHERE cow_id=?', (cow_id,))
            self.db.execute('DELETE FROM events WHERE cow_id=?', (cow_id,))
            self.db.execute('DELETE FROM cycle_marks WHERE cow_id=?', (cow_id,))
            self.db.execute('DELETE FROM milk WHERE cow_id=?', (cow_id,))
            self.db.execute('DELETE FROM corrections WHERE cow_id=?', (cow_id,))
            self.db.execute('UPDATE cows SET mother_id=NULL WHERE mother_id=?',(cow_id,))
            self.db.execute('DELETE FROM cows WHERE id=?', (cow_id,))

    def history(self, cow_id):
        return [r['day'] for r in self.db.execute('SELECT day FROM inseminations WHERE cow_id=? ORDER BY day DESC,id DESC', (cow_id,))]

    def delete_insemination(self, cow_id, day):
        self.get(cow_id)
        with self.db:
            removed = self.db.execute('DELETE FROM inseminations WHERE cow_id=? AND day=?', (cow_id,day))
            if not removed.rowcount:
                raise ValueError('Bu tohumlama kaydı artık bulunamıyor.')
            # Do not keep a birth schedule based on a date the user rejected,
            # or let startup migration recreate the deleted active date.
            self.db.execute("UPDATE cows SET insemination='',pregnant=0 WHERE id=? AND insemination=?", (cow_id,day))
            self.db.execute("DELETE FROM cycle_marks WHERE cow_id=? AND anchor=? AND kind IN ('heat','pregnancy','birth','dry')",(cow_id,day))

    def events(self, cow_id):
        return [dict(r) for r in self.db.execute('SELECT kind,day FROM events WHERE cow_id=? ORDER BY day DESC,id DESC', (cow_id,))]

    def move_record(self, cow_id, status, day, today=None):
        cow = self.get(cow_id)
        if status not in ('Aktif','Satıldı','Öldü','Arşiv'):
            raise ValueError('Geçerli bir kayıt durumu seçin.')
        day = parse_date(day)
        if not date.fromisoformat(cow['born']) <= day <= (today or date.today()):
            raise ValueError('İşlem tarihi doğumdan önce veya gelecekte olamaz.')
        if cow['status_date'] and day.isoformat() < cow['status_date']:
            raise ValueError('İşlem tarihi son arşiv işleminden önce olamaz.')
        if status == cow['record_status']: return
        with self.db:
            self.db.execute('UPDATE cows SET record_status=?,status_date=? WHERE id=?', (status,day.isoformat(),cow_id))
            self.db.execute('INSERT INTO events(cow_id,kind,day) VALUES (?,?,?)', (cow_id,status,day.isoformat()))

    def mark_dry(self, cow_id, day, today=None):
        cow = self.get(cow_id)
        if not due_date(cow): raise ValueError('Önce tarihli gebelik kaydı gerekli.')
        day = parse_date(day)
        if not date.fromisoformat(cow['insemination']) <= day <= (today or date.today()):
            raise ValueError('İşlem tarihi tohumlamadan önce veya gelecekte olamaz.')
        if cow['state'] == 'Kuru dönemde': return
        if cow['state'] != 'Sağmal':
            raise ValueError('Yalnızca sağmal hayvan kuruya ayrılabilir.')
        from corrections import snapshot,record
        before=snapshot(self.db,cow_id)
        with self.db:
            self.db.execute("UPDATE cows SET state='Kuru dönemde' WHERE id=?", (cow_id,))
            self.db.execute('INSERT INTO events(cow_id,kind,day) VALUES (?,?,?)', (cow_id,'Kuruya ayrıldı',day.isoformat()))
            record(self.db,cow_id,'Kuruya ayrıldı',before)

    def record_birth(self, cow_id, day, today=None, calves=None):
        cow = self.get(cow_id)
        if not can_reproduce(cow) or not cow['pregnant']:
            raise ValueError('Aktif gebelik kaydı gerekli.')
        day = parse_date(day)
        earliest = date.fromisoformat(cow['insemination'] or cow['born'])
        if not earliest <= day <= (today or date.today()):
            raise ValueError('Doğum tarihi kayıt başlangıcından önce veya gelecekte olamaz.')
        last_birth = self.db.execute("SELECT MAX(day) FROM events WHERE cow_id=? AND kind='Doğum yaptı'",(cow_id,)).fetchone()[0]
        if last_birth and day.isoformat() <= last_birth:
            raise ValueError('Yeni doğum tarihi önceki doğumdan sonra olmalı.')
        if calves is not None and (len(calves)>2 or any(sex not in ('Dişi','Erkek','Bilinmiyor') for sex in calves)):
            raise ValueError('Buzağı bilgisi geçersiz.')
        children=[]
        from corrections import snapshot,record
        before=snapshot(self.db,cow_id)
        with self.db:
            self.db.execute("UPDATE cows SET pregnant=0,insemination='',state='Sağmal',calved_before=1 WHERE id=?", (cow_id,))
            self.db.execute('INSERT INTO events(cow_id,kind,day) VALUES (?,?,?)', (cow_id,'Doğum yaptı',day.isoformat()))
            for sex in calves or []: children.append(self._insert_calf(cow,day,sex))
            record(self.db,cow_id,'Doğum yaptı',before)
        return children

    def register(self, info, gestation_days=283, initial=None):
        from animal_setup import validate
        setup=validate(info,initial)
        if not 250 <= int(gestation_days) <= 310:
            raise ValueError("Gebelik süresi 250–310 gün olmalı.")
        from registry import normalize_tag
        tag = normalize_tag(info['tag'])
        born = date.fromisoformat(info['born'])
        if born > date.today():
            raise ValueError('Doğum tarihi gelecekte olamaz.')
        try:
            with self.db:
                cursor = self.db.execute('''INSERT INTO cows
                    (tag,name,born,state,pregnant,insemination,gestation_days,notes,sex,breed,species,registry_status,vaccinations,checked_at)
                    VALUES (?,?,?,'Diğer',0,'',?,'',?,?,?,?,?,?)''',
                    (tag, '', born.isoformat(), int(gestation_days), info.get('sex','Bilinmiyor'), info.get('breed',''), info.get('species',''),
                     info.get('registry_status',''), json.dumps(info.get('vaccinations',[]),ensure_ascii=False), info.get('checked_at','')))
                cow_id=cursor.lastrowid
                if (date.today()-born).days<365:
                    self.db.execute('UPDATE cows SET calved_before=0 WHERE id=?',(cow_id,))
                if initial:
                    self.db.execute('UPDATE cows SET state=?,pregnant=?,insemination=?,calved_before=? WHERE id=?',
                        (setup['state'],setup['pregnant'],setup['insemination'],setup['calved_before'],cow_id))
                    if setup['insemination']:
                        self.db.execute('INSERT INTO inseminations(cow_id,day) VALUES (?,?)',(cow_id,setup['insemination']))
                    if setup['last_birth']:
                        self.db.execute("INSERT INTO events(cow_id,kind,day) VALUES (?,'Doğum yaptı',?)",(cow_id,setup['last_birth']))
                return cow_id
        except sqlite3.IntegrityError:
            raise ValueError('Bu küpe numarası zaten kayıtlı.') from None

    def sync(self, cow_id, info):
        cow = self.get(cow_id)
        if (cow['last_birth'] or self.children(cow_id)) and info.get('sex')!='Dişi':
            raise ValueError('Resmi cinsiyet doğum geçmişiyle çelişiyor; küpeyi kontrol et. Kayıt değişmedi.')
        if cow['tag'].upper() != info['tag'].upper():
            raise ValueError('Gelen küpe numarası kayıtla eşleşmiyor.')
        born = date.fromisoformat(info['born'])
        if cow['mother_id'] and born.isoformat()!=cow['born']:
            raise ValueError('Resmi doğum tarihi annesine bağlı doğum kaydıyla eşleşmiyor; küpeyi kontrol et.')
        if born > date.today():
            raise ValueError('Geçersiz doğum tarihi.')
        earliest = self.db.execute('SELECT MIN(day) FROM inseminations WHERE cow_id=?',(cow_id,)).fetchone()[0]
        if earliest and born.isoformat() > earliest:
            raise ValueError('Resmi doğum tarihi tohumlama geçmişiyle çelişiyor. Kayıt değişmedi.')
        first_event = self.db.execute('SELECT MIN(day) FROM events WHERE cow_id=?',(cow_id,)).fetchone()[0]
        if first_event and born.isoformat() > first_event:
            raise ValueError('Resmi doğum tarihi işlem geçmişiyle çelişiyor. Kayıt değişmedi.')
        with self.db:
            self.db.execute('''UPDATE cows SET born=?,sex=?,breed=?,species=?,registry_status=?,vaccinations=?,checked_at=? WHERE id=?''',
                            (born.isoformat(), info.get('sex','Bilinmiyor'), info.get('breed',''), info.get('species',''),
                             info.get('registry_status',''), json.dumps(info.get('vaccinations',[]),ensure_ascii=False),info.get('checked_at',''),cow_id))
            if not can_reproduce(info):
                self.db.execute("UPDATE cows SET pregnant=0,insemination='' WHERE id=?", (cow_id,))
            if info.get('sex') != 'Dişi' and cow['state'] in ('Sağmal','Kuru dönemde','Düve'):
                self.db.execute("UPDATE cows SET state='Diğer' WHERE id=?", (cow_id,))

    def set_photo(self, cow_id, path):
        self.get(cow_id)
        with self.db:
            self.db.execute('UPDATE cows SET photo_path=? WHERE id=?', (str(path), cow_id))

    def update_care(self, cow_id, name, state, notes):
        cow = self.get(cow_id)
        if state not in STATES:
            raise ValueError('Geçerli bir durum seçin.')
        if cow['sex'] != 'Dişi' and state in ('Sağmal','Kuru dönemde','Düve'):
            raise ValueError('Bu durum yalnızca cinsiyeti dişi olarak doğrulanan hayvanlar için kullanılabilir.')
        if (cow['calved_before']==1 or cow['last_birth'] or self.children(cow_id)) and state in ('Düve','Buzağı'):
            raise ValueError('Doğum yapmış hayvan düve veya buzağı olamaz.')
        with self.db:
            self.db.execute('UPDATE cows SET name=?,state=?,notes=? WHERE id=?', (name.strip(),state,notes.strip(),cow_id))
            if state in ('Sağmal','Kuru dönemde','Düve','Buzağı'):
                self.db.execute('UPDATE cows SET calved_before=? WHERE id=?',(int(state in ('Sağmal','Kuru dönemde')),cow_id))

    def save(self, values, cow_id=None, today=None):
        today = today or date.today()
        tag = values['tag'].strip()
        if not tag:
            raise ValueError('Küpe numarası gerekli.')
        born = parse_date(values['born'])
        if born > today:
            raise ValueError('Doğum tarihi gelecekte olamaz.')
        if values['state'] not in STATES:
            raise ValueError('Geçerli bir durum seçin.')
        pregnant = bool(values['pregnant'])
        ins = parse_date(values['insemination']) if values['insemination'].strip() else None
        current = self.get(cow_id) if cow_id is not None else values
        if (pregnant or ins) and not can_reproduce(current):
            raise ValueError(reproduction_reason(current))
        if ins and not born <= ins <= today:
            raise ValueError('Tohumlama tarihi doğumdan önce veya gelecekte olamaz.')
        if ins and cow_id is not None:
            last_birth = self.db.execute("SELECT MAX(day) FROM events WHERE cow_id=? AND kind='Doğum yaptı'",(cow_id,)).fetchone()[0]
            if last_birth and ins.isoformat() <= last_birth:
                raise ValueError('Yeni tohumlama son doğum tarihinden sonra olmalı.')
        try:
            duration = int(values['gestation_days'])
        except (ValueError, TypeError):
            raise ValueError('Gebelik süresini tam sayı olarak yazın.') from None
        if not 250 <= duration <= 310:
            raise ValueError('Hesaplama süresini 250–310 gün arasında girin.')
        row = (tag, values['name'].strip(), born.isoformat(), values['state'], int(pregnant), ins.isoformat() if ins else '', duration, values['notes'].strip())
        try:
            with self.db:
                if cow_id is None:
                    cursor = self.db.execute('INSERT INTO cows (tag,name,born,state,pregnant,insemination,gestation_days,notes,sex) VALUES (?,?,?,?,?,?,?,?,?)', row+(values.get('sex','Bilinmiyor'),))
                    cow_id = cursor.lastrowid
                else:
                    self.db.execute('UPDATE cows SET tag=?,name=?,born=?,state=?,pregnant=?,insemination=?,gestation_days=?,notes=? WHERE id=?', row+(cow_id,))
                if ins and current.get('insemination') != ins.isoformat():
                    self.db.execute('INSERT OR IGNORE INTO inseminations(cow_id,day) VALUES (?,?)', (cow_id,ins.isoformat()))
        except sqlite3.IntegrityError:
            raise ValueError('Bu küpe numarası zaten kayıtlı.') from None

    def update_reproduction(self, cow_id, day, pregnant, duration):
        cow = self.get(cow_id)
        if not can_reproduce(cow):
            raise ValueError(reproduction_reason(cow))
        parsed=parse_date(day).isoformat() if day.strip() else ''
        if cow.get('_loss_pending') and (parsed or pregnant):
            raise ValueError('Önce gebelik kaybı sonrası kontrol sonucunu kaydet.')
        previous=self.history(cow_id)
        if parsed and parsed!=cow['insemination'] and previous and parsed<=previous[0]:
            raise ValueError('Bu tarih önceki tohumlama kaydıyla çelişiyor; yanlış kaydı geçmişten silip düzelt.')
        values = cow | {'born': date.fromisoformat(cow['born']).strftime('%d.%m.%Y'),
                        'insemination': day, 'pregnant': pregnant, 'gestation_days': duration}
        self.save(values, cow_id)

    def close(self):
        self.db.close()
