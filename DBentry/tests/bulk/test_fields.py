from ..base import MyTestCase

from django.utils.translation import override as translation_override
from django.core.exceptions import ValidationError

from DBentry.bulk.fields import BulkField, BulkJahrField

class TestBulkField(MyTestCase):

    def test_validate_numerical(self):
        # Assert that simple numerical values are valid.
        field = BulkField()
        msg = "Strictly numerical values should not raise a ValidationError."
        with self.assertNotRaises(ValidationError, msg=msg):
            field.validate('1')

    def test_validate_valid_inputs(self):
        # Assert the validity of various valid inputs.
        field = BulkField()
        valid = ['1-2', '1-2*3', '1/2', '1/2/3']
        for valid_input in valid:
            with self.subTest(valid_input=valid_input):
                with self.assertNotRaises(ValidationError):
                    field.validate(valid_input)

    def test_validate_invalid_inputs(self):
        # Assert the validity of various invalid inputs.
        field = BulkField()
        invalid = ['1--2', '1-2**3', '1--2*3', '1//2', '1-2*3/4']
        for invalid_input in invalid:
            with self.subTest(invalid_input=invalid_input):
                with self.assertRaises(ValidationError):
                    field.validate(invalid_input)

    def test_validation_error_msg_contains_invalid_values(self):
        # Assert that all invalid values are mentioned in the error message.
        field = BulkField()
        invalid = ['1--2', '1//2']
        test_value = '0,{invalid},3'.format(invalid=",".join(invalid))
        with self.assertRaises(ValidationError) as cm:
            field.validate(test_value)
        self.assertEqual(cm.exception.code, 'invalid_format')
        # cm.exception.message is the unformatted error message
        # the message with the values is found in ValidationError.messages
        self.assertEqual(len(cm.exception.messages), 1)
        error_message = cm.exception.messages[0]
        msg = "Error message should contain all invalid values."
        for invalid_input in invalid:
            with self.subTest(invalid_input=invalid_input):
                self.assertIn(invalid_input,error_message, msg=msg)

    def test_clean(self):
        # Assert that clean():
        #   - strips values
        #   - removes empty values
        #   - returns a string of comma separated values with no whitespaces
        field = BulkField()
        test_data = [
            ('', ''),
            (' ', ''),
            (',', ''),
            (' 1 , ', '1'),
            ('1, 2, 3, 4', '1,2,3,4'),
            (' , 1 ,2 ,3, 4', '1,2,3,4')
        ]
        for input, expected in test_data:
            with self.subTest(input=input):
                self.assertEqual(field.clean(input), expected)

    def test_to_list(self):
        field = BulkField()
        test_data = [
            # (input, expected list, expected 'item_count')
            (None, [], 0),
            ('1', ['1'], 1),
            ('1,2,3,4', ['1', '2', '3', '4'], 4),
            # range of values
            ('1,2-4', ['1', ['2'], ['3'], ['4']], 4),
            # range grouping of values
            ('1,2-5*2', ['1', ['2', '3'], ['4', '5']], 3),
            # grouping of values
            ('1,2/3/4', ['1', ['2', '3', '4']], 2),
            # all of it
            ('1,2-3,4-7*2,8/9', ['1', ['2'], ['3'], ['4', '5'], ['6', '7'], ['8', '9']], 6),
            # sneak in some bad values
            ('1,1-2&3', ['1'], 1),
            ('1,2&3', ['1'], 1)
        ]
        for input, expected_list, expected_count in test_data:
            with self.subTest(input=input):
                self.assertEqual(field.to_list(input), (expected_list, expected_count))

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
