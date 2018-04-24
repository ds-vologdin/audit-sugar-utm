from django.test import TestCase
from datetime import date, timedelta

import audit.views as views

# Create your tests here.


class getReportBeginEendDateTest(TestCase):
    '''
    Тестирование функции get_report_begin_end_date
    '''
    def test_last_parameter(self):
        date_today = date.today()

        self.assertEqual(
            views.get_report_begin_end_date(year='', month='', last='week'),
            (date_today - timedelta(days=6), date_today)
        )
        self.assertEqual(
            views.get_report_begin_end_date(year='', month='', last='month'),
            (date_today - timedelta(days=30), date_today)
        )
        self.assertEqual(
            views.get_report_begin_end_date(year='', month='', last='quarter'),
            (date_today - timedelta(days=90), date_today)
        )
        self.assertEqual(
            views.get_report_begin_end_date(year='', month='', last='year'),
            (date_today.replace(year=(date_today.year-1), day=1), date_today)
        )
        self.assertEqual(
            views.get_report_begin_end_date(year='', month='', last='2years'),
            (date_today.replace(year=(date_today.year-2), day=1), date_today)
        )
        self.assertEqual(
            views.get_report_begin_end_date(year='', month='', last='3years'),
            (date_today.replace(year=(date_today.year-3), day=1), date_today)
        )
