from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from cycle_settings import load_cycle, save_cycle, validate_cycle, DEFAULT_CYCLE


class CycleSettingsTests(unittest.TestCase):
    def test_initial_values_inherit_existing_preferences_once(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'cycle.json'
            values=load_cycle(path,{'gestation_days':280,'fresh_days':55},{'dry_days':50})
            self.assertEqual((values['gestation_days'],values['fresh_days'],values['dry_days']),(280,55,50))
            self.assertEqual(values['pregnancy_check_days'],35)
            self.assertFalse(path.exists())
            save_cycle(path,values)
            self.assertEqual(load_cycle(path,{'gestation_days':290,'fresh_days':80},{'dry_days':90}),values)

    def test_all_types_round_trip(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'cycle.json'
            values=DEFAULT_CYCLE|dict(weaning_days='95',weaning_enabled=False,show_photos=False,milk_mode='daily',calendar_view='month')
            saved=save_cycle(path,values)
            self.assertEqual(saved['weaning_days'],95)
            self.assertEqual(load_cycle(path),saved)

    def test_invalid_save_preserves_original_file(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'cycle.json'
            save_cycle(path,DEFAULT_CYCLE)
            original=path.read_bytes()
            for key,value in [('dry_days',''),('dry_days',0),('weaning_days',251),('heifer_days',149),
                              ('fresh_days','3.5'),('fresh_days',True),('show_photos','false'),('milk_mode','other')]:
                with self.subTest(key=key,value=value):
                    with self.assertRaises(ValueError): save_cycle(path,DEFAULT_CYCLE|{key:value})
                    self.assertEqual(path.read_bytes(),original)

    def test_partial_settings_get_new_defaults(self):
        values=validate_cycle({'weaning_days':80})
        self.assertEqual(values['weaning_days'],80)
        self.assertEqual(values['pregnancy_check_days'],35)

    def test_corrupt_file_is_not_silently_reset(self):
        with TemporaryDirectory() as folder:
            path=Path(folder)/'cycle.json'
            path.write_text('{broken',encoding='utf-8')
            with self.assertRaises(ValueError): load_cycle(path)
            self.assertEqual(path.read_text(encoding='utf-8'),'{broken')
