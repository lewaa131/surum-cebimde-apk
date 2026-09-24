"""Optional initial state, validated before the animal is inserted."""
from datetime import date

def eligible(info,today=None):
    today=today or date.today()
    born=date.fromisoformat(info['born'])
    months=(today.year-born.year)*12+today.month-born.month-(today.day<born.day)
    return info.get('sex')=='Dişi' and info.get('registry_status','') in ('','Canlı') and months>=14

def validate(info,initial=None,today=None):
    from herd import parse_date
    today=today or date.today()
    initial=initial or {}
    state=initial.get('state','Diğer')
    reproduction=initial.get('reproduction','Bilmiyorum')
    birth=initial.get('last_birth','').strip()
    ins=initial.get('insemination','').strip()
    if state not in ('Diğer','Sağmal','Kuru dönemde','Düve'): raise ValueError('Geçerli durum seç.')
    if reproduction not in ('Bilmiyorum','Gebe değil','Gebe','Tohumlandı'): raise ValueError('Geçerli üreme durumu seç.')
    if not eligible(info,today) and (state!='Diğer' or reproduction!='Bilmiyorum' or birth or ins):
        raise ValueError('Bu bölüm 14 ay ve üzeri dişiler içindir.')
    born=date.fromisoformat(info['born'])
    birth=parse_date(birth) if birth else None
    ins=parse_date(ins) if ins else None
    for day in (birth,ins):
        if day and not born<day<=today: raise ValueError('İşlem tarihi doğumdan sonra ve bugün veya önce olmalı.')
    if birth and state=='Düve': raise ValueError('Düvenin önceki doğumu olamaz; durumunu değiştir.')
    if birth and ins and birth>=ins: raise ValueError('Son doğum, tohumlamadan önce olmalı.')
    if reproduction=='Tohumlandı' and not ins: raise ValueError('Tohumlandı seçtiysen kontrol takvimi için tohumlama tarihini yaz veya şimdilik Bilmiyorum seç.')
    if ins and reproduction not in ('Gebe','Tohumlandı'): raise ValueError('Tohumlama tarihi için Gebe veya Tohumlandı seç.')
    return dict(state=state,pregnant=int(reproduction=='Gebe'),insemination=ins.isoformat() if ins else '',
        last_birth=birth.isoformat() if birth else '',calved_before=1 if birth or state in ('Sağmal','Kuru dönemde') else 0 if state=='Düve' else -1)
