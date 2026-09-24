from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from herd import Herd
from lifecycle import snapshot
from cycle_settings import DEFAULT_CYCLE
from dashboard import sections

class ConfirmationStates(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(); self.herd=Herd(Path(self.temp.name)/'herd.db')
        self.herd.save(dict(tag='TR000000000001',name='Test',born='01.01.2020',state='Sağmal',
            pregnant=True,insemination='01.01.2026',gestation_days=283,notes='',sex='Dişi'))
    def tearDown(self):
        self.herd.close(); self.temp.cleanup()
    def test_dry_changes_milking_only_after_confirmation(self):
        snapshot(self.herd.get(1),DEFAULT_CYCLE,date(2026,9,9))
        self.assertEqual(self.herd.get(1)['state'],'Sağmal')
        self.herd.mark_dry(1,'09.09.2026',today=date(2026,9,9))
        cow=self.herd.get(1)
        self.assertEqual(cow['state'],'Kuru dönemde')
        self.assertTrue(cow['pregnant'])
    def test_non_milking_heifer_cannot_be_dried(self):
        with self.herd.db: self.herd.db.execute("UPDATE cows SET state='Düve',calved_before=0 WHERE id=1")
        with self.assertRaises(ValueError): self.herd.mark_dry(1,'09.09.2026',today=date(2026,9,9))
        self.assertEqual(dict(sections(self.herd.all(),'today',date(2026,9,9)))['Kuruya ayrılacaklar'],[])
    def test_weaning_requires_confirmation_and_does_not_change_mother(self):
        with self.herd.db:
            self.herd.db.execute("UPDATE cows SET born='2026-06-01',state='Buzağı',calved_before=0,pregnant=0,insemination='' WHERE id=1")
        day=date(2026,9,9)
        kinds=lambda:[t['kind'] for t in snapshot(self.herd.get(1),DEFAULT_CYCLE,day)['tasks']]
        self.assertIn('weaning',kinds())
        self.assertEqual(self.herd.events(1),[])
        self.herd.cycle_mark(1,'weaning','2026-06-01',DEFAULT_CYCLE,today=day)
        self.assertNotIn('weaning',kinds())
        self.assertEqual(self.herd.get(1)['state'],'Buzağı')
        self.assertEqual(self.herd.events(1)[0]['kind'],'Sütten kesildi')
