# Test the custom assertions

import unittest

class X(object):
    
    def assertDictKeysEqual(self, d1, d2):
        t = "dict keys missing from {d}: {key_diff}"
        msg = ''
        key_diff = set(d1.keys()) - set(d2.keys())
        if key_diff:
            msg = t.format(d='d2', key_diff=str(key_diff))
        
        key_diff = set(d2.keys()) - set(d1.keys())
        if key_diff:
            if msg:
                msg += '\n'
            msg +=  t.format(d='d1', key_diff=str(key_diff))
        if msg:
            raise AssertionError(msg)
    
    def assertDictsEqual(self, dict1, dict2, msg=''):
        d1 = dict1.copy()
        d2 = dict2.copy()
        self.assertDictKeysEqual(d1, d2)
        
        t = "dict values differ for key {k}: \n{v1} \n!=\n{v2}\n\n\n"
        msg = ''
        for k, v in d1.items():
            v1 = v
            v2 = d2.get(k)
            if isinstance(v1, dict) and isinstance(v2, dict):
                try:
                    self.assertDictsEqual(v1, v2)
                except AssertionError as e:
                    msg += "subdicts for key {k} differ: {msg}\n\n\n".format(k=k, msg=e.args[0])
            else:
                v1 = str(v1)
                v2 = str(v2)
                if v1 != v2:
                    msg += t.format(k=k, v1=v1, v2=v2)
        if msg:
            raise AssertionError(msg)

class TestMyTestCase(unittest.TestCase):
    
    def test_dictkeys(self):
        func = X().assertDictKeysEqual
        d1 = dict(a=1)
        d2 = dict(a=2)
        func(d1, d2)
            
        d1 = dict(a=1)
        d2 = dict(b=2)
        with self.assertRaises(AssertionError) as e:
            func(d1, d2)
        
        d1 = dict(a=1, b=2)
        d2 = dict(b=2)
        with self.assertRaises(AssertionError) as e:
            func(d1, d2)
        
        
        d1 = dict(a=1)
        d2 = dict(a=1, b=2)
        with self.assertRaises(AssertionError) as e:
            func(d1, d2)
        
        d1 = dict(a=1, c=3)
        d2 = dict(a=1, b=2)
        with self.assertRaises(AssertionError) as e:
            func(d1, d2)
        
    def test_dicts(self):
        func = X().assertDictsEqual
        d1 = dict(a=1)
        d2 = dict(a=1)
        func(d1, d2)
        
        d1 = dict(a=1)
        d2 = dict(a=2)
        with self.assertRaises(AssertionError) as e:
            func(d1, d2)
        
        d1 = dict(a=1)
        d2 = dict(a='1')
        func(d1, d2)
        
        d1 = dict(a=1)
        d2 = dict(a='2')
        with self.assertRaises(AssertionError) as e:
            func(d1, d2)
        
        d1 = dict(a={'b':1})
        d2 = dict(a={'b':1})
        func(d1, d2)
        
        d1 = dict(a={'b':1})
        d2 = dict(a={'b':2})
        with self.assertRaises(AssertionError) as e:
            func(d1, d2)
    

if __name__ == '__main__':
    unittest.main()
