from django.core.exceptions import ValidationError
from django.utils.translation import override as translation_override

from dbentry.tools.bulk.fields import BulkField, BulkJahrField
from tests.case import MIZTestCase


class TestBulkField(MIZTestCase):

    def test_validate_valid_inputs(self):
        """Assert that valid inputs do not raise ValidationErrors."""
        field = BulkField()
        valid = ['1', '1-2', '1-2*3', '1/2', '1/2/3']
        for valid_input in valid:
            with self.subTest(valid_input=valid_input):
                with self.assertNotRaises(ValidationError):
                    field.clean(valid_input)

    def test_validate_invalid_inputs(self):
        """Assert that invalid inputs raise ValidationErrors."""
        field = BulkField()
        invalid = ['1--2', '1-2**3', '1--2*3', '1//2', '1-2*3/4']
        for invalid_input in invalid:
            with self.subTest(invalid_input=invalid_input):
                with self.assertRaises(ValidationError) as cm:
                    field.clean(invalid_input)
                self.assertEqual(cm.exception.code, 'invalid')
                self.assertEqual(len(cm.exception.messages), 1)
                error_message = cm.exception.messages[0]
                self.assertIn(invalid_input, error_message)

    def test_clean(self):
        """
        Assert that clean():
            - strips values
            - removes empty values
            - returns a string of comma separated values with no whitespaces
        """
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
                self.assertEqual(field.to_list(data), (expected_list, expected_count))


class TestBulkJahrField(MIZTestCase):

    @translation_override(language=None)
    def test_four_digits_year_validator(self):
        """Assert that only 4 digit year values are accepted."""
        field = BulkJahrField()
        with self.assertRaises(ValidationError) as cm:
            field.clean('15')
        self.assertEqual(len(cm.exception.messages), 1)
        self.assertEqual(cm.exception.messages[0], 'Bitte vierstellige Jahresangaben benutzen.')
