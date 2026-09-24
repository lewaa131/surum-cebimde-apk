import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from herd import Herd
from dashboard import sections
from reminders import reminder_plan


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'herd.db'
        self.herd = Herd(self.path)
        self.herd.save(dict(tag='TR350004339192',name='Pamuk',born='01.01.2020',
            state='Sağmal',pregnant=True,insemination='01.01.2026',gestation_days=283,
            notes='Korunacak not',sex='Dişi'),today=date(2026,9,9))
        self.id = self.herd.all()[0]['id']

    def tearDown(self):
        self.herd.close()
        self.temp.cleanup()

    def test_due_today_and_overdue_have_distinct_lists(self):
        cows = self.herd.all()
        before = sections(cows,'birth',date(2026,10,10))
        self.assertTrue(all(not rows for _,rows in before))
        on_day = sections(cows,'birth',date(2026,10,11))
        self.assertEqual(len(on_day[0][1]),1)
        self.assertEqual(on_day[1][1],[])
        late = sections(cows,'birth',date(2026,10,12))
        self.assertEqual(late[0][1],[])
        self.assertEqual(len(late[1][1]),1)

    def test_special_includes_today_and_late_separately(self):
        today = dict(sections(self.herd.all(),'special',date(2026,10,11)))
        self.assertEqual(len(today['Bugün doğum beklenenler']),1)
        self.assertEqual(today['Doğumu gecikenler'],[])
        late = dict(sections(self.herd.all(),'special',date(2026,10,12)))
        self.assertEqual(late['Bugün doğum beklenenler'],[])
        self.assertEqual(len(late['Doğumu gecikenler']),1)

    def test_dry_task_completed_without_losing_birth_reminder(self):
        self.assertEqual(len(sections(self.herd.all(),'today',date(2026,9,9))[1][1]),1)
        self.herd.mark_dry(self.id,'09.09.2026',today=date(2026,9,9))
        self.assertEqual(sections(self.herd.all(),'today',date(2026,9,9))[1][1],[])
        self.assertEqual(len(dict(sections(self.herd.all(),'special',date(2026,9,9)))['Kurular']),1)
        self.assertEqual([e['kind'] for e in reminder_plan(self.herd.all())],['birth'])
        self.herd.mark_dry(self.id,'09.09.2026',today=date(2026,9,9))
        self.assertEqual(len(self.herd.events(self.id)),1)

    def test_archives_are_separate_persistent_and_silent(self):
        for status,position in [('Satıldı',0),('Öldü',1),('Arşiv',2)]:
            with self.subTest(status=status):
                self.herd.move_record(self.id,status,'09.09.2026',today=date(2026,9,9))
                self.assertEqual(sections(self.herd.all(),'herd')[0][1],[])
                self.assertEqual(reminder_plan(self.herd.all()),[])
                for tab in ('today','birth','special'):
                    self.assertTrue(all(not rows for _,rows in sections(self.herd.all(),tab)))
                lists = sections(self.herd.all(),'archive')
                self.assertEqual([len(rows) for _,rows in lists],[int(i==position) for i in range(3)])
        self.herd.close(); self.herd = Herd(self.path)
        self.assertEqual(self.herd.get(self.id)['record_status'],'Arşiv')
        self.assertEqual(self.herd.get(self.id)['notes'],'Korunacak not')
        self.assertEqual(self.herd.history(self.id),['2026-01-01'])
        self.herd.move_record(self.id,'Aktif','09.09.2026',today=date(2026,9,9))
        self.assertEqual(len(reminder_plan(self.herd.all())),2)

    def test_birth_closes_pregnancy_and_records_history(self):
        self.herd.record_birth(self.id,'11.10.2026',today=date(2026,10,11))
        cow = self.herd.get(self.id)
        self.assertEqual((cow['state'],cow['pregnant'],cow['insemination']),('Sağmal',0,''))
        self.assertEqual(reminder_plan([cow]),[])
        self.assertEqual(self.herd.events(self.id),[{'kind':'Doğum yaptı','day':'2026-10-11'}])
        self.assertEqual(self.herd.history(self.id),['2026-01-01'])
        with self.assertRaises(ValueError):
            self.herd.record_birth(self.id,'11.10.2026',today=date(2026,10,11))

    def test_invalid_action_dates_leave_records_unchanged(self):
        cow = self.herd.get(self.id)
        for action in (lambda:self.herd.record_birth(self.id,'01.01.2027',today=date(2026,9,9)),
                       lambda:self.herd.mark_dry(self.id,'01.01.2019'),
                       lambda:self.herd.move_record(self.id,'Satıldı','01.01.2019')):
            with self.assertRaises(ValueError): action()
        self.assertEqual(self.herd.get(self.id),cow)
        self.assertEqual(self.herd.events(self.id),[])

    def test_birth_rolls_back_if_history_cannot_be_saved(self):
        self.herd.db.execute("CREATE TRIGGER reject_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'blocked'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.herd.record_birth(self.id,'11.10.2026',today=date(2026,10,11))
        self.assertTrue(self.herd.get(self.id)['pregnant'])


if __name__=='__main__': unittest.main()
