"""Farm preferences; never rewrite existing reproduction records."""
import json
from datetime import date

DEFAULT_FARM = {'gestation_days':283,'fresh_days':60}

def validate_farm(values):
    result={}
    for key,low,high,title in [('gestation_days',250,310,'Gebelik'),('fresh_days',1,250,'Yeni doğuran')]:
        try: value=int(str(values[key]))
        except (ValueError,KeyError,TypeError): raise ValueError(f'{title}: tam gün sayısı gir.') from None
        if not low <= value <= high: raise ValueError(f'{title}: {low}–{high} gün seç.')
        result[key]=value
    return result

def load_farm(path):
    try: return validate_farm(json.loads(path.read_text(encoding='utf-8')))
    except (OSError,ValueError,TypeError): return dict(DEFAULT_FARM)

def save_farm(path,values):
    values=validate_farm(values)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(values),encoding='utf-8')
    temporary.replace(path)
    return values

def fresh_ids(herd,cows,days,today=None):
    today=today or date.today()
    result=set()
    for cow in cows:
        births=[date.fromisoformat(event['day']) for event in herd.events(cow['id']) if event['kind']=='Doğum yaptı']
        if births and 0 <= (today-max(births)).days < days: result.add(cow['id'])
    return result
