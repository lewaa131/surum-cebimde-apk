"""Undo confirmed events only when their dependent records are unchanged."""
import json
from datetime import date

def init(db):
    db.execute('CREATE TABLE IF NOT EXISTS corrections (id INTEGER PRIMARY KEY, cow_id INTEGER NOT NULL, title TEXT NOT NULL, before_json TEXT NOT NULL, after_json TEXT NOT NULL)')

def snapshot(db,cow_id):
    ids=[r[0] for r in db.execute('SELECT id FROM cows WHERE id=? OR mother_id=? ORDER BY id',(cow_id,cow_id))]
    result={}
    for table,column in [('cows','id'),('events','cow_id'),('inseminations','cow_id'),('cycle_marks','cow_id'),('milk','cow_id')]:
        rows=[]
        for i in ids: rows.extend(dict(r) for r in db.execute('SELECT * FROM '+table+' WHERE '+column+'=? ORDER BY rowid',(i,)))
        result[table]=rows
    return result

def record(db,cow_id,title,before):
    after=snapshot(db,cow_id)
    if before!=after:
        db.execute('INSERT INTO corrections(cow_id,title,before_json,after_json) VALUES (?,?,?,?)',
            (cow_id,title,json.dumps(before),json.dumps(after)))

def undo(herd,correction_id):
    row=herd.db.execute('SELECT * FROM corrections WHERE id=?',(correction_id,)).fetchone()
    if not row: raise ValueError('İşlem artık geri alınabilir değil.')
    before=json.loads(row['before_json']); after=json.loads(row['after_json'])
    cow_id=row['cow_id']
    if snapshot(herd.db,cow_id)!=after:
        raise ValueError('Bu işlemden sonra hayvanda veya bağlı buzağıda değişiklik var. Önce sonraki işlemi düzelt.')
    existing={r['id'] for r in before['cows']}
    added=[r['id'] for r in after['cows'] if r['id'] not in existing]
    for i in added:
        if herd.db.execute('SELECT 1 FROM cows WHERE mother_id=?',(i,)).fetchone():
            raise ValueError('Buzağıya bağlı başka kayıt var; doğum geri alınamaz.')
    ids=[r['id'] for r in after['cows']]
    with herd.db:
        for table,column in [('events','cow_id'),('inseminations','cow_id'),('cycle_marks','cow_id'),('milk','cow_id')]:
            for i in ids: herd.db.execute('DELETE FROM '+table+' WHERE '+column+'=?',(i,))
            for data in before[table]:
                columns=list(data)
                herd.db.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',tuple(data.values()))
        for i in added:
            herd.db.execute('DELETE FROM cows WHERE id=?',(i,))
            herd.db.execute('DELETE FROM corrections WHERE cow_id=?',(i,))
        for data in before['cows']:
            columns=[key for key in data if key!='id']
            herd.db.execute('UPDATE cows SET '+','.join(key+'=?' for key in columns)+' WHERE id=?',
                tuple(data[key] for key in columns)+(data['id'],))
        herd.db.execute('DELETE FROM corrections WHERE id=?',(correction_id,))

def loss(herd,cow_id,day,reason,today=None):
    from herd import can_reproduce,parse_date
    cow=herd.get(cow_id); parsed=parse_date(day); today=today or date.today()
    if reason not in ('Gebelik kaybı','Düşük'): raise ValueError('Kayıp türünü seç.')
    if not can_reproduce(cow) or not cow['pregnant']: raise ValueError('Aktif gebelik kaydı gerekli.')
    if not date.fromisoformat(cow['insemination'] or cow['born'])<=parsed<=today:
        raise ValueError('Tarih gebelik başlangıcından önce veya gelecekte olamaz.')
    before=snapshot(herd.db,cow_id)
    with herd.db:
        herd.db.execute("UPDATE cows SET pregnant=0,insemination='' WHERE id=?",(cow_id,))
        herd.db.execute('INSERT INTO events(cow_id,kind,day) VALUES (?,?,?)',(cow_id,reason,parsed.isoformat()))
        record(herd.db,cow_id,reason,before)
