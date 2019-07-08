from collections import OrderedDict

from DBentry import utils
from DBentry.tests.base import MyTestCase

class TestUtils(MyTestCase):
    
    def test_is_iterable(self):
        self.assertTrue(utils.is_iterable(list()))
        self.assertTrue(utils.is_iterable(tuple()))
        self.assertTrue(utils.is_iterable(dict()))
        self.assertTrue(utils.is_iterable(set()))
        self.assertTrue(utils.is_iterable(OrderedDict()))
        self.assertFalse(utils.is_iterable("abc"))
        
    def test_flatten_dict(self):
        d = {
            'dont_flatten' : 1, 
            'dont_flatten_str' : 'abc', 
            'dont_flatten_iterable' : [1, 2], 
            'flatten' : [3], 
            'excluded' : [4], 
            'recursive' : {
                'dont_flatten' : 1, 
                'flatten' : [2], 
                'excluded' : [4]
            }, 
        }
        
        flattened = utils.flatten_dict(d, exclude = ['excluded'])
        self.assertEqual(flattened['dont_flatten'], 1)
        self.assertEqual(flattened['dont_flatten_str'], 'abc')
        self.assertEqual(flattened['dont_flatten_iterable'], [1, 2])
        self.assertEqual(flattened['flatten'], 3)
        self.assertEqual(flattened['excluded'], [4])
        self.assertEqual(flattened['recursive']['dont_flatten'], 1)
        self.assertEqual(flattened['recursive']['flatten'], 2)
        self.assertEqual(flattened['recursive']['excluded'], [4])
  
