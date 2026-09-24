from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import date
import unittest
from herd import Herd
from milk_store import MilkStore,litres,display
from backup_store import create_backup,restore_backup,SETTINGS
from cycle_settings import DEFAULT_CYCLE
from farm_settings import DEFAULT_FARM
from reminders import DEFAULT_SETTINGS

class MilkTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.root=Path(self.temp.name)
        self.herd=Herd(self.root/'suru.sqlite3'); self.store=MilkStore(self.herd.db)
        self.herd.save(dict(tag='TR123456789012',name='Test',born='01.01.2020',state='Sağmal',
            sex='Dişi',pregnant=False,insemination='',gestation_days=283,notes=''))
        self.day='2026-09-01'; self.today=date(2026,9,12)
    def tearDown(self): self.herd.close(); self.temp.cleanup()
    def save(self,mode='separate',**values):
        self.store.save(self.herd.get(1),self.day,mode,today=self.today,**values)
    def test_decimal_partial_and_update(self):
        self.save(morning='12,5')
        self.assertEqual(self.store.summary(self.day),(12500,1,1))
        self.save(morning='12.5',evening='10,25')
        self.assertEqual(self.store.summary(self.day),(22750,1,0))
        self.assertEqual(len(self.store.history(1)),1)
        self.assertEqual(display(22750),'22.75')
    def test_switching_mode_does_not_double_count(self):
        self.save(morning='10',evening='12')
        self.save('daily',daily='22')
        self.assertEqual(self.store.summary(self.day),(22000,1,0))
        self.assertIsNone(self.store.get(1,self.day)['morning'])
    def test_zero_is_recorded_empty_rejected(self):
        with self.assertRaises(ValueError): self.save()
        self.save('daily',daily='0')
        self.assertEqual(self.store.summary(self.day),(0,1,0))
        for invalid in ('-1','NaN','1.0001','1000','abc'):
            with self.assertRaises(ValueError): litres(invalid)
    def test_dry_no_new_record_but_history_editable(self):
        self.save('daily',daily='20')
        with self.herd.db: self.herd.db.execute("UPDATE cows SET state='Kuru dönemde' WHERE id=1")
        self.save('daily',daily='21')
        self.day='2026-09-02'
        with self.assertRaises(ValueError): self.save('daily',daily='10')
    def test_dates_and_delete(self):
        self.day='2026-09-13'
        with self.assertRaises(ValueError): self.save('daily',daily='10')
        self.day='2026-09-01'; self.save('daily',daily='10')
        self.store.delete(1,self.day)
        self.assertEqual(self.store.summary(self.day),(0,0,0))
    def test_backup_and_animal_deletion(self):
        self.save(morning='10',evening='11')
        prefs=dict(zip(SETTINGS,(DEFAULT_FARM,DEFAULT_CYCLE,DEFAULT_SETTINGS)))
        archive=create_backup(self.herd,self.root/'exports',prefs)
        self.herd.delete(1)
        self.assertEqual(self.store.summary(self.day),(0,0,0))
        restore_backup(self.herd,self.root,archive,prefs)
        self.assertEqual(self.store.summary(self.day),(21000,1,0))
