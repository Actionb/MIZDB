from .base import MyTestCase, translation_override

from django.core.exceptions import ValidationError

from DBentry.validators import (
    ISSNValidator, ISBNValidator, EANValidator, 
    InvalidChecksum, InvalidComponent, InvalidFormat, InvalidLength
)

class TestStdNumValidators(MyTestCase):
    # Assert that the validators reraise the correct django.ValidationError subclass
    
    @translation_override(language = None)
    def run_validators(self, validator, invalid):
        msg = "\nUnexpected exception raised. Expected: {}, got: {}"
        with self.collect_fails() as collector:
            for invalid_number, exception_class in invalid:
                with collector():
                    with self.assertRaises(ValidationError) as cm:
                        validator(invalid_number)
                    self.assertEqual(cm.exception.__class__, exception_class, msg = msg.format(cm.exception.__class__.__name__, exception_class.__name__))
    
    def test_isbn_validator(self):
        invalid = [
            ("9999!)()/?1*", InvalidFormat), 
            ("9"*20, InvalidLength), 
            ("1234567890128", InvalidComponent),
            ('1234567890', InvalidChecksum), 
            ('1-234-56789-0', InvalidChecksum), 
            ('9781234567890', InvalidChecksum), 
            ('978-1-234-56789-0', InvalidChecksum), 
        ]
        self.run_validators(ISBNValidator, invalid)
        
    def test_issn_validator(self):
        invalid = [
            ("123%&/79", InvalidFormat), 
            ("9"*20, InvalidLength), 
            ('12345670', InvalidChecksum), 
            ("1234-5670", InvalidChecksum), 
        ]
        self.run_validators(ISSNValidator, invalid)
        
    def test_ean_validator(self):
        invalid = [
            ("123%&/()90128", InvalidFormat), 
            ("9"*20, InvalidLength), 
            ('73513538', InvalidChecksum), 
            ("1234567890123", InvalidChecksum), 
        ]
        self.run_validators(EANValidator, invalid)
