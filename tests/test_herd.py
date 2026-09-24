import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from herd import Herd, age_text, due_date, due_text

class HerdTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'test.db'
        self.herd = Herd(self.path)
        self.values = dict(tag='TR123', name='Pamuk', born='01.01.2020', state='Sağmal', pregnant=True, insemination='01.01.2026', gestation_days='283', notes='Kontrol', sex='Dişi')

    def tearDown(self):
        self.herd.close()
        self.temp.cleanup()

    def save(self):
        self.herd.save(self.values, today=date(2026, 9, 9))

    def test_persistence_and_update(self):
        self.save()
        self.herd.close()
        self.herd = Herd(self.path)
        cow = self.herd.all()[0]
        self.assertEqual(cow['name'], 'Pamuk')
        self.values['name'] = 'Boncuk'
        self.herd.save(self.values, cow['id'], today=date(2026, 9, 9))
        self.assertEqual(len(self.herd.all()), 1)
        self.assertEqual(self.herd.all()[0]['name'], 'Boncuk')

    def test_delete_persists_and_keeps_other_animals(self):
        self.save()
        cow = self.herd.all()[0]
        self.herd.save(self.values | {'tag': 'TR456'}, today=date(2026, 9, 9))
        other = self.herd.all()[1]
        self.herd.delete(cow['id'])
        self.herd.close()
        self.herd = Herd(self.path)
        self.assertEqual([c['id'] for c in self.herd.all()], [other['id']])
        self.assertEqual(self.herd.history(cow['id']), [])
        self.assertEqual(self.herd.history(other['id']), ['2026-01-01'])
        with self.assertRaises(ValueError):
            self.herd.delete(cow['id'])

    def test_delete_rolls_back_history_on_failure(self):
        self.save()
        cow = self.herd.all()[0]
        self.herd.db.execute("CREATE TRIGGER prevent_delete BEFORE DELETE ON cows BEGIN SELECT RAISE(ABORT, 'blocked'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.herd.delete(cow['id'])
        self.assertEqual(self.herd.get(cow['id'])['tag'], cow['tag'])
        self.assertEqual(self.herd.history(cow['id']), ['2026-01-01'])

    def test_duplicate(self):
        self.save()
        with self.assertRaises(ValueError): self.save()
        self.assertEqual(len(self.herd.all()), 1)

    def test_dates(self):
        for key, value in [('born','31.02.2020'), ('born','01.01.2027'), ('insemination','01.01.2019'), ('insemination','01.01.2027')]:
            with self.subTest(key=key, value=value):
                values = self.values | {key: value}
                with self.assertRaises(ValueError):
                    self.herd.save(values, today=date(2026, 9, 9))

    def test_due_today_overdue_and_pregnancy(self):
        self.save()
        cow = self.herd.all()[0]
        due = date(2026, 1, 1) + timedelta(days=283)
        self.assertEqual(due_date(cow), due)
        self.assertIn('bugün', due_text(cow, due))
        self.assertIn('2 gün geçti', due_text(cow, due+timedelta(days=2)))
        self.assertIsNone(due_date(cow | {'pregnant': 0}))
        self.assertIsNone(due_date(cow | {'insemination': ''}))

    def test_age(self):
        self.assertEqual(age_text(date(2020,9,10),date(2026,9,9)), '5 yaş 11 ay')
        self.assertEqual(age_text(date(2020,9,9),date(2026,9,9)), '6 yaş 0 ay')
        self.assertEqual(age_text(date(2024,2,29),date(2025,3,1)), '1 yaş 0 ay')

if __name__ == '__main__':
    unittest.main()
