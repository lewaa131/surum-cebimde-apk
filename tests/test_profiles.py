import sqlite3
import tempfile
import unittest
from pathlib import Path
from herd import Herd, can_reproduce, due_date

INFO = dict(tag='TR350004339192',born='2022-08-26',sex='Dişi',breed='Holstein-SA',species='Sığır',registry_status='Canlı',vaccinations=[],checked_at='2026-09-09T15:00:00')

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name)/'herd.db'; self.herd = Herd(self.path)
    def tearDown(self):
        self.herd.close(); self.tmp.cleanup()

    def test_add_only_registry_then_record_insemination(self):
        key = self.herd.register(INFO)
        cow = self.herd.get(key)
        self.assertEqual(cow['insemination'],''); self.assertFalse(cow['pregnant'])
        self.herd.update_reproduction(key,'01.01.2026',True,'283')
        self.assertIsNotNone(due_date(self.herd.get(key)))
        self.assertEqual(self.herd.history(key),['2026-01-01'])

    def test_male_unknown_dead_blocked_in_storage(self):
        for sex,status in [('Erkek','Canlı'),('Bilinmiyor','Canlı'),('','Canlı'),('Dişi','Ölü')]:
            with self.subTest(sex=sex,status=status):
                key = self.herd.register(INFO | {'tag':f'TR{len(self.herd.all()):012d}','sex':sex,'registry_status':status})
                for day,pregnant in [('01.01.2026',False),('',True)]:
                    with self.assertRaises(ValueError): self.herd.update_reproduction(key,day,pregnant,'283')
                self.assertFalse(can_reproduce(self.herd.get(key)))
                self.assertEqual(self.herd.history(key),[])

    def test_cannot_spoof_sex_via_edit(self):
        key = self.herd.register(INFO | {'sex':'Erkek'})
        values = self.herd.get(key) | {'sex':'Dişi','born':'26.08.2022','pregnant':True}
        with self.assertRaises(ValueError): self.herd.save(values,key)

    def test_history_preserved_and_no_duplicate_on_unchanged_save(self):
        key = self.herd.register(INFO)
        self.herd.update_reproduction(key,'01.01.2026',False,'283')
        self.herd.update_reproduction(key,'01.01.2026',True,'283')
        self.herd.update_reproduction(key,'01.02.2026',False,'283')
        self.herd.update_reproduction(key,'',False,'283')
        self.assertEqual(self.herd.history(key),['2026-02-01','2026-01-01'])

    def test_sync_preserves_care_and_photo_clears_invalid_active_reproduction(self):
        key = self.herd.register(INFO)
        self.herd.update_care(key,'Pamuk','Sağmal','Özel not')
        self.herd.set_photo(key,'photo.jpg')
        self.herd.update_reproduction(key,'01.01.2026',True,'283')
        self.herd.sync(key,INFO | {'sex':'Erkek'})
        cow = self.herd.get(key)
        self.assertEqual((cow['name'],cow['notes'],cow['photo_path']),('Pamuk','Özel not','photo.jpg'))
        self.assertFalse(cow['pregnant']); self.assertEqual(cow['insemination'],'')
        self.assertEqual(self.herd.history(key),['2026-01-01'])
        with self.assertRaises(ValueError): self.herd.update_care(key,'Pamuk','Sağmal','')

    def test_duplicate_and_mismatching_sync(self):
        key = self.herd.register(INFO)
        with self.assertRaises(ValueError): self.herd.register(INFO)
        with self.assertRaises(ValueError): self.herd.sync(key,INFO | {'tag':'TR000000000000'})
        self.assertEqual(self.herd.get(key)['tag'],INFO['tag'])

    def test_legacy_migration_keeps_records_and_history(self):
        self.herd.close()
        old = Path(self.tmp.name)/'legacy.db'
        with sqlite3.connect(old) as db:
            db.execute('CREATE TABLE cows(id INTEGER PRIMARY KEY,tag TEXT UNIQUE,name TEXT,born TEXT,state TEXT,pregnant INTEGER,insemination TEXT,gestation_days INTEGER,notes TEXT)')
            db.execute("INSERT INTO cows VALUES(1,'TR350004339192','Pamuk','2022-08-26','Sağmal',1,'2026-01-01',283,'Eski not')")
        db.close()
        self.herd = Herd(old)
        self.assertEqual(self.herd.get(1)['notes'],'Eski not')
        self.assertEqual(self.herd.get(1)['sex'],'Bilinmiyor')
        self.assertIsNone(due_date(self.herd.get(1)))
        self.assertEqual(self.herd.history(1),['2026-01-01'])
