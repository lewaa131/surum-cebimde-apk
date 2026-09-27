"""Age/breeding fallback for incomplete imports, never a recorded calving.

24 months is the upper end of the usual 22–24 month first-calving target.
Using it also as a first-service protection boundary is deliberately conservative.
An early service keeps protection indefinitely, even after its estimated due date.
"""
from datetime import date
import calendar


def infer_lactation(cow,today=None):
    today=today or date.today()
    result=dict(estimated=False,first_calving_pending=False)
    if (cow.get('sex')!='Dişi' or cow.get('record_status','Aktif')!='Aktif'
            or cow.get('registry_status','') not in ('','Canlı')
            or cow.get('calved_before',-1)!=-1 or cow.get('last_birth')
            or cow.get('state')!='Diğer'):
        return result
    born=date.fromisoformat(cow['born'])
    boundary=date(born.year+2,born.month,min(born.day,calendar.monthrange(born.year+2,born.month)[1]))
    dates=[date.fromisoformat(d) for d in (cow.get('_first_insemination'),cow.get('insemination')) if d]
    if dates and min(dates)<=boundary:
        result['first_calving_pending']=True
    elif today>=boundary:
        result['estimated']=True
    return result
