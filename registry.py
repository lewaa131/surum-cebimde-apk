"""Resmi, herkese açık küpe formunu kullanır; resmi bir API değildir."""
from datetime import date, datetime
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import re
import ssl
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler, Request
from urllib.error import URLError

URL = 'https://www.turkiye.gov.tr/gtvh-kupe-ile-buyukbas-hayvan-sorgulama'

class LookupError(ValueError):
    pass

def normalize_tag(value):
    value = value.strip().upper()
    if not re.fullmatch(r'TR\d{12}', value):
        raise LookupError('Küpe TR ve ardından 12 rakam olmalı.')
    return value

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None
        self.token = None
        self.in_form = False
        self.fields = {}
        self.key = None
        self.cell = None
        self.text = []
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form' and attrs.get('name') == 'mainForm':
            self.in_form = True
            self.action = attrs.get('action')
        if self.in_form and tag == 'input' and attrs.get('name') == 'token':
            self.token = attrs.get('value')
        if tag in ('dt', 'dd', 'td'):
            self.cell = tag
            self.text = []
        if tag == 'tr':
            self.row = []

    def handle_data(self, data):
        if self.cell:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == 'form':
            self.in_form = False
        if tag == self.cell:
            value = ' '.join(''.join(self.text).split())
            if tag == 'dt':
                self.key = value
            elif tag == 'dd' and self.key:
                self.fields[self.key] = value
                self.key = None
            elif tag == 'td':
                self.row.append(value)
            self.cell = None
        if tag == 'tr' and len(self.row) == 2:
            self.rows.append(self.row)

def parse_result(html, requested_tag):
    page = Page()
    page.feed(html)
    values = page.fields
    if values.get('Küpe No') != normalize_tag(requested_tag):
        raise LookupError('Kayıt doğrulanamadı. Numara bulunamadı veya resmi hizmet yanıt vermiyor. Tekrar deneyin.')
    try:
        born = datetime.strptime(values['Doğum Tarihi'], '%d/%m/%Y').date()
        if born > date.today():
            raise ValueError()
    except (KeyError, ValueError):
        raise LookupError('Resmi kayıttaki doğum tarihi okunamadı; hayvan eklenmedi.') from None
    vaccines = []
    for day, group in page.rows:
        try:
            day = datetime.strptime(day, '%d/%m/%Y').date().isoformat()
        except ValueError:
            continue
        vaccines.append({'date': day, 'group': group})
    return dict(tag=requested_tag.upper().strip(), born=born.isoformat(),
                breed=values.get('Irkı', ''), species=values.get('Türü', ''),
                sex=values.get('Cinsiyeti', 'Bilinmiyor'),
                registry_status=values.get('Durumu', ''),
                vaccinations=sorted(vaccines, key=lambda v: v['date'], reverse=True),
                checked_at=datetime.now().isoformat(timespec='seconds'))

def lookup(tag):
    tag = normalize_tag(tag)
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    try:
        context.set_alpn_protocols(['http/1.1'])
    except (AttributeError, NotImplementedError):
        # Some Android/OpenSSL builds do not expose ALPN; HTTPS still works.
        pass
    opener = build_opener(HTTPCookieProcessor(CookieJar()), HTTPSHandler(context=context))
    opener.addheaders = [('User-Agent', 'Surum/0.2 (personal herd tracker)')]
    try:
        with opener.open(URL, timeout=20) as response:
            page = Page()
            page.feed(response.read(2_000_000).decode('utf-8'))
        if not page.token or not page.action:
            raise LookupError('Resmi sorgulama formu şu anda kullanılamıyor.')
        action = urljoin(URL, page.action)
        if urlparse(action).hostname != 'www.turkiye.gov.tr' or urlparse(action).scheme != 'https':
            raise LookupError('Sorgulama adresi değişmiş; işlem durduruldu.')
        request = Request(action, urlencode({'kupeNo': tag, 'token': page.token}).encode(),
                          headers={'Referer': URL, 'Content-Type': 'application/x-www-form-urlencoded'})
        with opener.open(request, timeout=25) as response:
            return parse_result(response.read(2_000_000).decode('utf-8'), tag)
    except (URLError, TimeoutError, OSError, UnicodeError):
        raise LookupError('Resmi hizmete bağlanılamadı. İnterneti kontrol edip tekrar deneyin.') from None
