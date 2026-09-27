"""Version-specific, persistent reminder deferral; manual checks bypass it."""
import json
import time
from pathlib import Path


def should_offer(folder, version, now=None):
    now=time.time() if now is None else now
    try:
        data=json.loads((Path(folder)/'update-later.json').read_text(encoding='utf-8'))
        return data['version']!=version or now>=float(data['until'])
    except (OSError, ValueError, TypeError, KeyError):
        return True


def remind_later(folder, version, now=None):
    now=time.time() if now is None else now
    path=Path(folder)/'update-later.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(dict(version=version,until=now+86400)),encoding='utf-8')
    temporary.replace(path)
