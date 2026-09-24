import sqlite3
import tempfile
import unittest
from pathlib import Path
from herd import Herd
from reminders import reminder_plan


class DeleteInseminationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'herd.db'
        self.herd = Herd(self.path)
        for tag in ('TR000000000001','TR000000000002'):
            self.herd.save(dict(tag=tag,name='Pamuk',born='01.01.2020',state='Sağmal',pregnant=True,
                                insemination='01.01.2026',gestation_days=283,notes='Not',sex='Dişi'))
        self.herd.update_reproduction(1,'01.02.2026',True,283)

    def tearDown(self):
        self.herd.close()
        self.temp.cleanup()

    def test_old_date_only_deleted_from_selected_animal(self):
        before = self.herd.get(1)
        self.herd.delete_insemination(1,'2026-01-01')
        self.assertEqual(self.herd.history(1),['2026-02-01'])
        self.assertEqual(self.herd.history(2),['2026-01-01'])
        self.assertEqual(self.herd.get(1),before)
        self.herd.close(); self.herd = Herd(self.path)
        self.assertEqual(self.herd.history(1),['2026-02-01'])

    def test_current_date_clears_schedule_and_stays_deleted_after_restart(self):
        self.herd.delete_insemination(1,'2026-01-01')
        self.herd.delete_insemination(1,'2026-02-01')
        cow = self.herd.get(1)
        self.assertEqual((cow['insemination'],cow['pregnant'],cow['state'],cow['notes']),('',0,'Sağmal','Not'))
        self.assertEqual(reminder_plan([cow]),[])
        self.herd.close(); self.herd = Herd(self.path)
        self.assertEqual(self.herd.history(1),[])

    def test_failure_rolls_back_both_changes(self):
        self.herd.db.execute("CREATE TRIGGER reject_change BEFORE UPDATE ON cows BEGIN SELECT RAISE(ABORT,'blocked'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.herd.delete_insemination(1,'2026-02-01')
        self.assertIn('2026-02-01',self.herd.history(1))
        self.assertTrue(self.herd.get(1)['pregnant'])
        with self.assertRaises(ValueError): self.herd.delete_insemination(1,'2025-01-01')
