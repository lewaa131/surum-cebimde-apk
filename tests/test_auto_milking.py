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

    def test_unknown_adult_is_estimated_without_birth_event(self):
        i=self.herd.register(self.info)
        cow=self.herd.get(i)
        self.assertEqual(cow['state'],'Sağmal')
        self.assertTrue(cow['_milking_estimated'])
        self.assertEqual(cow['calved_before'],-1)
        self.assertEqual(cow['last_birth'],'')
        self.herd.update_reproduction(i,'01.01.2026',True,283)
        self.assertTrue(self.herd.get(i)['_milking_estimated'])
        self.herd.update_care(i,'Pamuk','Sağmal','Not değişti')
        self.assertTrue(self.herd.get(i)['_milking_estimated'])
        self.herd.set_birth_history(i,False)
        self.assertEqual(self.herd.get(i)['state'],'Düve')

    def test_age_estimate_boundary_and_exceptions(self):
        from lactation import estimate_milking
        cow=self.info|dict(born='2024-09-27',state='Diğer',calved_before=-1)
        self.assertFalse(estimate_milking(cow,date(2026,9,26)))
        self.assertTrue(estimate_milking(cow,date(2026,9,27)))
        for changes in (dict(state='Kuru dönemde'),dict(state='Sağılmıyor'),dict(state='Düve'),
                        dict(calved_before=0),dict(sex='Erkek'),dict(record_status='Satıldı')):
            self.assertFalse(estimate_milking(cow|changes,date(2026,9,27)))

    def test_estimated_milk_and_dry_cycle(self):
        i=self.herd.register(self.info,initial=dict(reproduction='Gebe',insemination='01.01.2026'))
        cow=self.herd.get(i)
        self.assertTrue(cow['_milking_estimated'])
        milk=MilkStore(self.herd.db)
        self.assertFalse(milk.can_enter(cow,'2021-12-31'))
        self.assertTrue(milk.can_enter(cow,'2026-09-25'))
        self.assertIn('dry',{t['kind'] for t in tasks_for([cow],DEFAULT_CYCLE,date(2026,8,1),True)})
        self.herd.mark_dry(i,'01.09.2026')
        self.assertFalse(milk.can_enter(self.herd.get(i),'2026-09-25'))
        self.herd.record_birth(i,'25.09.2026',calves=[])
        self.assertEqual(self.herd.get(i)['state'],'Sağmal')
        self.assertFalse(self.herd.get(i)['_milking_estimated'])

    def test_linked_calf_proves_birth_without_inventing_date(self):
        i=self.herd.register(self.info)
        with self.herd.db:
            self.herd._insert_calf(self.herd.get(i),date(2026,1,1),'Dişi')
        cow=self.herd.get(i)
        self.assertEqual(cow['state'],'Sağmal')
        self.assertEqual(cow['calved_before'],1)
        self.assertEqual(cow['last_birth'],'')
        self.herd.update_care(i,'','Kuru dönemde','')
        self.assertEqual(self.herd.get(i)['state'],'Kuru dönemde')

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
