import tempfile
import unittest
from pathlib import Path
from datetime import date
from farm_settings import save_farm,load_farm,validate_farm,fresh_ids
from herd import Herd

class FarmTests(unittest.TestCase):
    def test_settings_roundtrip_and_invalid(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            self.assertEqual(load_farm(path)['fresh_days'],60)
            save_farm(path,{'gestation_days':'270','fresh_days':'60'})
            self.assertEqual(load_farm(path)['gestation_days'],270)
            with self.assertRaises(ValueError): validate_farm({'gestation_days':400,'fresh_days':60})
            with self.assertRaises(ValueError): validate_farm({'gestation_days':270,'fresh_days':0})

    def test_new_defaults_preserve_existing_and_fresh_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            herd=Herd(Path(folder)/'data.db')
            try:
                base={'tag':'TR123456789012','born':'2020-01-01','sex':'Dişi'}
                first=herd.register(base)
                second=herd.register(dict(base,tag='TR123456789013'),gestation_days=270)
                self.assertEqual(herd.get(first)['gestation_days'],283)
                self.assertEqual(herd.get(second)['gestation_days'],270)
                with herd.db:
                    herd.db.execute('INSERT INTO events(cow_id,kind,day) VALUES (?,?,?)',(first,'Doğum yaptı','2026-01-01'))
                self.assertEqual(fresh_ids(herd,herd.all(),60,date(2026,3,1)),{first})
                self.assertEqual(fresh_ids(herd,herd.all(),60,date(2026,3,2)),set())
            finally: herd.close()
