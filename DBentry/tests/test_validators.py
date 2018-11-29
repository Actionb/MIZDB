from .base import MyTestCase

from DBentry.validators import *
from DBentry.validators import _add_check_digit, _validate

class TestValidators(MyTestCase):
    
    def test_add_check_digit(self):
        # Assert that _add_check_digit adds a check digit if the length of the number string passed in 
        # is equal to min_length; the ISBNValidator does this on its own so no need to check with isbn.
        self.assertEqual(len(_add_check_digit(issn, "1234567", 7)), 8)
        self.assertEqual(len(_add_check_digit(ean, "1234567", 7)), 8)
        
        # _add_check_digit should simply return the number if its len is unequal to min_length
        self.assertEqual(len(_add_check_digit(issn, "1234567", 1)), 7)
        
        # _add_check_digit should raise an InvalidComponent exception if number is not numeric
        with self.assertRaises(InvalidComponent):
            _add_check_digit(issn, "!", 1)
            
    def test_validate(self):
        self.assertTrue(_validate(issn, "12345679"))
        
        # Assert that _validate raises appropriate exceptions
        with self.assertRaises(InvalidLength):
            _validate(issn, "12")
            
        with self.assertRaises(InvalidFormat):
            _validate(issn, "!")
            
        with self.assertRaises(InvalidChecksum):
            _validate(issn, "12345671") # last digit should be 9
            
        with self.assertRaises(InvalidComponent):
            _validate(isbn, "1234567890128") # isbn13 should lead with '978' or '979'
            
        # Assert that _validate adds a check digit if required
        # "1234567" should not validate without the missing check digit
        self.assertTrue(_validate(issn, "1234567", min_length = 7))
        
    def test_isbn_validator(self):
        isbn_10 = '978456789X'
        self.assertTrue(ISBNValidator(isbn_10))
        self.assertTrue(ISBNValidator(isbn_10[:9]))
        
        isbn_10 = "1-234-56789-X"
        self.assertTrue(ISBNValidator(isbn_10))
        
        isbn_13 = '9784567890120'
        self.assertTrue(ISBNValidator(isbn_13))
        self.assertTrue(ISBNValidator(isbn_13[:12]))
        
        isbn_13 = '978-4-56-789012-0'
        self.assertTrue(ISBNValidator(isbn_13))
        
        with self.assertRaises(ValidationError):
            ISBNValidator('9784567891')
        
    def test_issn_validator(self):
        self.assertTrue(ISSNValidator("12345679"))
        self.assertTrue(ISSNValidator("1234-5679"))
        with self.assertRaises(ValidationError):
            ISSNValidator("12345671")
        
    def test_ean_validator(self):
        self.assertTrue(EANValidator('73513537')) # ean 8
        self.assertTrue(EANValidator("1234567890128")) # ean 13
        with self.assertRaises(ValidationError):
            EANValidator("1234567890121")
        
#TODO: use these:
#ISBN            
#invalid = [
#        ("9999!)()/?1*", InvalidFormat), 
#        ("9"*20, InvalidLength), 
#        ("1234567890128", InvalidComponent), #NOTE: how does this contain an invalid component? prefix != 978 ?
#        ('1234567890', InvalidChecksum), 
#        ('1-234-56789-0', InvalidChecksum), 
#        ('9781234567890', InvalidChecksum), 
#        ('978-1-234-56789-0', InvalidChecksum), 
#    ]
#    
#ISSN
#invalid = [
#        ("123%&/79", InvalidFormat), 
#        ("9"*20, InvalidLength), 
#        ('12345670', InvalidChecksum), 
#        ("1234-5670", InvalidChecksum), 
#    ]
#    
#EAN
#invalid = [
#        ("123%&/()90128", InvalidFormat), 
#        ("9"*20, InvalidLength), 
#        ('73513538', InvalidChecksum), 
#        ("1234567890123", InvalidChecksum), 
#    ]
