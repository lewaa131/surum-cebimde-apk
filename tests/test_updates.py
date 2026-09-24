import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch
from update_service import validate, download, REPOSITORY


class UpdateTests(unittest.TestCase):
    def data(self,payload=b'apk'):
        return dict(version='0.13.1',version_code=100013001,package='org.surutakip.surum',
            size=len(payload),sha256=hashlib.sha256(payload).hexdigest(),
            url=f'https://github.com/{REPOSITORY}/releases/download/v0.13.1/surum-cebimde.apk')
    def test_semantic_version(self):
        self.assertIsNotNone(validate(self.data(),'0.12.9'))
        self.assertIsNone(validate(self.data(),'0.13.1'))
        self.assertIsNone(validate(self.data(),'0.14.0'))
    def test_reject_wrong_package_url_size_hash_code(self):
        for field,value in [('package','other'),('url','http://example.com/x.apk'),('size',0),('sha256','x'),('version_code',1)]:
            with self.assertRaises(ValueError): validate(self.data()|{field:value},'0.13.0')
    def test_success_atomic_download(self):
        with tempfile.TemporaryDirectory() as folder, patch('update_service.request',return_value=io.BytesIO(b'apk')):
            progress=[]; result=download(self.data(),folder,Event(),progress.append)
            self.assertEqual(result.read_bytes(),b'apk'); self.assertEqual(progress[-1],100)
            self.assertFalse((Path(folder)/'update.part').exists())
    def test_bad_download_preserves_previous_apk(self):
        for payload in (b'a',b'bad',b'extra'):
            with tempfile.TemporaryDirectory() as folder, patch('update_service.request',return_value=io.BytesIO(payload)):
                target=Path(folder)/'update.apk';target.write_bytes(b'old')
                with self.assertRaises(ValueError): download(self.data(),folder,Event(),lambda _:None)
                self.assertEqual(target.read_bytes(),b'old')
                self.assertFalse((Path(folder)/'update.part').exists())
    def test_cancel_cleans_partial(self):
        event=Event();event.set()
        with tempfile.TemporaryDirectory() as folder, patch('update_service.request',return_value=io.BytesIO(b'apk')):
            with self.assertRaises(ValueError): download(self.data(),folder,event,lambda _:None)
            self.assertFalse((Path(folder)/'update.apk').exists())
            self.assertFalse((Path(folder)/'update.part').exists())
