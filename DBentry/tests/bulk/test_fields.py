from ..base import *

from DBentry.bulk.fields import *

class TestBulkField(MyTestCase):
    
    @translation_override(language = None)
    def test_init_error_msg_text(self):
        # The error message should depend on the settings of the BulkField
        field = BulkField()
        expected = 'Unerlaubte Zeichen gefunden: Bitte nur Ziffern oder "," oder "/" oder "-" oder "*" benutzen.'
        self.assertEqual(field.error_messages['invalid'], expected)
        field = BulkField(allowed_special = ['^'])
        expected = 'Unerlaubte Zeichen gefunden: Bitte nur Ziffern oder "^" benutzen.'
        self.assertEqual(field.error_messages['invalid'], expected)
        
        field = BulkField(allowed_special = ['^'], allowed_numerical = False)
        expected = 'Unerlaubte Zeichen gefunden: Bitte nur "^" benutzen.'
        self.assertEqual(field.error_messages['invalid'], expected)
        
        field = BulkField(allowed_special = ['^'], allowed_numerical = True, allowed_alpha = True)
        expected = 'Unerlaubte Zeichen gefunden: Bitte nur Ziffern (plus Buchstaben-Kürzel) oder "^" benutzen.'
        self.assertEqual(field.error_messages['invalid'], expected)
        
    def test_regex(self):
        # The regex should depend on the settings of the BulkField
        field = BulkField()
        
        # the default
        pattern = field.regex.pattern
        self.assertEqual(pattern, '\\,|\\/|\\-|\\*|\\s+|[0-9]')
        
        field.allowed_special = ['^']
        field.allowed_numerical = False
        field.allowed_space = False
        field.allowed_alpha = False
        self.assertEqual(field.regex.pattern, '\\^')
        
        field.allowed_special = []
        field.allowed_space = True
        self.assertEqual(field.regex.pattern, '\\s+')
        
        field.allowed_numerical = True
        field.allowed_space = False
        self.assertEqual(field.regex.pattern, '[0-9]')
        
        field.allowed_numerical = False
        field.allowed_alpha = True
        self.assertEqual(field.regex.pattern, '[a-zA-Z]')
        
    def test_validate(self):
        # Assert that a ValidationError is raised when the regex does not match
        with self.assertNotRaises(ValidationError):
            BulkField().validate('1')
            
        with self.assertRaises(ValidationError) as cm:
            BulkField().validate('A')
        expected = 'Unerlaubte Zeichen gefunden: Bitte nur Ziffern oder "," oder "/" oder "-" oder "*" benutzen.'
        self.assertEqual(cm.exception.message, expected)
        self.assertEqual(cm.exception.code, 'invalid')
    
    def test_clean(self):
        # Assert that clean strips 'value' 
        self.assertEqual(BulkField().clean(' 1 , '), '1')
        self.assertEqual(BulkField(allowed_alpha = True).clean(' 1 A '), '1A')
        self.assertEqual(BulkField().clean(' , 1 '), '1')
        
    def test_to_list(self):
        field = BulkField()
        self.assertEqual(field.to_list(None), ([], 0))
        
        self.assertEqual(field.to_list(',1'), (['1'], 1))
        
        expected = (['1', '2', '3', '4'], 4)
        self.assertEqual(field.to_list('1, 2, 3, 4'), expected)
        
        expected = (['1', ['2'], ['3'], ['4']], 4)
        self.assertEqual(field.to_list('1, 2 - 4'), expected)
        
        self.assertEqual(field.to_list('1, 2 - 4*1'), expected)
        expected = (['1', ['2', '3'], ['4', '5']], 3)
        self.assertEqual(field.to_list('1, 2 - 4*2'), expected)
        expected = (['1', ['2', '3', '4'], ['5', '6', '7']], 3)
        self.assertEqual(field.to_list('1, 2 - 5*3'), expected)
        
        expected = (['1', ['2'], ['3'], ['4'], ['5', '6', '7']], 5)
        self.assertEqual(field.to_list('1, 2 - 4, 5/6/7'), expected)
        
class TestBulkJahrField(MyTestCase):
    
    @translation_override(language = None)
    def test_clean(self):
        # Assert that clean returns a string of years with only a ',' seperator
        field = BulkJahrField()
        self.assertEqual(field.clean('2015, 2016'), '2015,2016')
        self.assertEqual(field.clean('2015/ 2016, 2017, '), '2015,2016,2017')
        
        with self.assertRaises(ValidationError) as cm:
            field.clean('15, 16')
        self.assertEqual(cm.exception.args[0], 'Bitte vierstellige Jahresangaben benutzen.')
        
    def test_to_list(self):
        # the second value of the tuple returned by BulkJahrField.to_list should always be 0
        field = BulkJahrField()
        self.assertEqual(field.to_list('15,16,17/18')[1], 0)
