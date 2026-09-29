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

    def test_mature_unknown_fallback_does_not_store_birth_fact(self):
        i=self.herd.register(self.info)
        cow=self.herd.get(i)
        self.assertEqual(cow['state'],'Sağmal')
        self.assertTrue(cow['_milking_estimated'])
        self.assertEqual(cow['calved_before'],-1)
        self.assertEqual(cow['last_birth'],'')
        self.herd.update_reproduction(i,'01.01.2026',True,283)
        self.assertTrue(self.herd.get(i)['_milking_estimated'])
        self.herd.update_care(i,'Pamuk','Sağmal','Not değişti')
        self.herd.close(); self.herd=Herd(self.path)
        self.assertTrue(self.herd.get(i)['_milking_estimated'])
        self.assertEqual(self.herd.get(i)['calved_before'],-1)
        self.herd.set_birth_history(i,False)
        self.assertEqual(self.herd.get(i)['state'],'Düve')

    def test_previous_age_fallback_records_recover_without_migration(self):
        # 0.13.2 only derived the mistaken state in memory; these are its stored values.
        for n in range(2):
            self.herd.register(self.info|dict(tag=f'TR{n:012d}',born='2024-09-01'),
                initial=dict(reproduction='Gebe',insemination='01.01.2026'))
        self.herd.close(); self.herd=Herd(self.path)
        cows=self.herd.all()
        self.assertEqual(sum(c['state']=='Sağmal' for c in cows),0)
        self.assertEqual(sum(c['pregnant'] for c in cows),2)
        self.assertTrue(all(c['insemination']=='2026-01-01' for c in cows))
        self.assertTrue(all(not c['last_birth'] for c in cows))

    def test_first_pregnancy_only_becomes_milking_after_birth(self):
        i=self.herd.register(self.info|dict(born='2024-09-01'),initial=dict(reproduction='Gebe',insemination='01.01.2026'))
        cow=self.herd.get(i)
        milk=MilkStore(self.herd.db)
        self.assertFalse(milk.can_enter(cow,'2021-12-31'))
        self.assertFalse(milk.can_enter(cow,'2026-09-25'))
        self.assertNotIn('dry',{t['kind'] for t in tasks_for([cow],DEFAULT_CYCLE,date(2026,8,1),True)})
        with self.assertRaises(ValueError): self.herd.mark_dry(i,'01.09.2026')
        self.herd.record_birth(i,'25.09.2026',calves=[])
        self.assertEqual(self.herd.get(i)['state'],'Sağmal')
        self.assertTrue(milk.can_enter(self.herd.get(i),'2026-09-25'))
        self.assertEqual(self.herd.get(i)['calved_before'],1)
        self.assertFalse(self.herd.get(i)['_first_calving_pending'])
        self.assertFalse(self.herd.get(i)['_milking_estimated'])

    def test_known_mother_without_birth_date_still_milks(self):
        i=self.herd.register(self.info,initial=dict(reproduction='Gebe',insemination='01.01.2026'))
        self.herd.set_birth_history(i,True)
        cow=self.herd.get(i)
        self.assertEqual(cow['state'],'Sağmal')
        self.assertEqual(cow['last_birth'],'')
        self.assertTrue(cow['pregnant'])

    def test_early_failed_service_keeps_first_birth_protection(self):
        i=self.herd.register(self.info|dict(born='2023-09-01'),
            initial=dict(reproduction='Tohumlandı',insemination='01.01.2025'))
        self.herd.pregnancy_result(i,False,'2025-01-01')
        self.assertTrue(self.herd.get(i)['_first_calving_pending'])
        self.herd.record_insemination(i,'01.01.2026',DEFAULT_CYCLE)
        self.herd.pregnancy_result(i,True,'2026-01-01')
        self.herd.close(); self.herd=Herd(self.path)
        cow=self.herd.get(i)
        self.assertTrue(cow['_first_calving_pending'])
        self.assertFalse(cow['_milking_estimated'])
        self.assertNotEqual(cow['state'],'Sağmal')
        self.herd.record_birth(i,'25.09.2026',calves=[])
        self.assertEqual(self.herd.get(i)['state'],'Sağmal')

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
        self.assertFalse(milk.can_enter(c,date.today().isoformat()))
        self.assertTrue(milk.can_enter(c,'2026-09-25'))
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

    def test_manual_pause_resume_keeps_pregnancy_and_notes(self):
        i=self.herd.register(self.info,initial=dict(state='Sağmal',reproduction='Gebe',insemination='01.01.2026'))
        milk=MilkStore(self.herd.db)
        self.herd.set_milking(i,False,'Tedavi nedeniyle ara verildi',date(2026,9,20))
        cow=self.herd.get(i)
        self.assertEqual(cow['state'],'Sağılmıyor')
        self.assertEqual(cow['notes'],'Tedavi nedeniyle ara verildi')
        self.assertTrue(cow['pregnant'])
        self.assertEqual(cow['insemination'],'2026-01-01')
        self.assertFalse(milk.can_enter(cow,'2026-09-21'))
        self.herd.set_milking(i,True,today=date(2026,9,22))
        cow=self.herd.get(i)
        self.assertTrue(cow['pregnant'])
        self.assertEqual(cow['notes'],'Tedavi nedeniyle ara verildi')
        self.assertFalse(milk.can_enter(cow,'2026-09-21'))
        self.assertTrue(milk.can_enter(cow,'2026-09-22'))

    def test_manual_resume_after_dry_updates_milk_eligibility(self):
        i=self.herd.register(self.info,initial=dict(state='Sağmal',reproduction='Gebe',insemination='01.01.2026'))
        self.herd.mark_dry(i,'01.09.2026')
        self.herd.set_milking(i,True,today=date(2026,9,20))
        milk=MilkStore(self.herd.db)
        self.assertFalse(milk.can_enter(self.herd.get(i),'2026-09-10'))
        self.assertTrue(milk.can_enter(self.herd.get(i),'2026-09-20'))

    def test_manual_milking_rejects_known_heifer(self):
        i=self.herd.register(self.info,initial=dict(state='Düve',reproduction='Gebe',insemination='01.01.2026'))
        with self.assertRaises(ValueError): self.herd.set_milking(i,True)
        self.assertEqual(self.herd.get(i)['state'],'Düve')
        self.assertTrue(self.herd.get(i)['pregnant'])

    def test_result_does_not_change_paused_milking(self):
        i=self.herd.register(self.info,initial=dict(state='Sağmal',reproduction='Tohumlandı',insemination='01.01.2026'))
        self.herd.set_milking(i,False)
        self.herd.pregnancy_result(i,True,'2026-01-01')
        self.assertTrue(self.herd.get(i)['pregnant'])
        self.assertEqual(self.herd.get(i)['state'],'Sağılmıyor')
