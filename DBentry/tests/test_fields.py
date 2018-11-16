from .base import *

from django.core.validators import MaxValueValidator, MinValueValidator

from DBentry.constants import MIN_JAHR, MAX_JAHR
from DBentry.fields import *
from DBentry.validators import *

class TestYearField(MyTestCase):
    
    def test_formfield(self):
        # Assert that formfield() passes the MaxValue and the MinValue validators on to the formfield
        formfield = YearField().formfield()
        self.assertEqual(len(formfield.validators), 2)
        if isinstance(formfield.validators[0], MinValueValidator):
            min, max = formfield.validators
        else:
            max, min = formfield.validators
        self.assertIsInstance(min, MinValueValidator)
        self.assertEqual(min.limit_value, MIN_JAHR)
        self.assertIsInstance(max, MaxValueValidator)
        self.assertEqual(max.limit_value, MAX_JAHR)        

class TestStdNumField(MyTestCase):
    
    def test_formfield(self):
        # Assert that formfield() passes the min_length and the validators on to the formfield
        field = StdNumField()
        field.default_validators = [ISSNValidator]
        field.min_length = 1
        formfield = field.formfield()
        self.assertIn(ISSNValidator, formfield.validators)
        self.assertEqual(formfield.min_length, 1)
    
    #TODO: wtf is this test...
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
        field = StdNumField(max_length = 20) # need max_length argument for this base class
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
    
    valid = [] # Can't copy() tuples, dumbnut... remove this comment before committing
    invalid = []
        
    #TODO: this is testing FORMFIELDS, is this intended?
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
    
    def test_conversion_on_save(self):
        # Assert that valid input is saved in the correct format
        isbn = '978456789'
        obj = make(buch, ISBN=isbn)
        self.assertEqual(obj.ISBN, self.field_class()._format_value(isbn))
        
    def test_conversion_on_query(self):
        # Assert that valid input of any format leads to a successful query
        isbn = '978456789'
        obj = make(buch, ISBN=isbn)
        qs = buch.objects.filter(ISBN=isbn)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), obj)
        
    def test_raises_validationerror_on_invalid_save(self):
        # Assert that invalid input results in a ValidationError when saving
        with self.assertRaises(ValidationError):
            buch(buch, ISBN='invalid')
            
    def test_raises_validationerror_on_invalid_query(self):
        # Assert that invalid input results in a ValidationError when querying
        with self.assertRaises(ValidationError):
            buch.objects.filter(ISBN='invalid')
    
class TestISSNField(FieldTestMethodsMixin, MyTestCase):
    valid = ["12345679", "1234-5679"]
    invalid = [
        ("123%&/79", InvalidFormat), 
        ("9"*20, InvalidLength), 
        ('12345671', InvalidChecksum), 
    ]
    field_class = ISSNField
    
    def test_conversion_on_save(self):
        # Assert that valid input is saved in the correct format
        issn = "12345679"
        obj = make(magazin, issn=issn)
        self.assertEqual(obj.issn, self.field_class()._format_value(issn))
        
    def test_conversion_on_query(self):
        # Assert that valid input of any format leads to a successful query
        issn = "12345679"
        obj = make(magazin, issn=issn)
        qs = magazin.objects.filter(issn=issn)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), obj)
        
    def test_raises_validationerror_on_invalid_save(self):
        # Assert that invalid input results in a ValidationError when saving
        with self.assertRaises(ValidationError):
            make(magazin, issn='invalid')
            
    def test_raises_validationerror_on_invalid_query(self):
        # Assert that invalid input results in a ValidationError when querying
        with self.assertRaises(ValidationError):
            magazin.objects.filter(issn='invalid')
        
class TestEANField(FieldTestMethodsMixin, MyTestCase):
    valid = ['73513537', "1234567890128"]
    invalid = [
        ("123%&/()90128", InvalidFormat), 
        ("9"*20, InvalidLength), 
    ]
    invalid.extend([(n[:-1] + '1', InvalidChecksum) for n in valid])
    field_class = EANField
    
    def test_conversion_on_save(self):
        # Assert that valid input is saved in the correct format
        ean = '978-0-471-11709-4'
        obj = make(buch, EAN=ean)
        self.assertEqual(obj.EAN, self.field_class()._format_value(ean))
        
    def test_conversion_on_query(self):
        # Assert that valid input of any format leads to a successful query
        ean = '978-0-471-11709-4'
        obj = make(buch, EAN=ean)
        qs = buch.objects.filter(EAN=ean)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first(), obj)
        
    def test_raises_validationerror_on_invalid_save(self):
        # Assert that invalid input results in a ValidationError when saving
        with self.assertRaises(ValidationError):
            make(buch, EAN='invalid')
            
    def test_raises_validationerror_on_invalid_query(self):
        # Assert that invalid input results in a ValidationError when querying
        with self.assertRaises(ValidationError):
            buch.objects.filter(EAN='invalid')
