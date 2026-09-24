from datetime import date,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
from contextlib import closing
import unittest
from unittest.mock import patch
from herd import Herd,due_date
from cycle_settings import DEFAULT_CYCLE,load_cycle,save_cycle
from lifecycle import snapshot,category,tasks_for,notification_plan


def human(day): return day.strftime('%d.%m.%Y')


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory()
        self.path=Path(self.folder.name)/'herd.db'
        self.herd=Herd(self.path)
        self.settings=dict(DEFAULT_CYCLE)
        self.today=date(2026,9,11)

    def tearDown(self):
        self.herd.close(); self.folder.cleanup()

    def cow(self,born=date(2024,1,1),state='Düve',sex='Dişi'):
        self.herd.save(dict(tag=f'TR{len(self.herd.all())+1:012d}',name='Pamuk',born=human(born),
            state=state,sex=sex,pregnant=False,insemination='',gestation_days=283,notes='Not'),today=self.today)
        return self.herd.all()[-1]['id']

    def kinds(self,i,day,upcoming=False):
        return {t['kind'] for t in tasks_for([self.herd.get(i)],self.settings,day,upcoming)}

    def test_age_stages_and_birth_not_age_make_cow(self):
        i=self.cow()
        c=self.herd.get(i)
        self.assertEqual(category(c,date(2024,6,30)),'Buzağı')
        self.assertEqual(category(c,date(2024,7,1)),'Dana')
        self.assertEqual(category(c,date(2025,1,1)),'Düve')
        self.assertEqual(category(c,date(2030,1,1)),'Düve')
        male=self.herd.get(self.cow(sex='Erkek',state='Diğer'))
        self.assertEqual(category(male,date(2025,1,1)),'Tosun')
        self.assertEqual(category(male,date(2026,1,1)),'Boğa')
        self.assertNotIn('breed',{t['kind'] for t in snapshot(male,self.settings)['tasks']})

    def test_heifer_target_boundary_and_setting(self):
        i=self.cow(); target=date(2024,1,1)+timedelta(days=420)
        self.assertNotIn('breed',self.kinds(i,target-timedelta(days=1)))
        self.assertIn('breed',self.kinds(i,target))
        self.settings['heifer_days']=450
        self.assertNotIn('breed',self.kinds(i,target))

    def test_full_cycle_twice_and_child_survives_restart(self):
        i=self.cow(); ins=date(2025,3,1)
        self.herd.record_insemination(i,human(ins),self.settings,today=self.today)
        self.assertFalse(self.herd.get(i)['pregnant'])
        self.assertIsNone(due_date(self.herd.get(i)))
        self.assertNotIn('pregnancy',self.kinds(i,ins+timedelta(days=34)))
        self.assertIn('pregnancy',self.kinds(i,ins+timedelta(days=35)))
        self.herd.pregnancy_result(i,True,ins.isoformat(),today=ins+timedelta(days=35))
        due=ins+timedelta(days=283)
        self.assertEqual(due_date(self.herd.get(i)),due)
        self.assertNotIn('dry',self.kinds(i,due-timedelta(days=60),True))
        self.assertIn('birth',self.kinds(i,due))
        # A late date never auto-creates a birth or calf.
        self.kinds(i,due+timedelta(days=10))
        self.assertTrue(self.herd.get(i)['pregnant'])
        children=self.herd.record_birth(i,human(due),today=self.today,calves=['Dişi'])
        c=self.herd.get(children[0]); mother=self.herd.get(i)
        self.assertEqual((c['mother_id'],c['born'],c['local_tag']),(i,due.isoformat(),1))
        self.assertEqual(category(mother,self.today),'İnek')
        self.assertEqual(mother['state'],'Sağmal')
        self.assertEqual(mother['insemination'],'')
        self.assertFalse(mother['pregnant'])
        self.assertNotIn('birth',self.kinds(i,due))
        self.assertNotIn('breed',self.kinds(i,due+timedelta(days=59)))
        self.assertIn('breed',self.kinds(i,due+timedelta(days=60)))
        self.assertIn('weaning',self.kinds(c['id'],due+timedelta(days=60)))
        ins2=due+timedelta(days=65)
        self.herd.record_insemination(i,human(ins2),self.settings,today=self.today)
        self.herd.pregnancy_result(i,True,ins2.isoformat(),today=ins2+timedelta(days=35))
        self.assertIn('dry',self.kinds(i,ins2+timedelta(days=223)))
        self.herd.mark_dry(i,human(ins2+timedelta(days=223)),today=ins2+timedelta(days=223))
        self.assertNotIn('dry',self.kinds(i,ins2+timedelta(days=224)))
        due2=ins2+timedelta(days=283)
        self.herd.record_birth(i,human(due2),today=due2,calves=['Erkek'])
        self.assertEqual(len(self.herd.children(i)),2)
        self.assertEqual(len(self.herd.history(i)),2)
        self.herd.close(); self.herd=Herd(self.path)
        self.assertEqual(self.herd.get(i)['last_birth'],due2.isoformat())
        self.assertEqual(self.herd.get(c['id'])['mother_id'],i)

    def test_birth_double_submit_and_atomic_rollback(self):
        i=self.cow(); ins='2025-01-01'
        self.herd.update_reproduction(i,'01.01.2025',True,283)
        original=self.herd.get(i)
        with patch.object(self.herd,'_insert_calf',side_effect=sqlite3.OperationalError('disk')):
            with self.assertRaises(sqlite3.Error): self.herd.record_birth(i,'11.09.2026',calves=['Dişi'])
        self.assertEqual(self.herd.get(i),original)
        self.herd.record_birth(i,'11.09.2026',calves=['Bilinmiyor','Erkek'])
        with self.assertRaises(ValueError): self.herd.record_birth(i,'11.09.2026',calves=['Dişi'])
        self.assertEqual(len(self.herd.children(i)),2)

    def test_negative_result_keeps_history_and_replans(self):
        i=self.cow(); ins='2026-07-01'
        self.herd.record_insemination(i,'01.07.2026',self.settings)
        self.herd.pregnancy_result(i,False,ins)
        self.assertEqual(self.herd.history(i),[ins])
        self.assertIn('breed',self.kinds(i,self.today))
        self.assertNotIn('pregnancy',self.kinds(i,self.today))
        self.herd.record_insemination(i,'10.09.2026',self.settings)
        with self.assertRaises(ValueError): self.herd.pregnancy_result(i,True,ins)

    def test_snooze_completion_and_notifications_match(self):
        i=self.cow(); anchor='2024-01-01'
        self.herd.cycle_mark(i,'breed',anchor,self.settings,snooze=True,today=self.today)
        self.assertNotIn('breed',self.kinds(i,self.today))
        self.assertIn('breed',self.kinds(i,self.today+timedelta(days=1)))
        c=self.herd.get(i)
        plan=notification_plan([c],self.settings,'08:30',self.today)
        self.assertEqual(plan[0]['time'],'08:30')
        self.assertEqual(plan[0]['day'],'2026-09-12')
        kid=self.cow(born=self.today-timedelta(days=60),state='Buzağı',sex='Erkek')
        k=self.herd.get(kid)
        self.assertIn('weaning',self.kinds(kid,self.today))
        self.settings['weaning_enabled']=False
        self.assertEqual(notification_plan([k],self.settings,today=self.today),[])
        self.herd.cycle_mark(kid,'weaning',k['born'],self.settings,today=self.today)
        self.assertNotIn('weaning',self.kinds(kid,self.today))

    def test_old_cow_unknown_history_and_archived(self):
        i=self.cow(state='Diğer')
        self.assertNotIn('history',self.kinds(i,self.today))
        self.assertNotIn('breed',self.kinds(i,self.today))
        self.herd.set_birth_history(i,False)
        self.assertEqual(category(self.herd.get(i)),'Düve')
        self.herd.move_record(i,'Satıldı','11.09.2026')
        self.assertEqual(self.kinds(i,self.today,True),set())
        self.assertEqual(notification_plan([self.herd.get(i)],self.settings),[])

    def test_completed_history_does_not_create_new_calf(self):
        i=self.cow(state='Sağmal')
        self.herd.set_birth_history(i,True,'01.08.2026')
        self.assertEqual(self.herd.children(i),[])
        self.assertNotIn('breed',self.kinds(i,self.today))
        with self.assertRaises(ValueError): self.herd.set_birth_history(i,False)

    def test_existing_preferences_and_pregnancy_dates_preserved(self):
        i=self.cow(); self.herd.update_reproduction(i,'01.01.2026',True,280)
        old=due_date(self.herd.get(i))
        self.settings.update(gestation_days=290,dry_days=45,weaning_days=100)
        self.assertEqual(due_date(self.herd.get(i)),old)
        self.herd.update_care(i,'Pamuk','Sağmal','')
        task=next(t for t in snapshot(self.herd.get(i),self.settings,date(2026,1,2))['tasks'] if t['kind']=='dry')
        self.assertEqual(task['day'],(old-timedelta(days=45)).isoformat())
        path=Path(self.folder.name)/'cycle.json'
        save_cycle(path,self.settings)
        self.assertEqual(load_cycle(path)['weaning_days'],100)

    def test_calf_tag_and_deleting_mother_keeps_child(self):
        i=self.cow(); self.herd.update_reproduction(i,'01.01.2026',True,283)
        kid=self.herd.record_birth(i,'11.09.2026',calves=['Bilinmiyor'])[0]
        self.herd.assign_calf_identity(kid,'TR123456789012','Dişi')
        self.assertEqual(self.herd.get(kid)['local_tag'],0)
        self.herd.delete(i)
        self.assertIsNone(self.herd.get(kid)['mother_id'])
        self.assertEqual(self.herd.get(kid)['sex'],'Dişi')

    def test_legacy_migration_is_repeatable_and_backs_up_records(self):
        i=self.cow(state='Sağmal')
        self.herd.update_reproduction(i,'01.01.2026',True,280)
        original=self.herd.get(i)
        self.herd.close()
        with closing(sqlite3.connect(self.path)) as db:
            for col in ('calved_before','mother_id','local_tag'): db.execute(f'ALTER TABLE cows DROP COLUMN {col}')
            db.execute('DROP TABLE cycle_marks')
        self.herd=Herd(self.path)
        cow=self.herd.get(i)
        for key in ('tag','born','pregnant','insemination','gestation_days','notes'):
            self.assertEqual(cow[key],original[key])
        self.assertEqual(cow['calved_before'],1)
        backup=self.path.with_suffix('.pre-cycle.sqlite3')
        self.assertTrue(backup.is_file())
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(db.execute('SELECT tag FROM cows').fetchone()[0],cow['tag'])
        self.herd.close(); self.herd=Herd(self.path)
        self.assertEqual(len(self.herd.history(i)),1)

    def test_changing_pending_check_rekeys_native_plan_and_archive_cancels(self):
        i=self.cow(); self.herd.record_insemination(i,'01.09.2026',self.settings)
        old=notification_plan([self.herd.get(i)],self.settings,today=self.today)
        self.settings['pregnancy_check_days']=40
        new=notification_plan([self.herd.get(i)],self.settings,today=self.today)
        before=next(t for t in old if t['kind']=='pregnancy')
        after=next(t for t in new if t['kind']=='pregnancy')
        self.assertNotEqual(before['key'],after['key'])
        self.assertEqual(after['day'],'2026-10-11')
        self.herd.move_record(i,'Arşiv','11.09.2026')
        self.assertEqual(notification_plan([self.herd.get(i)],self.settings),[])

    def test_birth_snooze_keeps_pregnancy_until_user_confirms(self):
        i=self.cow(); self.herd.update_reproduction(i,'01.12.2025',True,283)
        cow=self.herd.get(i)
        self.herd.cycle_mark(i,'birth',cow['insemination'],self.settings,snooze=True,today=self.today)
        self.assertNotIn('birth',self.kinds(i,self.today))
        self.assertIn('birth',self.kinds(i,self.today+timedelta(days=1)))
        self.assertTrue(self.herd.get(i)['pregnant'])
        self.assertEqual(self.herd.children(i),[])

    def test_calf_identity_can_be_corrected_without_losing_birth_link(self):
        i=self.cow(); self.herd.update_reproduction(i,'01.01.2026',True,283)
        kid=self.herd.record_birth(i,'11.09.2026',calves=['Bilinmiyor'])[0]
        self.herd.assign_calf_identity(kid,'TR123456789012','Bilinmiyor')
        self.herd.assign_calf_identity(kid,'TR123456789013','Dişi')
        child=self.herd.get(kid)
        self.assertEqual((child['local_tag'],child['mother_id'],child['sex']),(0,i,'Dişi'))
        with self.assertRaises(ValueError):
            self.herd.sync(kid,dict(tag=child['tag'],born='2025-01-01',sex='Dişi'))
        self.assertEqual(self.herd.get(kid)['born'],'2026-09-11')

    def test_heat_control_does_not_diagnose_pregnancy(self):
        i=self.cow(); self.herd.record_insemination(i,'01.08.2026',self.settings)
        day=date(2026,8,22)
        self.assertIn('heat',self.kinds(i,day))
        self.herd.cycle_mark(i,'heat','2026-08-01',self.settings,today=day)
        self.assertNotIn('heat',self.kinds(i,day))
        self.assertFalse(self.herd.get(i)['pregnant'])
        self.assertIn('pregnancy',self.kinds(i,date(2026,9,5)))


if __name__=='__main__': unittest.main()
