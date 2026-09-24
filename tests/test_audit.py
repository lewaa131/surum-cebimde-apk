from datetime import date
from pathlib import Path
import tempfile
import unittest
from herd import Herd
from photos import remove_unused_photo


class AuditRegressionTests(unittest.TestCase):
    def test_birth_date_sync_checks_events_after_history_deleted(self):
        self.herd.record_birth(self.id,'01.08.2026',today=date(2026,9,9))
        self.herd.delete_insemination(self.id,'2026-01-01')
        before=self.herd.get(self.id)
        with self.assertRaises(ValueError):
            self.herd.sync(self.id,{'tag':before['tag'],'born':'2026-08-15','sex':'Dişi'})
        self.assertEqual(self.herd.get(self.id),before)

    def test_unknown_insemination_cannot_backdate_birth_before_last_birth(self):
        self.herd.record_birth(self.id,'01.08.2026',today=date(2026,9,9))
        self.herd.update_reproduction(self.id,'',True,283)
        before=self.herd.events(self.id)
        for day in ('01.07.2026','01.08.2026'):
            with self.assertRaises(ValueError): self.herd.record_birth(self.id,day,today=date(2026,9,9))
        self.assertEqual(self.herd.events(self.id),before)
        self.assertTrue(self.herd.get(self.id)['pregnant'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'herd.db'
        self.herd = Herd(self.path)
        self.herd.save(dict(tag='TR000000000001',name='Pamuk',born='01.01.2020',
            state='Sağmal',pregnant=True,insemination='01.01.2026',gestation_days=283,
            notes='',sex='Dişi'),today=date(2026,9,9))
        self.id = self.herd.all()[0]['id']

    def tearDown(self):
        self.herd.close()
        self.temp.cleanup()

    def test_revisiting_insemination_date_does_not_duplicate_history(self):
        self.herd.update_reproduction(self.id,'01.02.2026',False,283)
        with self.assertRaises(ValueError):
            self.herd.update_reproduction(self.id,'01.01.2026',True,283)
        self.assertEqual(self.herd.get(self.id)['insemination'],'2026-02-01')
        self.assertEqual(self.herd.history(self.id),['2026-02-01','2026-01-01'])

    def test_new_pregnancy_cannot_start_before_recorded_birth(self):
        self.herd.record_birth(self.id,'01.09.2026',today=date(2026,9,9))
        for day in ('31.08.2026','01.09.2026'):
            with self.assertRaises(ValueError): self.herd.update_reproduction(self.id,day,True,283)
        self.assertEqual(self.herd.get(self.id)['pregnant'],0)

    def test_archive_cannot_be_restored_before_sale(self):
        self.herd.move_record(self.id,'Satıldı','09.09.2026',today=date(2026,9,9))
        with self.assertRaises(ValueError): self.herd.move_record(self.id,'Aktif','08.09.2026')
        self.assertEqual(self.herd.get(self.id)['record_status'],'Satıldı')

    def test_conflicting_official_birth_date_leaves_record_intact(self):
        before = self.herd.get(self.id)
        with self.assertRaises(ValueError):
            self.herd.sync(self.id,{'tag':before['tag'],'born':'2026-02-01','sex':'Dişi'})
        self.assertEqual(self.herd.get(self.id),before)

    def test_photo_cleanup_keeps_shared_and_external_originals(self):
        folder = Path(self.temp.name)/'photos'; folder.mkdir()
        original = Path(self.temp.name)/'original.jpg'; original.write_bytes(b'original')
        owned = folder/'copy.jpg'; owned.write_bytes(b'copy')
        remove_unused_photo(original,folder,[])
        self.assertTrue(original.exists())
        remove_unused_photo(owned,folder,[str(owned)])
        self.assertTrue(owned.exists())
        remove_unused_photo(owned,folder,[])
        self.assertFalse(owned.exists())


if __name__=='__main__': unittest.main()
