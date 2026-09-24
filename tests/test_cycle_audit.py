from datetime import date
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from herd import Herd
from lifecycle import snapshot
from cycle_settings import DEFAULT_CYCLE


class CycleAuditTests(unittest.TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory()
        self.herd=Herd(Path(self.folder.name)/'herd.db')
        self.settings=dict(DEFAULT_CYCLE)
        self.herd.save(dict(tag='TR123456789012',name='Test',born='01.01.2020',state='Düve',
            sex='Dişi',pregnant=False,insemination='',gestation_days=283,notes=''))
        self.i=self.herd.all()[0]['id']

    def tearDown(self):
        self.herd.close(); self.folder.cleanup()

    def test_merged_rebreeding_task_ends_after_insemination(self):
        self.herd.set_birth_history(self.i,True,'01.06.2026')
        self.settings['fresh_days']=90
        before=snapshot(self.herd.get(self.i),self.settings,date(2026,8,1))['tasks']
        self.assertEqual([t['kind'] for t in before],['breed'])
        self.herd.record_insemination(self.i,'01.08.2026',self.settings)
        tasks=snapshot(self.herd.get(self.i),self.settings,date(2026,9,1))['tasks']
        self.assertFalse(any(t['kind'] in ('fresh','breed') for t in tasks))
        self.assertTrue(any(t['kind']=='pregnancy' for t in tasks))

    def test_new_service_cannot_reuse_closed_service_date(self):
        self.herd.record_insemination(self.i,'01.08.2026',self.settings)
        self.herd.pregnancy_result(self.i,False,'2026-08-01')
        before=self.herd.get(self.i)
        for day in ('01.08.2026','30.07.2026'):
            with self.assertRaises(ValueError): self.herd.record_insemination(self.i,day,self.settings)
            self.assertEqual(self.herd.get(self.i),before)

    def test_deleted_service_does_not_keep_old_completed_check(self):
        self.herd.record_insemination(self.i,'01.08.2026',self.settings)
        self.herd.cycle_mark(self.i,'heat','2026-08-01',self.settings,today=date(2026,8,22))
        self.herd.delete_insemination(self.i,'2026-08-01')
        self.herd.record_insemination(self.i,'01.08.2026',self.settings)
        tasks=snapshot(self.herd.get(self.i),self.settings,date(2026,8,22))['tasks']
        self.assertTrue(any(t['kind']=='heat' for t in tasks))

    def test_heat_observation_keeps_pregnancy_check_pending(self):
        self.herd.record_insemination(self.i,'01.08.2026',self.settings)
        self.herd.cycle_mark(self.i,'heat','2026-08-01',self.settings,
            today=date(2026,8,22),heat_observed=True)
        c=self.herd.get(self.i)
        self.assertEqual(c['insemination'],'2026-08-01')
        self.assertFalse(c['pregnant'])
        self.assertTrue(any(e['kind']=='Kızgınlık gözlendi' for e in self.herd.events(self.i)))
        self.assertFalse(any(e['kind'].startswith('Gebe değil') for e in self.herd.events(self.i)))
        self.assertTrue(any(t['kind']=='pregnancy' for t in snapshot(c,self.settings,date(2026,9,5))['tasks']))

    def test_sex_edit_cannot_hide_existing_reproduction(self):
        self.herd.update_reproduction(self.i,'01.04.2024',True,283)
        kid=self.herd.record_birth(self.i,'01.01.2025',calves=['Dişi'])[0]
        self.herd.record_insemination(kid,'01.08.2026',self.settings)
        before=self.herd.get(kid)
        for sex in ('Erkek','Bilinmiyor'):
            with self.assertRaises(ValueError): self.herd.assign_calf_identity(kid,'',sex)
            self.assertEqual(self.herd.get(kid),before)

    def test_unknown_adult_can_complete_history_while_pregnant(self):
        self.herd.update_care(self.i,'Test','Diğer','')
        self.herd.update_reproduction(self.i,'01.01.2026',True,283)
        kinds={t['kind'] for t in snapshot(self.herd.get(self.i),self.settings)['tasks']}
        self.assertNotIn('history',kinds)
        self.assertIn('birth',kinds)

    def test_official_sex_conflict_does_not_destroy_birth_history(self):
        self.herd.set_birth_history(self.i,True,'01.06.2026')
        before=self.herd.get(self.i)
        with self.assertRaises(ValueError):
            self.herd.sync(self.i,dict(tag=before['tag'],born=before['born'],sex='Erkek',registry_status='Canlı'))
        self.assertEqual(self.herd.get(self.i),before)
