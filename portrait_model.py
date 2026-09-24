"""Temsili çizim seçimi; gerçek görünüm veya sağlık bilgisi çıkarımı yapmaz."""
from datetime import date
import hashlib
import unicodedata

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',(text or '').casefold().replace('ı','i')) if not unicodedata.combining(c))

def portrait_traits(cow,today=None):
    today = today or date.today()
    born = date.fromisoformat(cow['born'])
    months = (today.year-born.year)*12+today.month-born.month-(today.day<born.day)
    breed,species = normalized(cow.get('breed')),normalized(cow.get('species'))
    family = 'generic'
    if 'manda' in species or 'manda' in breed: family='buffalo'
    elif any(x in breed for x in ('holstein','holstayn','siyah alaca','kirmizi alaca')):
        family='red_holstein' if any(x in breed for x in ('kirmizi','red','-ka',' ka')) else 'holstein'
    elif any(x in breed for x in ('simental','simmental','simmenthal','simenthal')): family='simmental'
    elif 'jersey' in breed: family='jersey'
    elif any(x in breed for x in ('esmer','brown','montofon','montafon')): family='brown'
    elif 'angus' in breed: family='red_angus' if any(x in breed for x in ('red','kirmizi')) else 'angus'
    elif any(x in breed for x in ('sarole','charolais','charolaise')): family='charolais'
    elif any(x in breed for x in ('limuzin','limousin','limosin')): family='limousin'
    elif 'yerli kara' in breed: family='native_black'
    elif 'boz' in breed: family='grey'
    return family,('calf' if months<12 else 'young' if months<24 else 'adult'),cow.get('sex','Bilinmiyor')

NAMES = {'holstein':'Siyah alaca','red_holstein':'Kırmızı alaca','simmental':'Simental',
         'jersey':'Jersey','brown':'Esmer / Montofon','buffalo':'Manda','angus':'Angus',
         'red_angus':'Kırmızı Angus','charolais':'Şarole','limousin':'Limuzin',
         'native_black':'Yerli kara','grey':'Boz','generic':'Genel sığır'}

def portrait_caption(cow):
    family,age,sex=portrait_traits(cow)
    stage={'calf':'buzağı','young':'genç','adult':'yetişkin'}[age]
    if family=='generic': return f'Temsili · Irk eşleşmedi · {stage}'
    return f'Temsili · {NAMES[family]} · {stage}'

def pattern_seed(cow):
    return int.from_bytes(hashlib.sha256(cow.get('tag','').encode()).digest()[:8],'big')
