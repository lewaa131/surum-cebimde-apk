from datetime import date
from unittest import TestCase
from lactation import infer_lactation


class InferenceTests(TestCase):
    def cow(self,**changes):
        return dict(born='2024-01-01',sex='Dişi',state='Diğer',calved_before=-1,
                    record_status='Aktif',registry_status='Canlı',**changes)

    def test_service_at_15_months_stays_protected_past_due_date(self):
        cow=self.cow(insemination='2025-04-01')
        for day in (date(2025,12,31),date(2026,1,1),date(2027,1,1)):
            self.assertEqual(infer_lactation(cow,day),dict(estimated=False,first_calving_pending=True))

    def test_failed_early_service_is_still_protected_after_later_service(self):
        cow=self.cow(_first_insemination='2025-04-01',insemination='2026-03-01')
        self.assertTrue(infer_lactation(cow,date(2026,9,27))['first_calving_pending'])
        cow['insemination']=''
        self.assertFalse(infer_lactation(cow,date(2026,9,27))['estimated'])

    def test_mature_unknown_fallback_and_calendar_boundary(self):
        cow=self.cow()
        self.assertFalse(infer_lactation(cow,date(2025,12,31))['estimated'])
        self.assertTrue(infer_lactation(cow,date(2026,1,1))['estimated'])
        cow['insemination']='2026-03-01'
        self.assertTrue(infer_lactation(cow,date(2026,9,27))['estimated'])

    def test_late_first_service_at_boundary_remains_protected(self):
        self.assertTrue(infer_lactation(self.cow(insemination='2026-01-01'),date(2026,9,27))['first_calving_pending'])

    def test_real_records_and_explicit_status_override_inference(self):
        for change in (dict(calved_before=0),dict(calved_before=1),dict(last_birth='2025-12-01'),
                       dict(state='Kuru dönemde'),dict(state='Sağılmıyor'),dict(state='Sağmal'),
                       dict(sex='Erkek'),dict(record_status='Satıldı')):
            result=infer_lactation(self.cow(insemination='2025-04-01')|change,date(2026,9,27))
            self.assertEqual(result,dict(estimated=False,first_calving_pending=False))

    def test_leap_day_birth(self):
        cow=self.cow()|dict(born='2024-02-29')
        self.assertFalse(infer_lactation(cow,date(2026,2,27))['estimated'])
        self.assertTrue(infer_lactation(cow,date(2026,2,28))['estimated'])
