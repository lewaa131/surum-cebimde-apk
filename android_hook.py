"""Register Android components after p4a renders its manifest, before Gradle.

extra_manifest_application_arguments accepts attributes, not child elements.
This hook also runs for AAB because p4a shares its packaging path.
"""
from pathlib import Path
from copy import deepcopy
import xml.etree.ElementTree as ET

ANDROID = 'http://schemas.android.com/apk/res/android'
ET.register_namespace('android', ANDROID)


def patch_manifest(path):
    path = Path(path)
    tree = ET.parse(path)
    root = tree.getroot()
    app = root.find('application')
    if app is None: raise ValueError('Android manifest: application missing')
    app.set(f'{{{ANDROID}}}enableOnBackInvokedCallback', 'true')
    fragment = (Path(__file__).parent/'android'/'manifest_application.xml').read_text(encoding='utf-8')
    components = ET.fromstring(f'<components xmlns:android="{ANDROID}">{fragment}</components>')
    for element in components:
        name = element.get(f'{{{ANDROID}}}name')
        for existing in list(app):
            if existing.tag == element.tag and existing.get(f'{{{ANDROID}}}name') == name:
                app.remove(existing)
        app.append(deepcopy(element))
    for activity in app.findall('activity'):
        if activity.get(f'{{{ANDROID}}}name') == 'org.kivy.android.PythonActivity':
            activity.set(f'{{{ANDROID}}}windowSoftInputMode', 'adjustNothing')
    tree.write(path, encoding='utf-8', xml_declaration=True)


def after_apk_build(toolchain):
    directory = Path(toolchain._dist.dist_dir)
    patch_manifest(directory/'src'/'main'/'AndroidManifest.xml')
    legacy = directory/'AndroidManifest.xml'
    if legacy.exists(): patch_manifest(legacy)
