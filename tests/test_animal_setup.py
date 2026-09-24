from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from herd import Herd
from animal_setup import eligible
from lifecycle import snapshot
from cycle_settings import DEFAULT_CYCLE

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(); self.herd=Herd(Path(self.tmp.name)/'herd.db')
        self.info=dict(tag='TR123456789012',born='2020-01-01',sex='Dişi',registry_status='Canlı')
    def tearDown(self):
        self.herd.close(); self.tmp.cleanup()
    def test_optional_birth_no_invented_schedule(self):
        i=self.herd.register(self.info,initial=dict(state='Sağmal'))
        c=self.herd.get(i)
        self.assertEqual(c['last_birth'],'')
        self.assertEqual(snapshot(c,DEFAULT_CYCLE)['tasks'],[])
        self.herd.set_birth_history(i,True)
        self.assertEqual(self.herd.get(i)['last_birth'],'')
    def test_pregnant_and_milking_without_dates(self):
        i=self.herd.register(self.info,initial=dict(state='Sağmal',reproduction='Gebe'))
        c=self.herd.get(i)
        self.assertTrue(c['pregnant']); self.assertEqual(c['state'],'Sağmal')
        self.assertEqual(snapshot(c,DEFAULT_CYCLE)['tasks'],[])
    def test_dated_service_builds_control_tasks(self):
        i=self.herd.register(self.info,initial=dict(state='Düve',reproduction='Tohumlandı',insemination='01.09.2026'))
        self.assertEqual(self.herd.history(i),['2026-09-01'])
        self.assertIn('pregnancy',[t['kind'] for t in snapshot(self.herd.get(i),DEFAULT_CYCLE)['tasks']])
    def test_invalid_setup_leaves_no_partial_animal(self):
        with self.assertRaises(ValueError):
            self.herd.register(self.info,initial=dict(state='Düve',last_birth='01.01.2026'))
        self.assertEqual(self.herd.all(),[])
    def test_exact_fourteen_month_threshold_and_sex(self):
        info=self.info|dict(born='2025-07-13')
        self.assertTrue(eligible(info,date(2026,9,13)))
        self.assertFalse(eligible(info,date(2026,9,12)))
        self.assertFalse(eligible(info|dict(sex='Erkek'),date(2026,9,13)))

    def test_known_mother_without_date_cannot_become_heifer_in_care(self):
        i=self.herd.register(self.info,initial=dict(state='Sağmal'))
        with self.assertRaises(ValueError): self.herd.update_care(i,'Test','Düve','')
        self.assertEqual(self.herd.get(i)['state'],'Sağmal')
    def test_edit_screen_cannot_reactivate_closed_service(self):
        i=self.herd.register(self.info,initial=dict(reproduction='Tohumlandı',insemination='01.08.2026'))
        self.herd.pregnancy_result(i,False,'2026-08-01')
        with self.assertRaises(ValueError): self.herd.update_reproduction(i,'01.08.2026',True,283)
        self.assertFalse(self.herd.get(i)['pregnant'])
    def test_edit_screen_cannot_skip_loss_control(self):
        from corrections import loss
        i=self.herd.register(self.info,initial=dict(reproduction='Gebe',insemination='01.08.2026'))
        loss(self.herd,i,'10.09.2026','Düşük')
        with self.assertRaises(ValueError): self.herd.update_reproduction(i,'12.09.2026',True,283)
        self.assertFalse(self.herd.get(i)['pregnant'])
