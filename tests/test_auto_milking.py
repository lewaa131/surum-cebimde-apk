from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from herd import Herd
from milk_store import MilkStore
from lifecycle import tasks_for
from cycle_settings import DEFAULT_CYCLE
from datetime import date


class AutoMilkingTests(TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.path=Path(self.tmp.name)/'herd.db'
        self.herd=Herd(self.path)
        self.info=dict(tag='TR123456789012',born='2020-01-01',sex='Dişi',registry_status='Canlı')

    def tearDown(self):
        self.herd.close();self.tmp.cleanup()

    def test_optional_state_with_birth_enters_milking(self):
        i=self.herd.register(self.info,initial=dict(last_birth='01.01.2026'))
        self.assertEqual(self.herd.get(i)['state'],'Sağmal')
        self.assertEqual(self.herd.all()[0]['state'],'Sağmal')
        self.assertTrue(MilkStore(self.herd.db).can_enter(self.herd.get(i),'2026-09-25'))

    def test_legacy_birth_and_unknown_state_are_derived_after_reopen(self):
        i=self.herd.register(self.info,initial=dict(last_birth='01.01.2026'))
        with self.herd.db: self.herd.db.execute("UPDATE cows SET state='Diğer',calved_before=-1 WHERE id=?",(i,))
        self.herd.close();self.herd=Herd(self.path)
        self.assertEqual(self.herd.get(i)['state'],'Sağmal')

    def test_old_age_and_first_pregnancy_never_imply_milking(self):
        i=self.herd.register(self.info,initial=dict(state='Düve',reproduction='Gebe',insemination='01.01.2026'))
        self.assertEqual(self.herd.get(i)['state'],'Düve')
        self.assertFalse(MilkStore(self.herd.db).can_enter(self.herd.get(i),'2026-09-25'))
        self.assertNotIn('dry',{t['kind'] for t in tasks_for(self.herd.all(),DEFAULT_CYCLE,date(2026,9,25))})

    def test_unknown_adult_stays_unknown(self):
        i=self.herd.register(self.info)
        self.assertEqual(self.herd.get(i)['state'],'Diğer')

    def test_dry_until_confirmed_birth_and_calf_not_milking(self):
        i=self.herd.register(self.info,initial=dict(state='Sağmal',reproduction='Gebe',insemination='01.01.2026'))
        self.herd.mark_dry(i,'01.09.2026')
        self.assertEqual(self.herd.get(i)['state'],'Kuru dönemde')
        self.assertFalse(MilkStore(self.herd.db).can_enter(self.herd.get(i),'2026-09-25'))
        children=self.herd.record_birth(i,'25.09.2026',calves=['Dişi'])
        self.assertEqual(self.herd.get(i)['state'],'Sağmal')
        self.assertEqual(self.herd.get(children[0])['state'],'Buzağı')

    def test_exception_is_preserved_and_existing_milk_can_be_corrected(self):
        i=self.herd.register(self.info,initial=dict(last_birth='01.01.2026',reproduction='Gebe',insemination='01.04.2026'))
        milk=MilkStore(self.herd.db)
        milk.save(self.herd.get(i),'2026-09-24','daily',daily='10')
        self.herd.update_care(i,'Pamuk','Sağılmıyor','Sağım yapılmıyor')
        c=self.herd.get(i)
        self.assertEqual(c['state'],'Sağılmıyor');self.assertTrue(c['pregnant'])
        self.assertFalse(milk.can_enter(c,'2026-09-25'))
        milk.save(c,'2026-09-24','daily',daily='11')
        self.assertEqual(milk.get(i,'2026-09-24')['daily'],11000)
        self.herd.update_care(i,'Pamuk','Sağmal','')
        self.assertEqual(self.herd.get(i)['state'],'Sağmal')

    def test_initial_dry_and_nonmilking_are_not_overridden_by_birth(self):
        for n,state in enumerate(('Kuru dönemde','Sağılmıyor')):
            i=self.herd.register(self.info|dict(tag=f'TR{n:012d}'),initial=dict(state=state,last_birth='01.01.2026'))
            self.assertEqual(self.herd.get(i)['state'],state)

    def test_history_confirmation_keeps_nonmilking_exception(self):
        i=self.herd.register(self.info,initial=dict(state='Sağılmıyor'))
        self.herd.set_birth_history(i,True)
        self.assertEqual(self.herd.get(i)['state'],'Sağılmıyor')
        self.assertEqual(self.herd.get(i)['calved_before'],1)
