from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED
from unittest.mock import patch
import json
import unittest
from PIL import Image
from herd import Herd
from cycle_settings import DEFAULT_CYCLE
from farm_settings import DEFAULT_FARM
from reminders import DEFAULT_SETTINGS
from backup_store import create_backup, read_backup, restore_backup, SETTINGS


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.root=Path(self.temp.name)
        self.herd=Herd(self.root/'suru.sqlite3')
        self.prefs=dict(zip(SETTINGS,(dict(DEFAULT_FARM),dict(DEFAULT_CYCLE),dict(DEFAULT_SETTINGS))))
        self.herd.save(dict(tag='TR000000000001',name='Pamuk',born='01.01.2020',state='Sağmal',
            pregnant=False,insemination='',gestation_days=283,notes='Notum',sex='Dişi'))
        self.photo=self.root/'original.png'; Image.new('RGB',(20,30),'green').save(self.photo)
        self.herd.set_photo(1,str(self.photo))
        with self.herd.db:
            self.herd.db.execute("INSERT INTO events(cow_id,kind,day) VALUES (1,'Doğum yaptı','2025-01-01')")
            self.herd.db.execute("INSERT INTO cycle_marks(cow_id,kind,anchor,done_day) VALUES (1,'fresh','2025-01-01','2025-03-01')")

    def tearDown(self):
        self.herd.close(); self.temp.cleanup()

    def test_roundtrip_new_phone_and_safety_backup(self):
        backup=create_backup(self.herd,self.root/'exports',self.prefs)
        self.herd.db.execute("UPDATE cows SET name='Changed'"); self.herd.db.commit()
        safety,info=restore_backup(self.herd,self.root,backup,self.prefs)
        self.assertEqual(self.herd.get(1)['name'],'Pamuk')
        photo=Path(self.herd.get(1)['photo_path'])
        self.assertEqual(photo.parent,self.root/'photos')
        self.assertEqual(photo.read_bytes(),self.photo.read_bytes())
        self.assertEqual(self.herd.get(1)['last_birth'],'2025-01-01')
        self.assertEqual(len(self.herd.get(1)['_cycle_marks']),1)
        self.assertEqual(info['animals'],1)
        self.assertEqual(json.loads((self.root/SETTINGS[1]).read_text()),self.prefs[SETTINGS[1]])
        # The safety archive contains the replaced state, not the imported state.
        restore_backup(self.herd,self.root,safety,self.prefs)
        self.assertEqual(self.herd.get(1)['name'],'Changed')

    def test_corrupt_archive_leaves_live_data(self):
        backup=create_backup(self.herd,self.root/'exports',self.prefs)
        damaged=self.root/'damaged.zip'
        with ZipFile(backup) as source, ZipFile(damaged,'w',ZIP_DEFLATED) as dest:
            for name in source.namelist():
                dest.writestr(name,b'broken' if name=='suru.sqlite3' else source.read(name))
        with self.assertRaises(ValueError): restore_backup(self.herd,self.root,damaged,self.prefs)
        self.assertEqual(self.herd.get(1)['name'],'Pamuk')
        self.assertFalse((self.root/'backups').exists())

    def test_partial_settings_failure_rolls_back(self):
        backup=create_backup(self.herd,self.root/'exports',self.prefs)
        self.herd.db.execute("UPDATE cows SET name='Current'"); self.herd.db.commit()
        old=dict(DEFAULT_FARM,fresh_days=80)
        (self.root/SETTINGS[0]).write_text(json.dumps(old))
        replace=Path.replace
        def failure(path,target):
            if path.name==SETTINGS[1]+'.restore-tmp': raise OSError('disk error')
            return replace(path,target)
        with patch.object(Path,'replace',failure):
            with self.assertRaises(OSError): restore_backup(self.herd,self.root,backup,self.prefs)
        self.assertEqual(self.herd.get(1)['name'],'Current')
        self.assertEqual(json.loads((self.root/SETTINGS[0]).read_text()),old)
        self.assertEqual(list((self.root/'photos').iterdir()),[])

    def test_missing_photo_does_not_create_incomplete_backup(self):
        self.photo.unlink()
        with self.assertRaises(ValueError): create_backup(self.herd,self.root/'exports',self.prefs)
        self.assertEqual(list((self.root/'exports').iterdir()),[])

    def test_unknown_archive_path_rejected(self):
        backup=create_backup(self.herd,self.root/'exports',self.prefs)
        with ZipFile(backup,'a') as archive: archive.writestr('../outside','bad')
        with TemporaryDirectory(dir=self.root) as stage:
            with self.assertRaises(ValueError): read_backup(backup,stage)
        self.assertFalse((self.root/'outside').exists())

    def test_empty_herd(self):
        self.herd.delete(1)
        backup=create_backup(self.herd,self.root/'exports',self.prefs)
        with TemporaryDirectory(dir=self.root) as stage:
            self.assertEqual(read_backup(backup,stage)['animals'],0)

    def test_restore_on_different_phone_without_original_photo(self):
        backup=create_backup(self.herd,self.root/'exports',self.prefs)
        photo_bytes=self.photo.read_bytes(); self.photo.unlink()
        other=self.root/'new-phone'; other.mkdir()
        destination=Herd(other/'suru.sqlite3')
        try:
            restore_backup(destination,other,backup,self.prefs)
            path=Path(destination.get(1)['photo_path'])
            self.assertEqual(path.parent,other/'photos')
            self.assertEqual(path.read_bytes(),photo_bytes)
        finally: destination.close()


if __name__=='__main__': unittest.main()
