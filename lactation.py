"""Farm preference: estimate milking at 24 months only when history is unknown."""
from datetime import date


def estimate_milking(cow, today=None):
    today=today or date.today()
    born=date.fromisoformat(cow['born'])
    months=(today.year-born.year)*12+today.month-born.month-(today.day<born.day)
    return (months>=24 and cow.get('sex')=='Dişi'
            and cow.get('record_status','Aktif')=='Aktif'
            and cow.get('registry_status','') in ('','Canlı')
            and cow.get('calved_before',-1)==-1
            and cow.get('state')=='Diğer' and not cow.get('last_birth'))
