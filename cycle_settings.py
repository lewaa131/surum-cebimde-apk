"""Persistent cycle planning preferences; existing user values are preserved."""
import json
import re
from pathlib import Path

# key, title, one-sentence description, initial value, minimum, maximum, toggle
DAY_SETTINGS = (
    ('gestation_days','Gebelik takvimi','Tahmini doğum hesabında kullanılacak gün sayısını belirler.',283,250,310,None),
    ('pregnancy_check_days','Gebelik kontrolü','Tohumlamadan kaç gün sonra kontrol planlanacağını belirler.',35,1,180,'pregnancy_check_enabled'),
    ('dry_days','Kuruya ayırma','Tahmini doğumdan kaç gün önce kuruya ayırma planlanacağını belirler.',60,1,250,'dry_enabled'),
    ('weaning_days','Sütten kesme','Yem tüketimi ve gelişimi kontrol ederek sütten kesmeyi değerlendir.',60,1,250,'weaning_enabled'),
    ('fresh_days','Yeni doğuran takibi','Doğumdan sonraki özel takip döneminin uzunluğunu belirler.',60,1,250,'fresh_enabled'),
    ('postpartum_days','Doğum sonrası bekleme','Yeniden tohumlama değerlendirmesi için doğumdan sonraki bekleme gününü belirler.',60,1,250,None),
    ('heifer_days','İlk tohumlama yaşı','Düvelerde ilk tohumlama değerlendirmesi için hedef yaşı gün olarak belirler.',420,150,900,None),
    ('insemination_gap_days','Tohumlama kayıt aralığı','Yakın tarihli ikinci kayıtta uyarır; kızgınlık süresi değildir.',7,1,180,None),
    ('heat_days','Kızgınlık dönüş kontrolü','Tohumlamadan sonra yeniden kızgınlık gözlemi için hedef günü belirler.',21,18,30,'heat_enabled'),
)
DEFAULT_CYCLE = {row[0]:row[3] for row in DAY_SETTINGS}
DEFAULT_CYCLE.update({row[6]:True for row in DAY_SETTINGS if row[6]})
DEFAULT_CYCLE.update(milk_mode='separate',calendar_view='week',show_photos=True)


def validate_cycle(values):
    if not isinstance(values,dict): raise ValueError('Ayarlar okunamadı.')
    result = dict(DEFAULT_CYCLE)
    result.update({key:value for key,value in values.items() if key in result})
    for key,title,_,default,low,high,toggle in DAY_SETTINGS:
        value=str(result[key])
        if not re.fullmatch(r'[0-9]{1,3}',value) or not low <= int(value) <= high:
            raise ValueError(f'{title}: {low}–{high} arasında tam gün yaz.')
        result[key]=int(value)
    for key in [row[6] for row in DAY_SETTINGS if row[6]]+['show_photos']:
        if type(result[key]) is not bool: raise ValueError('Açık/kapalı seçimi geçersiz.')
    for key,options in [('milk_mode',('separate','daily')),('calendar_view',('week','fortnight','month'))]:
        if result[key] not in options: raise ValueError('Görünüm seçimi geçersiz.')
    return result


def load_cycle(path, farm=None, reminders=None):
    path=Path(path)
    if not path.exists():
        initial=dict(DEFAULT_CYCLE)
        if farm:
            initial.update({key:farm[key] for key in ('gestation_days','fresh_days')})
        if reminders: initial['dry_days']=reminders['dry_days']
        return validate_cycle(initial)
    # Report damaged files instead of silently overwriting saved preferences.
    try: return validate_cycle(json.loads(path.read_text(encoding='utf-8')))
    except (ValueError,TypeError) as exc: raise ValueError('Döngü ayarları okunamadı; dosya değiştirilmedi.') from exc


def save_cycle(path, values):
    values=validate_cycle(values)
    path=Path(path)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)
    return values
