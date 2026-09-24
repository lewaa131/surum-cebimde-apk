import tempfile
import unittest
from pathlib import Path
from PIL import Image
from photos import import_photo

class PhotoTests(unittest.TestCase):
    def test_photo_copied_and_resized(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'original.png'
            Image.new('RGB',(2400,1200),'white').save(source)
            saved = Path(import_photo(source,root/'photos'))
            source.unlink()
            with Image.open(saved) as image: self.assertEqual(image.size,(1600,800))

    def test_invalid_file_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'invalid.jpg'; source.write_text('not an image')
            with self.assertRaises(ValueError): import_photo(source,Path(folder)/'photos')

    def test_exif_orientation_applied(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'rotated.jpg'
            image = Image.new('RGB',(80,40),'white'); exif = image.getexif(); exif[274] = 6
            image.save(source,exif=exif)
            with Image.open(import_photo(source,Path(folder)/'photos')) as saved:
                self.assertEqual(saved.size,(40,80))
