"""Create release metadata from the exact APK uploaded by Actions."""
from pathlib import Path
import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess

spec=configparser.ConfigParser(interpolation=None)
spec.read('buildozer.spec',encoding='utf-8')
version=spec['app']['version']
assert re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}',version)
major,minor,patch=map(int,version.split('.'))
code=100000000+major*1000000+minor*1000+patch
assert int(spec['app']['android.numeric_version'])==code,'Update android.numeric_version as well'
assert f'__version__ = "{version}"' in Path('main.py').read_text(encoding='utf-8')
repo=os.environ['GITHUB_REPOSITORY']
assert repo=='lewaa131/surum-cebimde-apk','Update repository in update_service.py before publishing elsewhere'
files=list(Path('bin').glob('*.apk'))
assert len(files)==1,'Expected exactly one APK'
tool_dirs=sorted((Path.home()/'.buildozer/android/platform/android-sdk/build-tools').glob('*'))
tool=next((p for p in reversed(tool_dirs) if (p/'apksigner').exists() and (p/'aapt').exists()),None)
assert tool is not None,'Android build tools missing'
badging=subprocess.check_output([str(tool/'aapt'),'dump','badging',str(files[0])],text=True)
assert "name='org.surutakip.surum'" in badging and f"versionCode='{code}'" in badging and f"versionName='{version}'" in badging,'Built APK version does not match update metadata'
signing=subprocess.check_output([str(tool/'apksigner'),'verify','--print-certs',str(files[0])],text=True)
cert=subprocess.check_output(['keytool','-exportcert','-keystore',str(Path.home()/'.android/debug.keystore'),'-storepass','android','-alias','androiddebugkey'])
assert hashlib.sha256(cert).hexdigest() in signing.lower(),'APK was not signed with the permanent key'
output=Path('dist'); output.mkdir(exist_ok=True)
apk=output/'surum-cebimde.apk'; shutil.copy2(files[0],apk)
data=dict(version=version,version_code=code,package='org.surutakip.surum',size=apk.stat().st_size,
          sha256=hashlib.sha256(apk.read_bytes()).hexdigest(),
          url=f'https://github.com/{repo}/releases/download/v{version}/surum-cebimde.apk')
(output/'update.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as output:
    output.write(f'tag=v{version}\n')
