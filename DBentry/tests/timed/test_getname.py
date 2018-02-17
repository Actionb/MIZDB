from .base import *

@skip("Beep.")
class TestTimedCNGetName(TimedTestCase, DataTestCase):
    
    file_name = "timed_test_getname.txt"
    model = ausgabe
    test_data_count = 1000
    add_relations = True
    
    def setUp(self):
        super().setUp()
        # Force a name update with the most required operations possible (lnum sets)
        self.queryset.update(_name='Time me!')
    
    def test_classmethod_get_names(self):
        self.time(self.queryset._update_names, func_name='classmethod_get_names')
    
