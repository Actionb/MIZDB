import datetime

from DBentry import utils
from DBentry.tests.base import MyTestCase

class TestDateUtils(MyTestCase):
    
    def test_leapdays(self):
        # start.year == end.year no leap year
        self.assertEqual(utils.leapdays(datetime.date(2001, 1, 1), datetime.date(2001, 12, 31)), 0)
        # start.year == end.year with leap year including leap day
        self.assertEqual(utils.leapdays(datetime.date(2000, 1, 1), datetime.date(2000, 12, 31)), 1)
        # start.year == end.year with leap year excluding leap day
        self.assertEqual(utils.leapdays(datetime.date(2000, 1, 1), datetime.date(2000, 1, 2)), 0)
        self.assertEqual(utils.leapdays(datetime.date(2000, 11, 11), datetime.date(2000, 12, 31)), 0)
        
        # start > end, leapdays should swap them
        self.assertEqual(utils.leapdays(datetime.date(2000, 12, 31), datetime.date(2000, 1, 1)), 1)
        
        # start is leap year, end is not leap year
        # including leap day
        self.assertEqual(utils.leapdays(datetime.date(2000, 1, 1), datetime.date(2001, 1, 1)), 1)
        
        # excluding leap day
        self.assertEqual(utils.leapdays(datetime.date(2000, 3, 1), datetime.date(2001, 3, 1)), 0)
        
        # start is not leap year, end is leap year
        # including leap day
        self.assertEqual(utils.leapdays(datetime.date(2003, 3, 1), datetime.date(2004, 3, 1)), 1)
        
        # excluding leap day
        self.assertEqual(utils.leapdays(datetime.date(2003, 1, 1), datetime.date(2004, 1, 1)), 0)
        
        # start and end are leap years
        # start includes leap day, end excludes it
        self.assertEqual(utils.leapdays(datetime.date(2000,1,1), datetime.date(2004,1,1)), 1)
        
        # start excludes leap day, end includes it
        self.assertEqual(utils.leapdays(datetime.date(2000,3,1), datetime.date(2004,3,1)), 1)
        
        # start and end includes leap days
        self.assertEqual(utils.leapdays(datetime.date(2000,1,1), datetime.date(2004,3,1)), 2)
        
        # start and end exclude leap days
        self.assertEqual(utils.leapdays(datetime.date(2000,3,1), datetime.date(2004,1,1)), 0)
        
    def test_build_date(self):
        self.assertEqual(utils.build_date([2000], [1], 31), datetime.date(2000, 1, 31))
        self.assertEqual(utils.build_date([2000], [1], None), datetime.date(2000, 1, 1))
        
        self.assertEqual(utils.build_date([2001, 2000], [12], None), datetime.date(2000, 12, 1))
        # If there's more than one month, build_date should set the day to the last day of the min month
        self.assertEqual(utils.build_date([None, 2000], [12, 2], None), datetime.date(2000, 2, 29))
        # If there's more than one month and more than one year, 
        # build_date should set the day to the last day of the max month
        self.assertEqual(utils.build_date([2001, 2000], [12, 1], None), datetime.date(2000, 12, 31))
        
        self.assertIsNone(utils.build_date([None], [None]))
        self.assertIsNotNone(utils.build_date(2000, 1))
        
