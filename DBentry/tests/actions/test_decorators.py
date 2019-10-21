from django.test import SimpleTestCase

from DBentry.actions.decorators import add_cls_attrs

def dummy_func0():
    pass
    
def dummy_func1():
    pass
dummy_func1.short_description = 'Beep'
dummy_func1.perm_required = 'Boop'

class TestAddClsAttrsDecorator(SimpleTestCase):
    
    def test_deco_with_cls_attrs_and_no_func_attrs(self):
        dummy_view = type('Dummy', (object, ), {'short_description':'Testdesc', 'perm_required':'Nope'})
        decorated_func = add_cls_attrs(dummy_view)(dummy_func0)
        self.assertEqual(decorated_func.short_description, 'Testdesc')
        self.assertEqual(decorated_func.perm_required, 'Nope')
        
    def test_deco_with_cls_attrs_and_func_attrs(self):
        # decorator should not overwrite attributes set on the function
        dummy_view = type('Dummy', (object, ), {'short_description':'Testdesc', 'perm_required':'Nope'})
        decorated_func = add_cls_attrs(dummy_view)(dummy_func1)
        self.assertEqual(decorated_func.short_description, 'Beep')
        self.assertEqual(decorated_func.perm_required, 'Boop')
