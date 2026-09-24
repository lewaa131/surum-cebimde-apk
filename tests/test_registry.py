import unittest
from registry import Page, parse_result, normalize_tag, LookupError

TAG = 'TR350004339192'
def result(sex='Dişi',tag=TAG):
    return f'''<dl><dt>Küpe No</dt><dd>{tag}</dd><dt>Doğum Tarihi</dt><dd>26/08/2022</dd>
    <dt>Irkı</dt><dd>Holstein-SA</dd><dt>Türü</dt><dd>Sığır</dd>
    <dt>Cinsiyeti</dt><dd>{sex}</dd><dt>Durumu</dt><dd>Canlı</dd></dl>
    <table><tr><th>Aşı Tarihi</th><th>Aşı Grubu</th></tr><tr><td>12/03/2023</td><td>BRUCELLA</td></tr>
    <tr><td>29/06/2026</td><td>ŞAP</td></tr></table>'''

class RegistryTests(unittest.TestCase):
    def test_valid_result_and_vaccination_sort(self):
        info = parse_result(result(),TAG)
        self.assertEqual(info['born'],'2022-08-26')
        self.assertEqual(info['sex'],'Dişi')
        self.assertEqual(info['vaccinations'][0],{'date':'2026-06-29','group':'ŞAP'})

    def test_male_and_unknown_not_converted_to_female(self):
        self.assertEqual(parse_result(result('Erkek'),TAG)['sex'],'Erkek')
        self.assertEqual(parse_result(result(''),TAG)['sex'],'')

    def test_wrong_or_unavailable_result_rejected(self):
        for html in (result(tag='TR000000000000'),'<p>Hizmet kullanılamıyor</p>',result().replace('26/08/2022','99/99/9999')):
            with self.subTest(html=html):
                with self.assertRaises(LookupError): parse_result(html,TAG)

    def test_form_session_token(self):
        p = Page(); p.feed('<form name="mainForm" action="/lookup?submit"><input name="token" value="abc&amp;123"></form>')
        self.assertEqual(p.token,'abc&123'); self.assertEqual(p.action,'/lookup?submit')

    def test_tag(self):
        self.assertEqual(normalize_tag(' tr350004339192 '),TAG)
        for tag in ('','TR123','TR35000433919x',TAG+'0'):
            with self.assertRaises(LookupError): normalize_tag(tag)
