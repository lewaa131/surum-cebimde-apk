from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET
from android_hook import after_apk_build, ANDROID


class ManifestTests(unittest.TestCase):
    def test_packaging_registers_components_without_duplicates(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            manifest=root/'src'/'main'/'AndroidManifest.xml'
            manifest.parent.mkdir(parents=True)
            original=f'<manifest xmlns:android="{ANDROID}"><application android:allowBackup="false"><activity android:name="org.kivy.android.PythonActivity" android:exported="true" /></application></manifest>'
            manifest.write_text(original,encoding='utf-8')
            (root/'AndroidManifest.xml').write_text(original,encoding='utf-8')
            tool=SimpleNamespace(_dist=SimpleNamespace(dist_dir=folder))
            after_apk_build(tool)
            after_apk_build(tool)
            app=ET.parse(manifest).getroot().find('application')
            self.assertEqual(app.get(f'{{{ANDROID}}}allowBackup'),'false')
            self.assertEqual(app.get(f'{{{ANDROID}}}enableOnBackInvokedCallback'),'true')
            self.assertEqual(app.find('activity').get(f'{{{ANDROID}}}windowSoftInputMode'),'adjustNothing')
            self.assertEqual(len(app.findall('receiver')),1)
            self.assertEqual(len(app.findall('provider')),2)
            update=next(p for p in app.findall('provider') if p.get(f'{{{ANDROID}}}name').endswith('UpdateProvider'))
            self.assertEqual(update.get(f'{{{ANDROID}}}exported'),'false')
            self.assertEqual(update.get(f'{{{ANDROID}}}authorities'),'org.surutakip.surum.updates')
            provider=app.find('provider')
            self.assertEqual(provider.get(f'{{{ANDROID}}}exported'),'false')
            self.assertEqual(provider.get(f'{{{ANDROID}}}authorities'),'org.surutakip.surum.camera')
            self.assertEqual(manifest.read_bytes(),(root/'AndroidManifest.xml').read_bytes())
