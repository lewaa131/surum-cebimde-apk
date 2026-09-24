import unittest
from date_entry import format_date_entry, complete_date_entry
from herd import parse_date
from datetime import date


class DateEntryTests(unittest.TestCase):
    def test_deleted_separator_keeps_year(self):
        for value in ('01.092026','0109.2026','01092026'):
            self.assertEqual(complete_date_entry(value),'01.09.2026')
        self.assertEqual(format_date_entry('01.09202'),'01.09.202')

    def test_numeric_paste_and_single_digit_segments(self):
        for source in ('01092026', '1.9.2026', '1/9/2026', '01.09.2026'):
            self.assertEqual(complete_date_entry(source), '01.09.2026')
            self.assertEqual(parse_date(complete_date_entry(source)), date(2026,9,1))

    def test_partial_input_and_deletion_remain_editable(self):
        for source, expected in [('0','0'),('01','01'),('010','01.0'),('0109','01.09'),('01092','01.09.2'),('1.','01.'),('1.9.','01.09.')]:
            self.assertEqual(format_date_entry(source), expected)

    def test_invalid_dates_not_silently_changed(self):
        for source in ('31.02.2026','29.02.2025','00.09.2026'):
            with self.assertRaises(ValueError): parse_date(complete_date_entry(source))
        self.assertEqual(complete_date_entry('29022024'),'29.02.2024')
