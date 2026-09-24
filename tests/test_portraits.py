from datetime import date
import unittest
from portrait_model import portrait_traits, pattern_seed

class PortraitTests(unittest.TestCase):
    def cow(self,**changes):
        return dict(born='2022-01-01',breed='Holstein-SA',species='Sığır',sex='Dişi',tag='TR000000000001') | changes

    def test_breed_aliases_and_turkish_case(self):
        for breed,family in [('HOLSTEIN-SA','holstein'),('Holstein-KA','red_holstein'),('SİMENTAL MELEZİ','simmental'),('Simmental','simmental'),('Montofon','brown'),('ESMER','brown'),('Jersey','jersey'),('ŞAROLE','charolais'),('Limuzin','limousin'),('Yerli Kara','native_black'),('Boz Irk','grey'),('Red Angus','red_angus')]:
            with self.subTest(breed=breed): self.assertEqual(portrait_traits(self.cow(breed=breed))[0],family)

    def test_unknown_not_silently_holstein(self):
        self.assertEqual(portrait_traits(self.cow(breed='Bilinmeyen ırk'))[0],'generic')
        self.assertEqual(portrait_traits(self.cow(species='Manda'))[0],'buffalo')

    def test_age_boundaries(self):
        for born,stage in [('2025-09-10','calf'),('2025-09-09','young'),('2024-09-10','young'),('2024-09-09','adult')]:
            self.assertEqual(portrait_traits(self.cow(born=born),date(2026,9,9))[1],stage)

    def test_sex_preserved(self):
        for sex in ('Dişi','Erkek','Bilinmiyor'):
            self.assertEqual(portrait_traits(self.cow(sex=sex))[2],sex)

    def test_markings_stable_and_individual(self):
        a=self.cow(); b=self.cow(tag='TR000000000002')
        self.assertEqual(pattern_seed(a),pattern_seed(a))
        self.assertNotEqual(pattern_seed(a),pattern_seed(b))
