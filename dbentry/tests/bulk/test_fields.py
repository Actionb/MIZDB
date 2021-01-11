from django.utils.translation import override as translation_override
from django.core.exceptions import ValidationError

from DBentry.bulk.fields import BulkField, BulkJahrField
from DBentry.tests.base import MyTestCase


class TestBulkField(MyTestCase):

    def test_validate_numerical(self):
        # Assert that simple numerical values are valid.
        field = BulkField()
        msg = "Strictly numerical values should not raise a ValidationError."
        with self.assertNotRaises(ValidationError, msg=msg):
            field.clean('1')

    def test_validate_valid_inputs(self):
        # Assert the validity of various valid inputs.
        field = BulkField()
        valid = ['1-2', '1-2*3', '1/2', '1/2/3']
        for valid_input in valid:
            with self.subTest(valid_input=valid_input):
                with self.assertNotRaises(ValidationError):
                    field.clean(valid_input)

    def test_validate_invalid_inputs(self):
        # Assert the validity of various invalid inputs.
        field = BulkField()
        invalid = ['1--2', '1-2**3', '1--2*3', '1//2', '1-2*3/4']
        for invalid_input in invalid:
            with self.subTest(invalid_input=invalid_input):
                with self.assertRaises(ValidationError):
                    field.clean(invalid_input)

    def test_validation_error_msg_contains_invalid_values(self):
        # Assert that all invalid values are mentioned in the error message.
        field = BulkField()
        invalid = ['1--2', '1//2']
        test_value = '0,{invalid},3'.format(invalid=",".join(invalid))
        with self.assertRaises(ValidationError) as cm:
            field.validate(test_value)
        self.assertEqual(cm.exception.code, 'invalid')
        # cm.exception.message is the unformatted error message
        # the message with the values is found in ValidationError.messages
        self.assertEqual(len(cm.exception.messages), 1)
        error_message = cm.exception.messages[0]
        msg = "Error message should contain all invalid values."
        for invalid_input in invalid:
            with self.subTest(invalid_input=invalid_input):
                self.assertIn(invalid_input, error_message, msg=msg)

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
        for data, expected in test_data:
            with self.subTest(input=data):
                self.assertEqual(field.clean(data), expected)

    def test_to_list(self):
        field = BulkField()
        test_data = [
            # (input, expected list, expected 'item_count')
            (None, [], 0),
            ('1', ['1'], 1),
            ('1,2,3,4', ['1', '2', '3', '4'], 4),
            # range of values
            ('1,2-4', ['1', '2', '3', '4'], 4),
            # range grouping of values
            ('1,2-5*2', ['1', ['2', '3'], ['4', '5']], 3),
            # grouping of values
            ('1,2/3/4', ['1', ['2', '3', '4']], 2),
            # all of it
            ('1,2-3,4-7*2,8/9', ['1', '2', '3', ['4', '5'], ['6', '7'], ['8', '9']], 6),
            # sneak in some bad values
            ('1,1-2&3', ['1'], 1),
            ('1,2&3', ['1'], 1)
        ]
        for data, expected_list, expected_count in test_data:
            with self.subTest(input=data):
                self.assertEqual(
                    field.to_list(data),
                    (expected_list, expected_count)
                )


class TestBulkJahrField(MyTestCase):

    @translation_override(language=None)
    def test_four_digits_year_validator(self):
        field = BulkJahrField()
        with self.assertRaises(ValidationError) as cm:
            field.clean('15')
        self.assertEqual(len(cm.exception.messages), 1)
        self.assertEqual(
            cm.exception.messages[0],
            'Bitte vierstellige Jahresangaben benutzen.'
        )
