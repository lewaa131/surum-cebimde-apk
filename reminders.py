"""Gebelik hatırlatmaları; kullanıcı gün sayısı ve yerel bildirim saatini seçer."""
from datetime import timedelta
import json
from pathlib import Path
import re

from herd import due_date

DRY_DAYS = 60
DEFAULT_SETTINGS = {'dry_days':60, 'time':'09:00'}


def validate_settings(days, clock):
    if not re.fullmatch(r'[0-9]{1,3}',str(days)) or not 1 <= int(days) <= 250:
        raise ValueError('Gün sayısı 1–250 arasında olmalı.')
    if not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]',clock):
        raise ValueError('Saati 09:00 biçiminde gir.')
    return {'dry_days':int(days),'time':clock}


def load_settings(path):
    path = Path(path)
    if not path.exists(): return dict(DEFAULT_SETTINGS)
    data = json.loads(path.read_text(encoding='utf-8'))
    return validate_settings(data['dry_days'],data['time'])


def save_settings(path, days, clock):
    settings = validate_settings(days,clock)
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(settings),encoding='utf-8')
    temporary.replace(path)
    return settings


def reminder_plan(cows, settings=None):
    settings = settings or DEFAULT_SETTINGS
    settings = validate_settings(settings['dry_days'],settings['time'])
    events = []
    for cow in cows:
        due = due_date(cow)
        if due is None:
            continue
        identity = f'{cow["name"]} · {cow["tag"]}' if cow['name'] else cow['tag']
        # Including conception and due date invalidates alarms after date corrections.
        key = f'{cow["id"]}:{cow["tag"]}:{cow["insemination"]}:{due.isoformat()}'
        common = dict(cow_id=cow['id'], identity=identity, due=due.isoformat(), time=settings['time'])
        if cow['state'] != 'Kuru dönemde':
            events.append(common | dict(
                key=key+':dry', kind='dry', day=(due-timedelta(days=settings['dry_days'])).isoformat(),
                until=due.isoformat(), title='Kuruya ayır',
                body=f'{identity} — Tahmini doğum: {due:%d.%m.%Y}. Kuruya ayırma zamanı.'
            ))
        events.append(common | dict(
            key=key+':birth', kind='birth', day=due.isoformat(), until='',
            title='Tahmini doğum bugün',
            body=f'{identity} — Bugün doğum bekleniyor. Hayvanını kontrol et.'
        ))
    return sorted(events, key=lambda e: (e['day'], e['key']))


class AndroidReminders:
    """Java alıcısı Python uygulaması kapalıyken de çalışır."""
    def __init__(self):
        from jnius import autoclass
        self.activity = autoclass('org.kivy.android.PythonActivity').mActivity
        self.bridge = autoclass('org.surutakip.reminders.ReminderReceiver')
        self._last_sync = None

    def sync(self, cows, force=False, settings=None, cycle=None):
        from lifecycle import notification_plan
        plan=notification_plan(cows,cycle,(settings or DEFAULT_SETTINGS)['time']) if cycle is not None else reminder_plan(cows,settings)
        payload = json.dumps(plan, ensure_ascii=False)
        state = (payload, self.enabled())
        # Screen refreshes must not keep postponing an inexact alarm awaiting delivery.
        if force or state != self._last_sync:
            self.bridge.replacePlan(self.activity, payload)
            self._last_sync = state

    def enabled(self):
        return bool(self.bridge.notificationsEnabled(self.activity))

    def settings(self):
        self.bridge.openSettings(self.activity)

    def test(self):
        self.bridge.scheduleTest(self.activity)
