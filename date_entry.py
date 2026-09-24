"""Date typing helpers, independent of the UI and locale."""
from datetime import datetime
import re


def format_date_entry(value):
    """Keep partial input editable; accept both 01092026 and 1.9.2026."""
    value = re.sub(r'[^0-9./-]', '', value).replace('/', '.').replace('-', '.')
    digits = value.replace('.', '')
    parts = value.split('.')
    # Deleting a separator must not truncate the remaining month/year when
    # focus changes or another digit is entered.
    if len(digits) == 8 or any(len(part) > 2 for part in parts[:2]):
        value = digits
    if '.' in value:
        parts = value.split('.')[:3]
        for i in range(min(2, len(parts) - 1)):
            if parts[i]: parts[i] = parts[i][:2].zfill(2)
        parts[-1] = parts[-1][:4 if len(parts) == 3 else 2]
        return '.'.join(parts)
    digits = value[:8]
    if len(digits) <= 2: return digits
    if len(digits) <= 4: return digits[:2] + '.' + digits[2:]
    return digits[:2] + '.' + digits[2:4] + '.' + digits[4:]


def complete_date_entry(value):
    value = format_date_entry(value)
    try:
        return datetime.strptime(value, '%d.%m.%Y').strftime('%d.%m.%Y')
    except ValueError:
        return value
