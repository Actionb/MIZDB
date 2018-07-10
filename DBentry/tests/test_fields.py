from .base import *

from DBentry.fields import *
from DBentry.validators import *

class TestStdNumField(MyTestCase):
    
    def test_formfield(self):
        # Assert that formfield() passes the min_length and the validators on to the formfield
        field = StdNumField()
        field.default_validators = [ISSNValidator]
        field.min_length = 1
        formfield = field.formfield()
        self.assertIn(ISSNValidator, formfield.validators)
        self.assertEqual(formfield.min_length, 1)
        
    def test_pre_save(self):
        # Assert that pre_save formats the value and updates the model instance accordingly
        field = StdNumField()
        field.attname = 'x'
        field._format_value = mockv("ABCD")
        
        instance = Mock(x="12345679")
        self.assertEqual(field.pre_save(instance, True), "ABCD")
        
    def test_add_check_digit(self):
        # Assert that a check digit is added to 'value' if its length is equal to min_length
        field = StdNumField()
        field.min_length = 7
        field.stdnum = issn
        self.assertEqual(len(field._add_check_digit("1234567")), 8)
        field.stdnum = ean
        self.assertEqual(len(field._add_check_digit("1234567")), 8)
        field.min_length = 1
        self.assertEqual(len(field._add_check_digit("1234567")), 7)
        
    def test_format_value(self):
        # Assert that _format_value formats the given value 
        # ean has no 'format' attribute, value should be 'compact'ed instead
        field = StdNumField()
        field.stdnum = ean
        ean_13 = "1234-5678-9012-8"
        self.assertEqual(field._format_value(ean_13), ean.compact(ean_13))
        
        # issn can do pretty formats
        field.stdnum = issn
        self.assertEqual(field._format_value("12345679"), "1234-5679")
        
        # or just return the value if stdnum has neither format nor compact
        field.stdnum = None
        self.assertEqual(field._format_value("12345679"), "12345679")
        
        # Assert that _format_value does not care about AttributeErrors raised in _add_check_digit
        field._add_check_digit = mockex(AttributeError())
        with self.assertNotRaises(AttributeError):
            field._format_value("1")

class FieldTestMethodsMixin(object):
    
    valid = ()
    invalid = ()
        
    def test_valid_input(self):
        ff = self.field_class().formfield()
        for v in self.valid.copy():
            with self.assertNotRaises(ValidationError):
                ff.clean(v)
            # Also test values with missing check digits
            with self.assertNotRaises(ValidationError, msg = 'A stdnum without its check digit should validate.'):
                ff.clean(v.replace('-', '')[:-1])
        
    def test_invalid_input(self):
        ff = self.field_class().formfield()
        for v, exception in self.invalid.copy():
            with self.assertRaises(ValidationError, msg = v) as cm:
                ff.clean(v)
            # The exception stored in the context manager is actually ValidationError raised by clean 
            # with all collected errors in its 'error_list' attribute
            self.assertIn(exception.message, [e.message for e in cm.exception.error_list])

class TestISBNField(FieldTestMethodsMixin, MyTestCase):
    
    valid = ['978456789X', "1-234-56789-X", '9784567890120', '978-4-56-789012-0']
    invalid = [
        ("9999!)()/?`*", InvalidFormat), 
        ("9"*20, InvalidLength), 
        ("1234567890128", InvalidComponent)
    ]
    invalid.extend([(n[:-1] + '1', InvalidChecksum) for n in valid])
    field_class = ISBNField
    
    def test_format_value(self):
        # ISBNField._format_value should always convert into a formatted isbn13 number 
        field = self.field_class()
        expected = '978-978-45678-9-3'
        self.assertEqual(field._format_value('978456789X'), expected)
        self.assertEqual(field._format_value('978456789'), expected)
        self.assertEqual(field._format_value('9789784567893'), expected)
        self.assertEqual(field._format_value('978978456789'), expected)
    
class TestISSNField(FieldTestMethodsMixin, MyTestCase):
    valid = ["12345679", "1234-5679"]
    invalid = [
        ("123%&/79", InvalidFormat), 
        ("9"*20, InvalidLength), 
        ('12345671', InvalidChecksum), 
    ]
    field_class = ISSNField
    
class TestEANField(FieldTestMethodsMixin, MyTestCase):
    valid = ['73513537', "1234567890128"]
    invalid = [
        ("123%&/()90128", InvalidFormat), 
        ("9"*20, InvalidLength), 
    ]
    invalid.extend([(n[:-1] + '1', InvalidChecksum) for n in valid])
    field_class = EANField
