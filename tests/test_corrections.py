from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from herd import Herd
from corrections import undo,loss
from cycle_settings import DEFAULT_CYCLE
from lifecycle import snapshot,notification_plan
from milk_store import MilkStore

class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.herd=Herd(Path(self.temp.name)/'suru.sqlite3')
        self.herd.save(dict(tag='TR123456789012',name='Anne',born='01.01.2020',state='Sağmal',
            sex='Dişi',pregnant=True,insemination='01.01.2026',gestation_days=283,notes=''))
    def tearDown(self): self.herd.close(); self.temp.cleanup()
    def last(self): return self.herd.db.execute('SELECT MAX(id) FROM corrections').fetchone()[0]
    def test_undo_dry_keeps_pregnancy(self):
        self.herd.mark_dry(1,'01.09.2026',today=date(2026,9,12))
        undo(self.herd,self.last())
        self.assertEqual(self.herd.get(1)['state'],'Sağmal')
        self.assertTrue(self.herd.get(1)['pregnant'])
        self.assertEqual(self.herd.events(1),[])
    def test_birth_undo_removes_untouched_calf_and_restores_pregnancy(self):
        ids=self.herd.record_birth(1,'10.09.2026',today=date(2026,9,12),calves=['Dişi'])
        undo(self.herd,self.last())
        self.assertTrue(self.herd.get(1)['pregnant'])
        self.assertEqual(self.herd.get(1)['insemination'],'2026-01-01')
        self.assertEqual(self.herd.children(1),[])
        self.assertEqual(len(self.herd.all()),1)
    def test_modified_calf_blocks_undo(self):
        ids=self.herd.record_birth(1,'10.09.2026',today=date(2026,9,12),calves=['Dişi'])
        with self.herd.db: self.herd.db.execute("UPDATE cows SET notes='Yeni not' WHERE id=?",(ids[0],))
        with self.assertRaises(ValueError): undo(self.herd,self.last())
        self.assertEqual(len(self.herd.all()),2)
        self.assertFalse(self.herd.get(1)['pregnant'])
    def test_weaning_undo_restores_task(self):
        with self.herd.db:
            self.herd.db.execute("UPDATE cows SET born='2026-06-01',state='Buzağı',calved_before=0,pregnant=0,insemination='' WHERE id=1")
        self.herd.cycle_mark(1,'weaning','2026-06-01',DEFAULT_CYCLE,today=date(2026,9,12))
        undo(self.herd,self.last())
        self.assertIn('weaning',[t['kind'] for t in snapshot(self.herd.get(1),DEFAULT_CYCLE,date(2026,9,12))['tasks']])
    def test_loss_cancels_birth_and_is_reversible(self):
        self.herd.mark_dry(1,'01.09.2026',today=date(2026,9,12))
        loss(self.herd,1,'10.09.2026','Düşük',today=date(2026,9,12))
        cow=self.herd.get(1)
        self.assertFalse(cow['pregnant'])
        self.assertEqual(cow['state'],'Kuru dönemde')
        self.assertFalse(any(t['kind'] in ('dry','birth') for t in notification_plan([cow],DEFAULT_CYCLE,today=date(2026,9,12))))
        with self.assertRaises(ValueError): self.herd.record_insemination(1,'12.09.2026',DEFAULT_CYCLE,today=date(2026,9,12))
        undo(self.herd,self.last())
        self.assertTrue(self.herd.get(1)['pregnant'])
        undo(self.herd,self.last())
        self.assertEqual(self.herd.get(1)['state'],'Sağmal')
    def test_historical_milk_before_dry_allowed_dry_day_blocked(self):
        self.herd.mark_dry(1,'01.09.2026',today=date(2026,9,12))
        milk=MilkStore(self.herd.db); cow=self.herd.get(1)
        milk.save(cow,'2026-08-31','daily',daily='20',today=date(2026,9,12))
        for day in ('2026-09-01','2026-09-02'):
            with self.assertRaises(ValueError): milk.save(cow,day,'daily',daily='20',today=date(2026,9,12))
    def test_dry_period_remains_blocked_after_next_birth(self):
        self.herd.mark_dry(1,'01.09.2026',today=date(2026,9,12))
        self.herd.record_birth(1,'10.09.2026',today=date(2026,9,12))
        milk=MilkStore(self.herd.db)
        with self.assertRaises(ValueError): milk.save(self.herd.get(1),'2026-09-05','daily',daily='20',today=date(2026,9,12))
        milk.save(self.herd.get(1),'2026-09-11','daily',daily='20',today=date(2026,9,12))
