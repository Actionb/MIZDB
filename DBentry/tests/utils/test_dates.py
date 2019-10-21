import datetime

from DBentry import utils
from DBentry.tests.base import MyTestCase


class TestDateUtils(MyTestCase):

    def test_leapdays(self):
        test_data = [
            # start.year == end.year
            ((2001, 1, 1), (2001, 12, 31), 0),  # no leap year
            ((2000, 1, 1), (2000, 12, 31), 1),  # includes leap day
            ((2000, 1, 1), (2000, 2, 29), 1),
            ((2000, 2, 29), (2000, 2, 29), 1),
            ((2000, 2, 29), (2000, 12, 31), 1),
            ((2000, 1, 1), (2000, 1, 2), 0),  # excludes leap day
            ((2000, 11, 11), (2000, 12, 31), 0),
            # start is leap year, end is not leap year
            ((2000, 1, 1), (2001, 1, 1), 1),  # includes leap day
            ((2000, 3, 1), (2001, 1, 1), 0),  # excludes leap day
            # start is not leap year, end is leap year
            ((2003, 3, 1), (2004, 3, 1), 1),  # includes leap day
            ((2003, 1, 1), (2004, 1, 1), 0),  # excludes leap day
            # start and end are leap years
            ((2000, 1, 1), (2004, 1, 1), 1),  # start includes leap day, end excludes it
            ((2000, 3, 1), (2004, 3, 1), 1),  # start excludes leap day, end includes it
            ((2000, 1, 1), (2004, 3, 1), 2),  # start and end include leap days
            ((2000, 3, 1), (2004, 1, 1), 0),  # start and end exclude leap days
            # start > end, leapdays() should swap them
            ((2000, 12, 31), (2000, 1, 1), 1),  # purely for coverage
        ]
        for start, end,  expected in test_data:
            start = datetime.date(*start)
            end = datetime.date(*end)
            with self.subTest(start=str(start), end=str(end)):
                self.assertEqual(utils.leapdays(start, end), expected)
