import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from herd import Herd
from reminders import AndroidReminders, reminder_plan, save_settings, load_settings, validate_settings
from unittest.mock import Mock


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.herd = Herd(Path(self.temp.name)/'herd.db')
        self.herd.save(dict(tag='TR350004339192', name='Pamuk', born='01.01.2020',
            state='Sağmal', pregnant=True, insemination='01.01.2026',
            gestation_days=283, notes='', sex='Dişi'), today=date(2026, 9, 9))
        self.cow = self.herd.all()[0]

    def tearDown(self):
        self.herd.close()
        self.temp.cleanup()

    def test_two_events_sixty_days_apart(self):
        dry, birth = reminder_plan([self.cow])
        self.assertEqual(dry['title'], 'Kuruya ayır')
        self.assertEqual(birth['title'], 'Tahmini doğum bugün')
        self.assertEqual(date.fromisoformat(birth['day'])-date.fromisoformat(dry['day']), timedelta(days=60))
        self.assertEqual(birth['day'], '2026-10-11')
        self.assertEqual(dry['until'], birth['day'])
        self.assertIn(self.cow['tag'], birth['body'])

    def test_custom_day_and_clock_persist_and_change_plan(self):
        path = Path(self.temp.name)/'settings.json'
        self.assertEqual(load_settings(path),{'dry_days':60,'time':'09:00'})
        save_settings(path,'45','17:30')
        settings = load_settings(path)
        dry,birth = reminder_plan([self.cow],settings)
        self.assertEqual(date.fromisoformat(birth['day'])-date.fromisoformat(dry['day']),timedelta(days=45))
        self.assertEqual(dry['time'],'17:30')
        self.assertEqual(birth['time'],'17:30')
        self.assertEqual(birth['day'],'2026-10-11')

    def test_invalid_preferences_do_not_overwrite_saved_settings(self):
        path = Path(self.temp.name)/'settings.json'
        save_settings(path,'60','09:00')
        for days,clock in [('0','09:00'),('-5','09:00'),('251','09:00'),('60','24:00'),('60','09:60'),('x','10:00')]:
            with self.subTest(days=days,clock=clock):
                with self.assertRaises(ValueError): save_settings(path,days,clock)
        self.assertEqual(load_settings(path),{'dry_days':60,'time':'09:00'})

    def test_settings_change_preserves_delivered_event_identity(self):
        before = reminder_plan([self.cow])
        after = reminder_plan([self.cow],validate_settings('45','08:00'))
        self.assertEqual([e['key'] for e in before],[e['key'] for e in after])

    def test_no_alarm_without_confirmed_dated_live_female_pregnancy(self):
        for change in ({'pregnant':0}, {'insemination':''}, {'sex':'Erkek'},
                       {'sex':'Bilinmiyor'}, {'registry_status':'Ölü'}):
            with self.subTest(change=change):
                self.assertEqual(reminder_plan([self.cow | change]), [])

    def test_dry_state_keeps_birth_only(self):
        self.herd.update_care(self.cow['id'], 'Pamuk', 'Kuru dönemde', '')
        self.assertEqual([e['kind'] for e in reminder_plan(self.herd.all())], ['birth'])

    def test_closing_pregnancy_and_deletion_remove_all_events(self):
        self.herd.update_reproduction(self.cow['id'], '', False, 283)
        self.assertEqual(reminder_plan(self.herd.all()), [])
        self.herd.delete(self.cow['id'])
        self.assertEqual(reminder_plan(self.herd.all()), [])

    def test_date_change_replaces_alarm_identity_but_rename_does_not(self):
        original = reminder_plan([self.cow])
        renamed = reminder_plan([self.cow | {'name':'Boncuk'}])
        self.assertEqual([e['key'] for e in original], [e['key'] for e in renamed])
        self.assertIn('Boncuk', renamed[0]['body'])
        changed = reminder_plan([self.cow | {'gestation_days':280}])
        self.assertTrue(set(e['key'] for e in original).isdisjoint(e['key'] for e in changed))

    def test_leap_year_and_year_boundary(self):
        cow = self.cow | {'insemination':'2023-05-22', 'gestation_days':283}
        dry, birth = reminder_plan([cow])
        self.assertEqual(birth['day'], '2024-02-29')
        self.assertEqual(dry['day'], '2023-12-31')

    def test_reload_retains_event_identity(self):
        original = reminder_plan(self.herd.all())
        self.herd.close()
        self.herd = Herd(Path(self.temp.name)/'herd.db')
        self.assertEqual(reminder_plan(self.herd.all()), original)

    def test_multiple_cows_have_separate_alarm_keys(self):
        other = self.cow | {'id':2, 'tag':'TR000000000001'}
        self.assertEqual(len({e['key'] for e in reminder_plan([self.cow, other])}), 4)

    def test_refresh_does_not_postpone_alarm_but_changes_and_resume_reschedule(self):
        bridge = AndroidReminders.__new__(AndroidReminders)
        bridge.activity = object()
        bridge.bridge = Mock()
        bridge.bridge.notificationsEnabled.return_value = True
        bridge._last_sync = None
        bridge.sync([self.cow])
        bridge.sync([self.cow])
        self.assertEqual(bridge.bridge.replacePlan.call_count, 1)
        bridge.sync([self.cow], force=True)
        self.assertEqual(bridge.bridge.replacePlan.call_count, 2)
        bridge.bridge.notificationsEnabled.return_value = False
        bridge.sync([self.cow])
        self.assertEqual(bridge.bridge.replacePlan.call_count, 3)
        bridge.sync([])
        self.assertEqual(bridge.bridge.replacePlan.call_args.args[1], '[]')

    def test_failed_schedule_retries_same_plan(self):
        bridge = AndroidReminders.__new__(AndroidReminders)
        bridge.activity = object()
        bridge.bridge = Mock()
        bridge.bridge.notificationsEnabled.return_value = True
        bridge.bridge.replacePlan.side_effect = [RuntimeError('storage error'), None]
        bridge._last_sync = None
        with self.assertRaises(RuntimeError):
            bridge.sync([self.cow])
        bridge.sync([self.cow])
        self.assertEqual(bridge.bridge.replacePlan.call_count, 2)


if __name__ == '__main__':
    unittest.main()
