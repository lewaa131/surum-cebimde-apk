"""Portable, verified herd backups. No archive paths are extracted directly."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
from uuid import uuid4
from datetime import datetime, date
import hashlib
import json
import shutil
import sqlite3
from cycle_settings import validate_cycle
from farm_settings import validate_farm
from reminders import validate_settings

LIMIT = 512 * 1024 * 1024
SETTINGS = ('farm-settings.json', 'cycle-settings.json', 'reminder-settings.json')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_preferences(values):
    if set(values) != set(SETTINGS): raise ValueError('Yedekte ayarlar eksik.')
    return {
        SETTINGS[0]: validate_farm(values[SETTINGS[0]]),
        SETTINGS[1]: validate_cycle(values[SETTINGS[1]]),
        SETTINGS[2]: validate_settings(values[SETTINGS[2]]['dry_days'], values[SETTINGS[2]]['time']),
    }


def create_backup(herd, folder, preferences):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    preferences=validate_preferences(preferences)
    target=folder/('Surum-Cebimde-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid4().hex[:6]+'.zip')
    partial=target.with_suffix('.tmp')
    try:
        with TemporaryDirectory(dir=folder) as temporary:
            dbpath=Path(temporary)/'suru.sqlite3'
            db=sqlite3.connect(dbpath)
            try:
                herd.db.backup(db)
                photos={}
                for cow_id,source in db.execute('SELECT id,photo_path FROM cows').fetchall():
                    if not source: continue
                    source=Path(source)
                    if not source.is_file(): raise ValueError('Bir hayvanın fotoğrafı bulunamadı; yedek tamamlanamadı.')
                    photos['photos/'+str(cow_id)+'.image']=source
                    db.execute('UPDATE cows SET photo_path=? WHERE id=?',('photos/'+str(cow_id)+'.image',cow_id))
                db.commit()
                count=db.execute('SELECT COUNT(*) FROM cows').fetchone()[0]
            finally: db.close()
            with ZipFile(partial,'w',ZIP_DEFLATED) as archive:
                hashes={}; total=0
                for name,path in {'suru.sqlite3':dbpath,**photos}.items():
                    total+=path.stat().st_size
                    if total>LIMIT: raise ValueError('Yedek 512 MB sınırını aşıyor.')
                    data=path.read_bytes(); hashes[name]=digest(data); archive.writestr(name,data)
                for name,value in preferences.items():
                    data=json.dumps(value,ensure_ascii=False).encode('utf-8')
                    hashes[name]=digest(data); archive.writestr(name,data)
                archive.writestr('manifest.json',json.dumps(dict(format='surum-backup',version=1,
                    created=datetime.now().isoformat(timespec='seconds'),animals=count,files=hashes)))
        partial.replace(target)
        return target
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def read_backup(path, staging):
    """Validate completely before showing confirmation or touching live data."""
    staging=Path(staging)
    if Path(path).stat().st_size>LIMIT: raise ValueError('Yedek çok büyük.')
    with ZipFile(path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)) or len(names)>20000 or sum(i.file_size for i in archive.infolist())>LIMIT:
            raise ValueError('Yedek boyutu veya içeriği geçersiz.')
        if archive.getinfo('manifest.json').file_size>2*1024*1024: raise ValueError('Yedek başlığı geçersiz.')
        manifest=json.loads(archive.read('manifest.json'))
        if manifest.get('format')!='surum-backup' or manifest.get('version')!=1:
            raise ValueError('Bu dosya desteklenen bir Sürüm Cebimde yedeği değil.')
        datetime.fromisoformat(manifest['created'])
        hashes=manifest['files']
        if set(names)!=set(hashes)|{'manifest.json'} or not {'suru.sqlite3',*SETTINGS}<=set(hashes):
            raise ValueError('Yedek dosyaları eksik.')
        photos={}; preferences={}
        for index,(name,expected) in enumerate(hashes.items()):
            data=archive.read(name)
            if digest(data)!=expected: raise ValueError('Yedek hasarlı; hiçbir kayıt değiştirilmedi.')
            if name in SETTINGS: preferences[name]=json.loads(data)
            elif name=='suru.sqlite3': (staging/'suru.sqlite3').write_bytes(data)
            elif name.startswith('photos/') and name.count('/')==1 and '\\' not in name:
                local=staging/('photo-'+str(index)); local.write_bytes(data)
                from PIL import Image
                with Image.open(local) as image:
                    if image.width*image.height>40_000_000: raise ValueError('Yedekte fotoğraf çok büyük.')
                    image.verify()
                photos[name]=local
            else: raise ValueError('Yedekte tanınmayan dosya var.')
    preferences=validate_preferences(preferences)
    db=sqlite3.connect(staging/'suru.sqlite3')
    try:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Hayvan kayıtları hasarlı.')
        from herd import Herd
        template=Herd(':memory:')
        try:
            for table in ('cows','events','inseminations','cycle_marks'):
                required={r[1] for r in template.db.execute('PRAGMA table_info('+table+')')}
                actual={r[1] for r in db.execute('PRAGMA table_info('+table+')')}
                if not required<=actual: raise ValueError('Yedek kayıt yapısı uyumsuz.')
        finally: template.close()
        if db.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger','view') LIMIT 1").fetchone():
            raise ValueError('Yedek kayıt yapısı desteklenmiyor.')
        for table in ('events','inseminations','cycle_marks'):
            if db.execute('SELECT 1 FROM '+table+' WHERE cow_id NOT IN (SELECT id FROM cows) LIMIT 1').fetchone():
                raise ValueError('Yedekte hayvan bağlantısı eksik.')
        if db.execute('SELECT 1 FROM cows WHERE mother_id IS NOT NULL AND mother_id NOT IN (SELECT id FROM cows) LIMIT 1').fetchone():
            raise ValueError('Yedekte anne bağlantısı eksik.')
        for table in ('events','inseminations'):
            for row in db.execute('SELECT day FROM '+table): date.fromisoformat(row[0])
        from milk_store import MilkStore
        MilkStore(db)  # Older backups predate milk tracking; restore an empty milk table.
        from corrections import init
        init(db)
        # Undo snapshots refer to the original device and exact record state.
        db.execute('DELETE FROM corrections'); db.commit()
        if db.execute('SELECT 1 FROM milk WHERE cow_id NOT IN (SELECT id FROM cows) LIMIT 1').fetchone():
            raise ValueError('Süt kaydının hayvanı eksik.')
        for row in db.execute('SELECT day,mode,morning,evening,daily FROM milk'):
            date.fromisoformat(row[0])
            if row[1] not in ('daily','separate') or any(v is not None and (type(v)!=int or not 0<=v<=999000) for v in row[2:]):
                raise ValueError('Yedekte süt miktarı geçersiz.')
        count=0
        for born,ins,path in db.execute('SELECT born,insemination,photo_path FROM cows'):
            date.fromisoformat(born)
            if ins: date.fromisoformat(ins)
            if path and path not in photos: raise ValueError('Yedekte fotoğraf eksik.')
            count+=1
        if count!=manifest['animals']: raise ValueError('Yedek hayvan sayısı uyuşmuyor.')
    finally: db.close()
    return dict(animals=count,created=manifest['created'],preferences=preferences,photos=photos)


def restore_backup(herd, root, path, current_preferences):
    root=Path(root)
    with TemporaryDirectory(dir=root) as temporary:
        stage=Path(temporary)
        info=read_backup(path,stage)
        safety=create_backup(herd,root/'backups',current_preferences)
        rollback=sqlite3.connect(stage/'rollback.sqlite3')
        incoming=sqlite3.connect(stage/'suru.sqlite3')
        old={name:(root/name).read_bytes() if (root/name).exists() else None for name in SETTINGS}
        added=[]; rollback_ready=False
        try:
            herd.db.backup(rollback)
            rollback_ready=True
            photo_folder=root/'photos'; photo_folder.mkdir(exist_ok=True)
            for relative,source in info['photos'].items():
                destination=photo_folder/(uuid4().hex+'.jpg')
                added.append(destination); shutil.copyfile(source,destination)
                incoming.execute('UPDATE cows SET photo_path=? WHERE photo_path=?',(str(destination),relative))
            incoming.commit()
            for name,value in info['preferences'].items():
                temp=root/(name+'.restore-tmp')
                temp.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8'); temp.replace(root/name)
            incoming.backup(herd.db)
        except Exception:
            if rollback_ready: rollback.backup(herd.db)
            for name,data in old.items():
                if data is None: (root/name).unlink(missing_ok=True)
                else: (root/name).write_bytes(data)
            for file in added: file.unlink(missing_ok=True)
            raise
        finally:
            incoming.close(); rollback.close()
            for name in SETTINGS: (root/(name+'.restore-tmp')).unlink(missing_ok=True)
    return safety,info
