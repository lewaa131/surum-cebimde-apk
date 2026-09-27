from datetime import datetime, date, timedelta
from unittest import TestCase
from unittest.mock import Mock
from day_refresh import DayRefresh
from lifecycle import task_window
from cycle_settings import DEFAULT_CYCLE


class DayRefreshTests(TestCase):
    def setUp(self):
        self.now=datetime(2026,9,27,23,59,59)
        self.clock=Mock()
        self.render=Mock()
        self.blocked=False
        self.timer=DayRefresh(self.clock,self.render,lambda:self.blocked,lambda:self.now)

    def test_midnight_is_scheduled_and_refreshes_once(self):
        self.timer.schedule()
        callback,seconds=self.clock.schedule_once.call_args.args
        self.assertAlmostEqual(seconds,1.1)
        self.now=datetime(2026,9,28)
        callback(0)
        self.timer.check()
        self.render.assert_called_once()

    def test_editor_defers_without_losing_day_change(self):
        self.now+=timedelta(days=1)
        self.blocked=True
        self.timer.check()
        self.render.assert_not_called()
        self.blocked=False
        self.timer.check()
        self.render.assert_called_once()

    def test_resume_after_several_days_and_clock_backwards(self):
        self.now+=timedelta(days=4)
        self.timer.check()
        self.now-=timedelta(days=2)
        self.timer.check()
        self.assertEqual(self.render.call_count,2)

    def test_failed_render_is_retried(self):
        self.now+=timedelta(days=1)
        error=Mock()
        self.timer.on_error=error
        self.render.side_effect=[ValueError('retry'),None]
        self.timer.check()
        error.assert_called_once()
        self.timer.check()
        self.assertEqual(self.render.call_count,2)
        self.assertEqual(self.timer.day,self.now.date())

    def test_month_window_rolls_and_due_task_moves(self):
        today=date(2026,9,27)
        settings=dict(DEFAULT_CYCLE,calendar_view='month')
        def calf(i,days):
            return dict(id=i,tag=str(i),born=(today+timedelta(days=days-settings['weaning_days'])).isoformat(),
                        sex='Erkek',state='Buzağı',calved_before=0,record_status='Aktif',registry_status='Canlı')
        cows=[calf(1,1),calf(2,30),calf(3,31)]
        due,upcoming,days=task_window(cows,settings,today)
        self.assertEqual(days,30)
        self.assertEqual([t['cow_id'] for t in upcoming],[1,2])
        self.assertEqual(due,[])
        due,upcoming,_=task_window(cows,settings,today+timedelta(days=1))
        self.assertEqual([t['cow_id'] for t in due],[1])
        self.assertEqual([t['cow_id'] for t in upcoming],[2,3])
        cows[0]['_cycle_marks']=[dict(kind='weaning',anchor=cows[0]['born'],done_day=today.isoformat(),snooze_until='')]
        self.assertEqual(task_window(cows,settings,today+timedelta(days=1))[0],[])
