"""Confirmed cycle events and calf links, stored alongside the existing herd."""
from datetime import date, timedelta
import uuid


class CycleStore:
    def init_cycle(self):
        columns={r['name'] for r in self.db.execute('PRAGMA table_info(cows)')}
        if 'calved_before' not in columns and self.db.execute('SELECT COUNT(*) FROM cows').fetchone()[0]:
            from pathlib import Path
            import sqlite3
            filename=self.db.execute('PRAGMA database_list').fetchone()['file']
            if filename:
                backup=Path(filename).with_suffix('.pre-cycle.sqlite3')
                if not backup.exists():
                    destination=sqlite3.connect(str(backup))
                    try: self.db.backup(destination)
                    finally: destination.close()
        with self.db:
            for key,definition in [('calved_before','INTEGER NOT NULL DEFAULT -1'),
                                   ('mother_id','INTEGER'),('local_tag','INTEGER NOT NULL DEFAULT 0')]:
                if key not in columns: self.db.execute(f'ALTER TABLE cows ADD COLUMN {key} {definition}')
            if 'calved_before' not in columns:
                self.db.execute("UPDATE cows SET calved_before=1 WHERE sex='Dişi' AND (state IN ('Sağmal','Kuru dönemde') OR id IN (SELECT cow_id FROM events WHERE kind='Doğum yaptı'))")
                self.db.execute("UPDATE cows SET calved_before=0 WHERE calved_before=-1 AND (state IN ('Düve','Buzağı') OR born>date('now','-365 days'))")
            self.db.execute('''CREATE TABLE IF NOT EXISTS cycle_marks (
                cow_id INTEGER NOT NULL, kind TEXT NOT NULL, anchor TEXT NOT NULL,
                done_day TEXT NOT NULL DEFAULT '', snooze_until TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(cow_id,kind,anchor))''')

    def cycle_data(self, cow):
        cow['_loss_day']=self.db.execute("SELECT MAX(day) FROM events WHERE cow_id=? AND kind IN ('Gebelik kaybı','Düşük')",(cow['id'],)).fetchone()[0] or ''
        cow['_recovery_day']=self.db.execute("SELECT MAX(day) FROM events WHERE cow_id=? AND kind='Kayıp sonrası kontrol edildi'",(cow['id'],)).fetchone()[0] or ''
        loss_id=self.db.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE cow_id=? AND kind IN ('Gebelik kaybı','Düşük')",(cow['id'],)).fetchone()[0]
        resolved_id=self.db.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE cow_id=? AND kind IN ('Kayıp sonrası kontrol edildi','Doğum yaptı')",(cow['id'],)).fetchone()[0]
        cow['_loss_pending']=loss_id>resolved_id
        cow['last_birth']=self.db.execute("SELECT MAX(day) FROM events WHERE cow_id=? AND kind='Doğum yaptı'",(cow['id'],)).fetchone()[0] or ''
        cow['_cycle_marks']=[dict(r) for r in self.db.execute('SELECT * FROM cycle_marks WHERE cow_id=?',(cow['id'],))]
        if cow['last_birth'] or (cow['calved_before']==-1 and cow['state'] in ('Sağmal','Kuru dönemde') and cow['sex']=='Dişi'):
            cow['calved_before']=1
        elif cow['calved_before']==-1 and cow['state'] in ('Düve','Buzağı'):
            cow['calved_before']=0
        return cow

    def _insert_calf(self, mother, day, sex):
        tag='BUZ-'+uuid.uuid4().hex[:12].upper()
        cursor=self.db.execute('''INSERT INTO cows
            (tag,name,born,state,pregnant,insemination,gestation_days,notes,sex,breed,species,
             registry_status,calved_before,mother_id,local_tag)
            VALUES (?,?,?,'Buzağı',0,'',?,'',?,?,?,'Canlı',0,?,1)''',
            (tag,(mother['name'] or 'Hayvan')+' buzağısı',day.isoformat(),mother['gestation_days'],
             sex,mother['breed'],mother['species'],mother['id']))
        return cursor.lastrowid

    def children(self, cow_id):
        return [self.cycle_data(dict(r)) for r in self.db.execute('SELECT * FROM cows WHERE mother_id=? ORDER BY born DESC,id',(cow_id,))]

    def assign_calf_identity(self,cow_id,tag,sex):
        from registry import normalize_tag
        cow=self.get(cow_id)
        if not cow['local_tag'] and not cow['mother_id']: raise ValueError('Bu hayvanın küpesi zaten kayıtlı.')
        if sex not in ('Dişi','Erkek','Bilinmiyor'): raise ValueError('Cinsiyet seçimi geçersiz.')
        if (cow['last_birth'] or cow['insemination'] or cow['pregnant']) and sex!='Dişi':
            raise ValueError('Üreme kaydıyla cinsiyet çelişiyor; önce ilgili kaydı kontrol et.')
        tag=normalize_tag(tag) if tag.strip() else cow['tag']
        if tag!=cow['tag'] and self.db.execute('SELECT id FROM cows WHERE tag=? COLLATE NOCASE',(tag,)).fetchone():
            raise ValueError('Bu küpe zaten sürüde; ikinci kayıt oluşturulmadı.')
        with self.db:
            self.db.execute('UPDATE cows SET tag=?,sex=?,local_tag=? WHERE id=?',(tag,sex,int(tag.startswith('BUZ-')),cow_id))

    def set_birth_history(self,cow_id,calved,day='',today=None):
        from herd import can_reproduce,parse_date
        cow=self.get(cow_id); today=today or date.today()
        if not can_reproduce(cow): raise ValueError('Bu hayvanda üreme takibi kapalı.')
        if not calved and (cow['last_birth'] or self.children(cow_id)):
            raise ValueError('Kayıtlı doğumu olan hayvan düve olarak işaretlenemez.')
        born=date.fromisoformat(cow['born'])
        parsed=parse_date(day) if day.strip() else None
        if parsed and not born<parsed<=today: raise ValueError('Son doğum tarihi hayvanın doğumundan sonra ve bugün veya önce olmalı.')
        if parsed and cow['insemination'] and parsed.isoformat()>=cow['insemination']:
            raise ValueError('Son doğum, aktif tohumlamadan önce olmalı.')
        if cow['last_birth']:
            raise ValueError('Son doğum zaten kayıtlı; yeni doğum için Doğdu işlemini kullan.')
        with self.db:
            self.db.execute('UPDATE cows SET calved_before=?,state=? WHERE id=?',
                (int(calved),'Sağmal' if calved and cow['state']!='Kuru dönemde' else 'Kuru dönemde' if calved else 'Düve',cow_id))
            if calved and parsed:
                self.db.execute("INSERT INTO events(cow_id,kind,day) VALUES (?,'Doğum yaptı',?)",(cow_id,parsed.isoformat()))

    def cycle_mark(self,cow_id,kind,anchor,settings,snooze=False,today=None,heat_observed=False):
        from lifecycle import snapshot
        today=today or date.today()
        cow=self.get(cow_id)
        task=next((t for t in snapshot(cow,settings,today)['tasks'] if t['kind']==kind and t['anchor']==anchor),None)
        if not task: raise ValueError('Bu görev güncellendi; listeyi yeniden aç.')
        if not snooze and kind not in ('weaning','heat','fresh'): raise ValueError('Bu işlem için sonuç kaydı gerekli.')
        from corrections import snapshot,record
        before=snapshot(self.db,cow_id)
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO cycle_marks(cow_id,kind,anchor,done_day,snooze_until) VALUES (?,?,?,?,?)',
                (cow_id,kind,anchor,'' if snooze else today.isoformat(),(today+timedelta(days=1)).isoformat() if snooze else ''))
            if not snooze:
                title={'weaning':'Sütten kesildi','heat':'Kızgınlık gözlendi' if heat_observed else 'Kızgınlık gözlenmedi','fresh':'Yeni doğuran kontrolü yapıldı'}[kind]
                self.db.execute('INSERT INTO events(cow_id,kind,day) VALUES (?,?,?)',(cow_id,title,today.isoformat()))
                record(self.db,cow_id,title,before)

    def pregnancy_result(self,cow_id,confirmed,expected_ins,today=None):
        from herd import can_reproduce
        today=today or date.today()
        cow=self.get(cow_id)
        if not can_reproduce(cow) or not cow['insemination'] or cow['insemination']!=expected_ins:
            raise ValueError('Aktif tohumlama değişti; kaydı yeniden aç.')
        if today.isoformat()<expected_ins: raise ValueError('Kontrol tarihi tohumlamadan önce olamaz.')
        if confirmed and cow['pregnant']: return
        from corrections import snapshot,record
        before=snapshot(self.db,cow_id)
        with self.db:
            self.db.execute('UPDATE cows SET pregnant=?,insemination=? WHERE id=?',
                (int(confirmed),expected_ins if confirmed else '',cow_id))
            self.db.execute('INSERT INTO events(cow_id,kind,day) VALUES (?,?,?)',
                (cow_id,('Gebelik doğrulandı' if confirmed else 'Gebe değil')+' · '+expected_ins,today.isoformat()))
            record(self.db,cow_id,'Gebelik sonucu',before)

    def record_insemination(self,cow_id,day,settings,today=None):
        from herd import parse_date
        today=today or date.today()
        cow=self.get(cow_id)
        if cow['pregnant']: raise ValueError('Önce mevcut gebeliğin doğum veya kontrol sonucunu kaydet.')
        if cow.get('_loss_pending'): raise ValueError('Önce gebelik kaybı sonrası kontrol sonucunu kaydet.')
        parsed=parse_date(day)
        previous=self.history(cow_id)
        if previous and parsed.isoformat()<=previous[0]:
            raise ValueError('Yeni tohumlama geçmişteki son kayıttan sonra olmalı; yanlış tarihi geçmişten silip düzelt.')
        values=cow|dict(born=date.fromisoformat(cow['born']).strftime('%d.%m.%Y'),
            insemination=day,pregnant=False,gestation_days=settings['gestation_days'])
        self.save(values,cow_id,today=today)
