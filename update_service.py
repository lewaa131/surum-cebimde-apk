"""Public release metadata and bounded, verified APK downloads."""
import hashlib
import json
import re
import ssl
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import certifi

REPOSITORY = 'lewaa131/surum-cebimde-apk'
MAX_APK = 200 * 1024 * 1024


def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{1,3}\.\d{1,3}\.\d{1,3}',value):
        raise ValueError('Güncelleme sürümü geçersiz.')
    return tuple(map(int,value.split('.')))


def validate(data,current):
    target=version(data['version'])
    if target<=version(current): return None
    expected=100000000+target[0]*1000000+target[1]*1000+target[2]
    if data.get('package')!='org.surutakip.surum' or data.get('version_code')!=expected:
        raise ValueError('Güncelleme paketi uyuşmuyor.')
    url=data.get('url','')
    prefix=f'https://github.com/{REPOSITORY}/releases/download/v{data["version"]}/'
    if url!=prefix+'surum-cebimde.apk': raise ValueError('Güncelleme adresi geçersiz.')
    if type(data.get('size')) is not int or not 0<data['size']<=MAX_APK:
        raise ValueError('Güncelleme boyutu geçersiz.')
    if not re.fullmatch('[a-f0-9]{64}',data.get('sha256','')):
        raise ValueError('Güncelleme doğrulaması eksik.')
    return data


def request(url):
    return urlopen(Request(url,headers={'User-Agent':'Surum-Cebimde-Updater','Cache-Control':'no-cache'}),
                   timeout=25,context=ssl.create_default_context(cafile=certifi.where()))


def check(current):
    try:
        with request(f'https://github.com/{REPOSITORY}/releases/latest/download/update.json') as response:
            raw=response.read(32769)
    except HTTPError as exc:
        if exc.code==404: return None
        raise
    if len(raw)>32768: raise ValueError('Güncelleme bilgisi çok büyük.')
    return validate(json.loads(raw),current)


def download(data,folder,cancel,progress):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    temporary=folder/'update.part'; target=folder/'update.apk'
    digest=hashlib.sha256(); count=0; started=time.monotonic(); last=-1
    try:
        with request(data['url']) as response, temporary.open('wb') as out:
            while True:
                if cancel.is_set(): raise ValueError('İndirme iptal edildi.')
                if time.monotonic()-started>600: raise ValueError('İndirme zaman aşımına uğradı.')
                block=response.read(128*1024)
                if not block: break
                count+=len(block)
                if count>data['size']: raise ValueError('İndirilen dosyanın boyutu uyuşmuyor.')
                out.write(block); digest.update(block)
                percent=count*100//data['size']
                if percent!=last: progress(percent); last=percent
        if cancel.is_set(): raise ValueError('İndirme iptal edildi.')
        if count!=data['size'] or digest.hexdigest()!=data['sha256']:
            raise ValueError('Dosya eksik veya bozuk; tekrar indir.')
        temporary.replace(target)
        return target
    finally:
        temporary.unlink(missing_ok=True)
