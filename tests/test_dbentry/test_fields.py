import datetime
from unittest.mock import patch

from django import forms
from django.contrib.admin.widgets import AdminTextInputWidget
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils.translation import override as translation_override
from stdnum import isbn, issn

from dbentry.fields import (
    EANField, ISBNField, ISBNFormField, ISSNField, ISSNFormField, PartialDate, PartialDateField,
    PartialDateFormField, PartialDateWidget, StdNumField, StdNumFormField, StdNumWidget, YearField
)
from tests.case import DataTestCase, MIZTestCase
from tests.factory import make


class TestYearField(MIZTestCase):

    def test_formfield_adds_validators(self):
        """
        Assert that MaxValue and the MinValue validators are added to the
        formfield's validator list.
        """
        model_field = YearField()
        formfield = model_field.formfield()
        self.assertEqual(len(formfield.validators), 2)
        if isinstance(formfield.validators[0], MinValueValidator):
            min_validator, max_validator = formfield.validators
        else:
            max_validator, min_validator = formfield.validators
        self.assertIsInstance(min_validator, MinValueValidator)
        self.assertEqual(min_validator.limit_value, model_field.MIN_YEAR)
        self.assertIsInstance(max_validator, MaxValueValidator)
        self.assertEqual(max_validator.limit_value, model_field.MAX_YEAR)


####################################################################################################
# Tests for the standard number model and formfields
####################################################################################################


class TestStdNumWidget(MIZTestCase):

    def test_init_sets_format_callback_attr(self):
        """Assert that init sets a 'format_callback' attribute."""

        def callback(v):
            return v

        self.assertEqual(StdNumWidget(format_callback=callback).format_callback, callback)

    def test_format_value(self):
        """
        Assert that the format_callback is used to format the value if the
        callback is set and the value is not empty.
        """

        def callback(v):
            return f"formatted {v!s}"

        self.assertEqual(
            StdNumWidget(format_callback=callback).format_value('test value'),
            'formatted test value'
        )
        self.assertEqual(
            StdNumWidget(format_callback=None).format_value('test_value'),
            'test_value'
        )
        self.assertFalse(StdNumWidget(format_callback=callback).format_value(''))


class TestStdNumFormField(MIZTestCase):
    class StdNumModule:

        @staticmethod
        def compact(v):
            return v.replace('-', '')

    def test_init_sets_stdnum_attr(self):
        """Assert that init sets the 'stdnum' attribute."""
        self.assertEqual(StdNumFormField(stdnum=self.StdNumModule).stdnum, self.StdNumModule)

    def test_to_python(self):
        """Assert that to_python uses the compact function of the assigned stdnum module."""
        self.assertEqual(StdNumFormField(stdnum=self.StdNumModule).to_python('foo-bar'), 'foobar')


class TestISBNFormField(MIZTestCase):

    def test_to_python(self):
        """
        Assert that to_python converts non-empty, valid values in the ISBN-10
        format into values in the ISBN-13 format.
        """
        field = ISBNFormField(stdnum=isbn)
        for value, expected in [('123456789X', '9781234567897'), ('', ''), ('123', '123')]:
            with self.subTest(value=value):
                self.assertEqual(field.to_python(value), expected)


class TestISSNFormField(MIZTestCase):

    def test_to_python(self):
        """Assert that to_python extracts the ISSN from an EAN-13 number."""
        field = ISSNFormField(stdnum=issn)
        for value, expected in [
            # EAN-13            ISSN            ISSN        ISSN
            ('1234567890128', '45678901'), ('12345679', '12345679'), ('', ''), ('123', '123')
        ]:
            with self.subTest(value=value):
                self.assertEqual(field.to_python(value), expected)


class TestStdNumField(MIZTestCase):
    class Field(StdNumField):
        stdnum = isbn
        min_length = 10  # ISBN-10 without dashes/spaces
        max_length = 17  # ISBN-13 with four dashes/spaces

    def setUp(self):
        super().setUp()
        self.field = self.Field()

    def test_formfield_widget(self):
        """Assert that the widget of the formfield is an instance of StdNumWidget."""

        class Widget(StdNumWidget):
            pass

        widgets = [
            None,
            AdminTextInputWidget, AdminTextInputWidget(),
            Widget, Widget()
        ]
        for widget in widgets:
            with self.subTest(widget=str(widget)):
                formfield_widget = self.field.formfield(widget=widget).widget
                self.assertTrue(isinstance(formfield_widget, StdNumWidget))

    def test_get_format_callback(self):
        """
        Assert that the format callback is the 'format' function or, for
        standard numbers without a format function, the 'compact' function.
        """

        # Create some objects that mock a standard number module:
        class WithFormat:

            @staticmethod
            def format(value):
                return value

            @staticmethod
            def compact(value):
                return value

        class WithoutFormat:

            @staticmethod
            def compact(value):
                return value

        self.field.stdnum = WithFormat
        self.assertEqual(self.field.get_format_callback(), WithFormat.format)
        self.field.stdnum = WithoutFormat
        self.assertEqual(self.field.get_format_callback(), WithoutFormat.compact)

    def test_to_python(self):
        """Assert that compact is called on non-empty values."""
        with patch.object(self.field.stdnum, 'compact') as compact_mock:
            self.field.to_python('123456789X')
            compact_mock.assert_called()

    def test_to_python_empty_values(self):
        """Assert that to_python does not modify 'empty' values."""
        for empty_value in self.field.empty_values:
            with self.subTest(value=empty_value):
                self.assertEqual(self.field.to_python(empty_value), empty_value)


class StdNumModel(models.Model):
    isbn = ISBNField()
    issn = ISSNField()
    ean = EANField()


# noinspection PyUnresolvedReferences
class StdNumFieldTestsMixin(object):
    """Test method mixin with tests on the standard number model fields."""
    # Reminder: the field's cleaning methods will re-raise any errors as new
    # ValidationErrors, meaning we cannot test for the exact type of the original
    # validation error (i.e. InvalidLength, InvalidFormat, etc.).

    model = StdNumModel
    model_field = None
    instance_data = None

    def create_model_instance(self, **kwargs):
        if self.instance_data is not None:
            instance_data = self.instance_data.copy()
        else:
            instance_data = {}
        instance_data.update(kwargs)
        return self.model(**instance_data)

    def test_to_python_empty_values(self):
        """Assert that to_python does not modify 'empty' values."""
        for empty_value in self.model_field.empty_values:
            with self.subTest(value=empty_value):
                self.assertEqual(self.model_field.to_python(empty_value), empty_value)

    def test_empty_values_widget(self):
        """Assert that 'empty' values are not modified by the widget."""
        widget = self.model_field.formfield().widget
        for empty_value in self.model_field.empty_values:
            with self.subTest(value=empty_value):
                self.assertEqual(widget.format_value(empty_value), empty_value)

    def test_no_save_with_invalid_data(self):
        """Assert that no objects can be saved with invalid data."""
        for invalid_number in self.invalid:
            model_instance = self.create_model_instance(
                **{self.model_field.name: invalid_number}
            )
            with self.subTest(invalid_number=invalid_number):
                with transaction.atomic():
                    msg = "for invalid input: %s" % invalid_number
                    with self.assertRaises(ValidationError, msg=msg):
                        model_instance.save()

    def test_no_query_with_invalid_data(self):
        """Assert that no query can be attempted with invalid data (much like DateFields)."""
        for invalid_number in self.invalid:
            with self.subTest(invalid_number=invalid_number):
                msg = "for invalid input: %s" % invalid_number
                with self.assertRaises(ValidationError, msg=msg):
                    self.model.objects.filter(**{self.model_field.name: invalid_number})

    def test_query_with_any_format(self):
        """
        Assert queries are possible regardless of the format (pretty/compact)
        of the valid input.
        """
        for valid_number in self.valid:
            with self.subTest(valid_number=valid_number):
                msg = "for valid input: %s" % valid_number
                with self.assertNotRaises(ValidationError, msg=msg):
                    self.model.objects.filter(**{self.model_field.name: valid_number})

    def test_saves_as_compact(self):
        """Assert that all std number are saved to the db in their compact format."""
        for valid_number in self.valid:
            model_instance = self.create_model_instance(**{self.model_field.name: valid_number})
            model_instance.save()
            model_instance.refresh_from_db()
            with self.subTest(valid_number=valid_number):
                self.assertNotIn('-', getattr(model_instance, self.model_field.name))

    def test_modelform_uses_pretty_format(self):
        """Assert that the value displayed on a modelform is the formatted version."""
        # Note that this test will always succeed for EAN fields, since the ean
        # module does not provide a format function.
        model_form_class = forms.modelform_factory(self.model, fields=[self.model_field.name])
        for valid_number in self.valid:
            formatted_number = self.model_field.get_format_callback()(valid_number)
            model_instance = self.create_model_instance(**{self.model_field.name: valid_number})
            model_instance.save()
            model_instance.refresh_from_db()
            model_form = model_form_class(instance=model_instance)
            with self.subTest(valid_number=valid_number):
                value_displayed = 'value="%s"' % formatted_number
                # str(bound_field) will render the widget, including the value:
                self.assertIn(value_displayed, str(model_form[self.model_field.name]))

    def test_min_max_parameter_passed_to_formfield(self):
        """
        Assert that the correct min and max length parameters are passed to
        the field's formfield.
        """
        formfield = self.model_field.formfield()
        self.assertEqual(formfield.min_length, self.model_field.min_length)
        self.assertEqual(formfield.max_length, self.model_field.max_length)

    def test_widget_class_passed_to_formfield(self):
        """
        Assert that the widget class needed to render the value in the
        correct format is passed to the formfield.
        """
        formfield = self.model_field.formfield()
        self.assertIsInstance(formfield.widget, StdNumWidget)

    def test_query_formatted_number(self):
        """Assert that formatted numbers can be used in queries."""
        for valid_number in self.valid:
            # Save as compact, query with pretty format:
            compact = self.model_field.stdnum.compact(valid_number)
            pretty = self.model_field.get_format_callback()(valid_number)

            model_instance = self.create_model_instance(**{self.model_field.name: compact})
            model_instance.save()
            qs = self.model.objects.filter(**{self.model_field.name: pretty})
            with self.subTest(valid_number=valid_number):
                msg = (
                    "Query returned unexpected number of records."
                    "Querying for {filter_kwargs}\nIn database: {values}\n".format(
                        filter_kwargs={self.model_field.name: pretty},
                        values=list(
                            self.model.objects.values_list(self.model_field.name, flat=True)
                        )
                    )
                )
                self.assertEqual(qs.count(), 1, msg=msg)
                self.assertEqual(qs.get(), model_instance, msg="Query returned unexpected record.")
            model_instance.delete()

    def test_modelform_handles_formats_as_the_same_data(self):
        """
        Assert that a model form is not flagged as 'changed' because of
        different formatting of initial and bound value of the same number.
        """
        model_form_class = forms.modelform_factory(self.model, fields=[self.model_field.name])
        for valid_number in self.valid:
            # Model form initial data for the standard number will use the
            # compact formatting (from model instance), while form data for
            # that number will use the 'pretty' formatting.
            with self.subTest(valid_number=valid_number):
                pretty = self.model_field.get_format_callback()(valid_number)
                model_instance = self.create_model_instance(**{self.model_field.name: valid_number})
                # This will save the compact form of the number:
                model_instance.save()
                model_instance.refresh_from_db()
                model_form = model_form_class(
                    data={self.model_field.name: pretty},
                    instance=model_instance
                )
                msg = (
                    "ModelForm is flagged as changed for using different formats of the same "
                    "standard number.\nform initial: {},\nform data: {}\n".format(
                        model_form[self.model_field.name].initial,
                        model_form[self.model_field.name].value()
                    ))
                self.assertFalse(model_form.has_changed(), msg=msg)


class TestISBNField(StdNumFieldTestsMixin, MIZTestCase):
    # noinspection PyUnresolvedReferences
    model_field = StdNumModel._meta.get_field('isbn')

    valid = [
        '123456789X',  # ISBN-10 w/o hyphens
        '1-234-56789-X',  # ISBN-10 w/ hyphens
        '9780471117094',  # ISBN-13 w/o hyphens
        '978-0-471-11709-4',  # ISBN-13 w/ hyphens
        '9791234567896',  # ISBN-13 w/o hyphens with 979 bookmark
        '979-1-234-56789-6',  # ISBN-13 w/ hyphens with 979 bookmark
    ]
    invalid = [
        "9999!)()/?1*",  # InvalidFormat
        "9" * 20,  # InvalidLength
        "1234567890128",  # InvalidComponent prefix != 978
        '1234567890',  # InvalidChecksum
        '1-234-56789-0',  # InvalidChecksum
        '9781234567890',  # InvalidChecksum
        '978-1-234-56789-0',  # InvalidChecksum
    ]

    def test_to_python(self):
        """Assert that to_python converts non-empty values to ISBN-13."""
        self.assertEqual(isbn.isbn_type(self.model_field.to_python('123456789X')), 'ISBN13')

    def test_get_format_callback_empty_value(self):
        """Assert that the callback does not modify empty values."""
        for value in self.model_field.empty_values:
            with self.subTest(empty_value=value):
                self.assertFalse(self.model_field.get_format_callback()(value))

    def test_modelform_handles_isbn10_as_isbn13(self):
        """
        Assert that the form treats a value of ISBN13 passed in as initial as
        the same as an equal value of ISBN10 passed in as data.
        """
        model_form_class = forms.modelform_factory(self.model, fields=[self.model_field.name])
        isbn10_seen = set()
        for valid_number in self.valid:
            valid_number = isbn.compact(valid_number)
            # Use the ISBN13 for initial and the ISBN10 as data
            if valid_number.startswith('979'):
                # cannot convert from isbn13 with 979 bookmark to isbn10
                continue
            if isbn.isbn_type(valid_number) == 'ISBN13':
                isbn10 = isbn.to_isbn10(valid_number)
                isbn13 = valid_number
            else:
                isbn10 = valid_number
                isbn13 = isbn.to_isbn13(valid_number)
            if isbn10 in isbn10_seen:
                continue
            isbn10_seen.add(isbn10)

            model_instance = self.create_model_instance(**{self.model_field.name: isbn13})
            model_instance.save()
            model_instance.refresh_from_db()
            model_form = model_form_class(
                data={self.model_field.name: isbn10},
                instance=model_instance
            )
            with self.subTest(valid_number=valid_number):
                msg = (
                    "ModelForm is flagged as changed for using different ISBN types of "
                    "the same stdnum.\nform initial: {},\nform data: {}\n".format(
                        model_form[self.model_field.name].initial,
                        model_form[self.model_field.name].value()
                    ))
                self.assertFalse(model_form.has_changed(), msg=msg)

    def test_converts_isbn10_to_isbn13_on_save(self):
        """Assert that numbers are converted to ISBN-13 on save."""
        for valid_number in self.valid:
            model_instance = self.create_model_instance(**{self.model_field.name: valid_number})
            model_instance.save()
            model_instance.refresh_from_db()
            with self.subTest(valid_number=valid_number):
                self.assertEqual(
                    getattr(model_instance, self.model_field.name),
                    isbn.compact(isbn.to_isbn13(valid_number))
                )

    # noinspection PyUnresolvedReferences
    def test_query_for_isbn10_finds_isbn13(self):
        """Assert that ISBN-10c can be used to query for objects with a ISBN-13."""
        isbn_10 = '123456789X'
        obj = self.model.objects.create(isbn=isbn.to_isbn13(isbn_10))
        self.assertIn(obj, self.model.objects.filter(isbn=isbn_10))


class TestISSNField(StdNumFieldTestsMixin, MIZTestCase):
    # noinspection PyUnresolvedReferences
    model_field = StdNumModel._meta.get_field('issn')

    valid = ["12345679", "1234-5679"]
    invalid = [
        "123%&/79",  # InvalidFormat
        "9" * 20,  # InvalidLength
        '12345670',  # InvalidChecksum
        "1234-5670",  # InvalidChecksum
    ]

    def test_min_max_parameter_passed_to_formfield(self):
        """
        Assert that the correct min and max length parameters are passed to the
         field's formfield.
        """
        formfield = self.model_field.formfield()
        self.assertEqual(formfield.min_length, self.model_field.min_length)
        self.assertEqual(formfield.max_length, 17)  # allow for EAN-13


class TestEANField(StdNumFieldTestsMixin, MIZTestCase):
    # noinspection PyUnresolvedReferences
    model_field = StdNumModel._meta.get_field('ean')

    valid = ['73513537', "1234567890128"]
    invalid = [
        "123%&/()90128",  # InvalidFormat
        "9" * 20,  # InvalidLength
        '73513538',  # InvalidChecksum
        "1234567890123",  # InvalidChecksum
    ]


####################################################################################################
# Tests for the partial fields and widgets
####################################################################################################


class TestPartialDate(MIZTestCase):

    def assertAttrsSet(self, partial_date, year, month, day, date_format, msg=None):
        """
        Assert that the attributes 'year', 'month' and 'day' were set
        correctly during the creation of the PartialDate.
        """
        attrs = ('__year', '__month', '__day', 'date_format')
        expected = dict(zip(attrs, (year, month, day, date_format)))
        for attr in attrs:
            with self.subTest(attr=attr):
                self.assertEqual(getattr(partial_date, attr), expected[attr], msg=msg)

    def test_new_with_int_kwargs(self):
        # Full date
        self.assertAttrsSet(PartialDate(year=2019, month=5, day=20), 2019, 5, 20, '%Y-%m-%d')
        # year and month
        self.assertAttrsSet(PartialDate(year=2019, month=5), 2019, 5, None, '%Y-%m')
        self.assertAttrsSet(PartialDate(year=2019, month=5, day=0), 2019, 5, None, '%Y-%m')
        # year and day
        self.assertAttrsSet(PartialDate(year=2019, day=20), 2019, None, 20, '%Y-%d')
        self.assertAttrsSet(PartialDate(year=2019, month=0, day=20), 2019, None, 20, '%Y-%d')
        # month and day
        self.assertAttrsSet(PartialDate(month=5, day=20), None, 5, 20, '%m-%d')
        self.assertAttrsSet(PartialDate(year=0, month=5, day=20), None, 5, 20, '%m-%d')
        # year only
        self.assertAttrsSet(PartialDate(year=2019), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year=2019, month=0), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year=2019, month=0, day=0), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(PartialDate(month=5), None, 5, None, '%m')
        self.assertAttrsSet(PartialDate(year=0, month=5), None, 5, None, '%m')
        self.assertAttrsSet(PartialDate(year=0, month=5, day=0), None, 5, None, '%m')
        # day only
        self.assertAttrsSet(PartialDate(day=20), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(month=0, day=20), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(year=0, month=0, day=20), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(PartialDate(day=0), None, None, None, '')
        self.assertAttrsSet(PartialDate(month=0, day=0), None, None, None, '')
        self.assertAttrsSet(PartialDate(year=0, month=0, day=0), None, None, None, '')

    # noinspection PyTypeChecker
    def test_new_with_string_kwargs(self):
        # Full date
        self.assertAttrsSet(PartialDate(year='2019', month='5', day='20'), 2019, 5, 20, '%Y-%m-%d')
        # year and month
        self.assertAttrsSet(PartialDate(year='2019', month='05'), 2019, 5, None, '%Y-%m')
        self.assertAttrsSet(PartialDate(year='2019', month='05', day='0'), 2019, 5, None, '%Y-%m')
        # year and day
        self.assertAttrsSet(PartialDate(year='2019', day='20'), 2019, None, 20, '%Y-%d')
        self.assertAttrsSet(PartialDate(year='2019', month='0', day='20'), 2019, None, 20, '%Y-%d')
        # month and day
        self.assertAttrsSet(PartialDate(month='5', day='20'), None, 5, 20, '%m-%d')
        self.assertAttrsSet(PartialDate(year='0000', month='5', day='20'), None, 5, 20, '%m-%d')
        # year only
        self.assertAttrsSet(PartialDate(year='2019'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year='2019', month='00'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year='2019', month='00', day='0'), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(PartialDate(month='5'), None, 5, None, '%m')
        self.assertAttrsSet(PartialDate(year='0', month='05'), None, 5, None, '%m')
        self.assertAttrsSet(PartialDate(year='0000', month='05', day='00'), None, 5, None, '%m')
        # day only
        self.assertAttrsSet(PartialDate(day='20'), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(month='00', day='20'), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(year='0000', month='00', day='20'), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(PartialDate(day='0'), None, None, None, '')
        self.assertAttrsSet(PartialDate(month='0', day='0'), None, None, None, '')
        self.assertAttrsSet(PartialDate(year='0', month='0', day='0'), None, None, None, '')

    def test_from_string(self):
        # Full date
        self.assertAttrsSet(PartialDate.from_string('2019-05-20'), 2019, 5, 20, '%Y-%m-%d')
        # year and month
        self.assertAttrsSet(PartialDate.from_string('2019-05'), 2019, 5, None, '%Y-%m')
        self.assertAttrsSet(PartialDate.from_string('2019-05-00'), 2019, 5, None, '%Y-%m')
        # year and day
        self.assertAttrsSet(PartialDate.from_string('2019-00-20'), 2019, None, 20, '%Y-%d')
        # month and day
        self.assertAttrsSet(PartialDate.from_string('05-20'), None, 5, 20, '%m-%d')
        self.assertAttrsSet(PartialDate.from_string('0000-05-20'), None, 5, 20, '%m-%d')
        # year only
        self.assertAttrsSet(PartialDate.from_string('2019'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate.from_string('2019-00'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate.from_string('2019-00-00'), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(PartialDate.from_string('0000-05'), None, 5, None, '%m')
        self.assertAttrsSet(PartialDate.from_string('0000-05-00'), None, 5, None, '%m')
        # day only
        self.assertAttrsSet(PartialDate.from_string('0000-00-20'), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate.from_string('00-20'), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(PartialDate.from_string(''), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('00'), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('0000-00'), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('0000-00-00'), None, None, None, '')

    def test_from_date(self):
        self.assertAttrsSet(
            PartialDate.from_date(datetime.date(2019, 5, 20)), 2019, 5, 20, '%Y-%m-%d'
        )
        self.assertAttrsSet(
            PartialDate.from_date(datetime.datetime(2019, 5, 20)), 2019, 5, 20, '%Y-%m-%d'
        )

    def test_new_validates_date(self):
        """Assert that PartialDate does not accept invalid dates (31st of February, etc.)."""
        invalid_dates = ('02-31', '04-31')
        for date in invalid_dates:
            with self.subTest():
                with self.assertRaises(ValueError, msg="Date used: %s" % date):
                    PartialDate.from_string(date)

        for date_args in (d.split('-') for d in invalid_dates):
            with self.subTest():
                with self.assertRaises(ValueError, msg="Date args used: %s" % date_args):
                    PartialDate(*date_args)

    def test_from_string_invalid_format(self):
        """Assert that an exception is raised if the string has an invalid format."""
        invalid_dates = ('Beep-05-12', '2019-as-12', '2019-05-as')
        for date in invalid_dates:
            with self.subTest():
                msg = 'from_string should raise a ValueError if it cannot match its regex.'
                with self.assertRaises(ValueError, msg=msg):
                    PartialDate.from_string(date)

        for date_args in (d.split('-') for d in invalid_dates):
            with self.subTest():
                msg = "casting a string literal to int should raise a ValueError"
                with self.assertRaises(ValueError, msg=msg):
                    PartialDate(*date_args)

    def test_empty_date(self):
        """Assert that an empty PartialDate can be created."""
        with self.assertNotRaises(Exception):
            pd = PartialDate()
        self.assertAttrsSet(pd, year=None, month=None, day=None, date_format='')

    def test_db_value(self):
        """Assert that db_value returns a date string in the date ISO format."""
        test_data = [
            '2019-05-20', '2019-05-00', '2019-00-20', '2019-00-00',
            '0000-05-20', '0000-05-00', '0000-00-20', '0000-00-00',
        ]
        for data in test_data:
            with self.subTest():
                pd = PartialDate.from_string(data)
                self.assertEqual(pd.db_value, data)

    @translation_override(language=None)
    def test_str(self):
        test_data = [
            ('2019-05-20', '2019-05-20'), ('2019-05-00', '2019-05'),
            ('2019-00-20', '2019'), ('2019-00-00', '2019'),
            ('0000-05-20', '20. May'), ('0000-05-00', 'May'),
            ('0000-00-20', '20.'), ('0000-00-00', ''),
        ]
        for data, expected in test_data:
            with self.subTest(data=data):
                pd = PartialDate.from_string(data)
                self.assertEqual(str(pd), expected)

        with_date = PartialDate.from_date(datetime.date(2019, 5, 20))
        self.assertEqual(str(with_date), '2019-05-20')

    def test_iter(self):
        """Assert that iter returns the year, month and day, in that order."""
        pd = PartialDate(2022, 5, 21)
        iterator = pd.__iter__()
        self.assertEqual(next(iterator), 2022)
        self.assertEqual(next(iterator), 5)
        self.assertEqual(next(iterator), 21)
        with self.assertRaises(StopIteration):
            next(iterator)

    def test_len(self):
        """Assert that len returns the length of the date string in ISO format."""
        pd = PartialDate(2022, 5, 21)
        self.assertEqual(pd.__len__(), len("2022-05-21"))

    def test_bool(self):
        """Assert that bool returns False for an empty PartialDate, and True otherwise."""
        self.assertFalse(PartialDate().__bool__())
        self.assertTrue(PartialDate(2022).__bool__())

    def test_equality_partial_date_to_partial_date(self):
        """Assert that two equal PartialDate instances equate."""
        self.assertTrue(PartialDate().__eq__(PartialDate()))
        date = '2019-05-20'
        self.assertTrue(PartialDate.from_string(date).__eq__(PartialDate.from_string(date)))
        self.assertTrue(PartialDate(*date.split('-')).__eq__(PartialDate(*date.split('-'))))
        msg = (
            "A partial date created explicitly with the 'default' values should "
            "not equate to an empty partial date."
        )
        self.assertFalse(PartialDate(4, 1, 1).__eq__(PartialDate()), msg=msg)

    def test_equality_string_to_partial_date(self):
        """Assert that a PartialDate and a string of the same value equate."""
        self.assertTrue(PartialDate().__eq__(''))
        date = '2019-05-20'
        self.assertTrue(PartialDate.from_string(date).__eq__(date))
        self.assertFalse(
            PartialDate.from_string(date).__eq__('Nota-valid-date'),
            msg='Invalid string should equate to false.'
        )
        msg = (
            "A partial date created explicitly with the 'default' values should "
            "not equate to an empty string."
        )
        self.assertFalse(PartialDate(4, 1, 1).__eq__(''), msg=msg)

    def test_equality_partial_date_to_date(self):
        """Assert that a partial date and a datetime.date instance equate."""
        self.assertTrue(PartialDate(4, 1, 1).__eq__(datetime.date(4, 1, 1)))
        msg = "An empty partial date should not equate to any datetime.date."
        self.assertFalse(PartialDate().__eq__(datetime.date(4, 1, 1)), msg=msg)

    def test_gt(self):
        self.assertTrue(PartialDate(2022).__gt__(PartialDate(2021)))
        self.assertFalse(PartialDate(2021).__gt__(PartialDate(2022)))
        self.assertTrue(PartialDate(2022).__gt__('2021'))
        self.assertFalse(PartialDate(2021).__gt__('2022'))


class TestPartialDateWidget(MIZTestCase):

    def test_init_widgets(self):
        """Assert that init sets the 'widgets' argument if no widgets were passed in."""
        widget = PartialDateWidget()
        self.assertEqual(len(widget.widgets), 3)
        expected_attrs = [
            ({'placeholder': 'Jahr', 'style': 'width:70px; margin-right:10px;'}),
            ({'placeholder': 'Monat', 'style': 'width:70px; margin-right:10px;'}),
            ({'placeholder': 'Tag', 'style': 'width:70px;'}),
        ]
        for i, widget in enumerate(widget.widgets):
            self.assertIsInstance(widget, forms.widgets.NumberInput)
            self.assertEqual(widget.attrs, expected_attrs[i])

        widget = PartialDateWidget(widgets=[forms.widgets.DateInput()])
        self.assertEqual(len(widget.widgets), 1)
        self.assertIsInstance(widget.widgets[0], forms.widgets.DateInput)

    def test_decompress(self):
        pd = PartialDate(year=2019, month=5, day=20)
        self.assertEqual(PartialDateWidget().decompress(pd), [2019, 5, 20])

        self.assertEqual(PartialDateWidget().decompress(None), [None] * 3)


class TestPartialDateFormField(MIZTestCase):

    def test_init_fields(self):
        """Assert that init sets the 'fields' argument if no fields were passed in."""
        formfield = PartialDateFormField()
        self.assertEqual(len(formfield.fields), 3)
        for field in PartialDateFormField().fields:
            self.assertIsInstance(field, forms.IntegerField)
            self.assertFalse(field.required)

        formfield = PartialDateFormField(fields=[forms.CharField()])
        self.assertEqual(len(formfield.fields), 1)
        self.assertIsInstance(formfield.fields[0], forms.CharField)

    @patch("django.forms.fields.MultiValueField.__init__")
    def test_init_removes_max_length_kwarg(self, super_init_mock):
        """Assert that init removes any 'max_length' kwarg (added by CharField.formfield)."""
        PartialDateFormField(max_length=1)
        super_init_mock.assert_called()
        _args, kwargs = super_init_mock.call_args
        self.assertNotIn('max_length', kwargs)

        # Test with calling formfield() on the model field:
        super_init_mock.reset_mock()
        PartialDateField().formfield()
        super_init_mock.assert_called()
        _args, kwargs = super_init_mock.call_args
        self.assertNotIn('max_length', kwargs)

    @patch("django.forms.fields.MultiValueField.__init__")
    def test_init_sets_required_all_fields_to_false(self, super_init_mock):
        """Assert that the required_all_fields is set to False in the super call."""
        for kwargs in ({}, {'require_all_fields': True}):
            with self.subTest(kwargs=kwargs):
                PartialDateFormField(**kwargs)
                super_init_mock.assert_called()
                _args, kwargs = super_init_mock.call_args
                self.assertFalse(kwargs['require_all_fields'])
                super_init_mock.reset_mock()

    def test_widgets(self):
        """Assert that the formfield's widget is an instance of PartialDateWidget."""

        class Widget(PartialDateWidget):
            pass

        self.assertIsInstance(PartialDateFormField().widget, PartialDateWidget)
        self.assertIsInstance(PartialDateFormField(widget=Widget).widget, PartialDateWidget)
        self.assertIsInstance(PartialDateFormField(widget=Widget()).widget, PartialDateWidget)
        self.assertIsInstance(
            PartialDateFormField(widget=forms.widgets.DateInput).widget,
            PartialDateWidget
        )
        self.assertIsInstance(
            PartialDateFormField(widget=forms.widgets.DateInput()).widget,
            PartialDateWidget
        )

    def test_compress(self):
        field = PartialDateFormField()
        self.assertEqual(field.compress([2019, 5, 20]), PartialDate(year=2019, month=5, day=20))

    def test_compress_raises_error_on_invalid_date(self):
        field = PartialDateFormField()
        invalid_dates = ('Beep-05-12', '2019-as-12', '2019-05-as', '2022-02-31')
        for invalid_date in invalid_dates:
            invalid_date = invalid_date.split('-')
            with self.subTest():
                with self.assertRaises(ValidationError, msg=invalid_date) as cm:
                    field.compress(invalid_date)
                self.assertEqual(cm.exception.code, 'invalid')

    def test_clean(self):
        """Assert that clean accepts valid partial dates and returns a PartialDate."""
        field = PartialDateFormField(required=False)
        for data in ([], [2019], [2019, 5], [2019, 5, 20], [None, 5, 20]):
            with self.assertNotRaises(ValidationError):
                cleaned = field.clean(data)
            self.assertEqual(cleaned, PartialDate(*data))


class TestPartialDateField(MIZTestCase):

    def test_init_sets_help_text(self):
        """Assert that init sets the field's help text."""
        self.assertEqual(PartialDateField().help_text, PartialDateField.help_text)
        self.assertEqual(PartialDateField(help_text='Test').help_text, 'Test')

    def test_init_sets_max_length(self):
        """Assert that init sets max_length to 10."""
        self.assertEqual(PartialDateField().max_length, 10)
        self.assertEqual(PartialDateField(max_length=1).max_length, 10)

    def test_to_python_empty_value(self):
        """Assert that to_python returns an empty partial date if the value is 'empty'."""
        for value in (None, ''):
            with self.subTest(value=value):
                self.assertEqual(PartialDateField().to_python(value), PartialDate())

    def test_to_python_takes_string(self):
        """Assert that to_python converts a string value to PartialDate."""
        value = PartialDateField().to_python('2019')
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, PartialDate(2019))

    def test_to_python_invalid_strings(self):
        """Assert that to_python raises a ValidationError on invalid string values."""
        invalid_dates = ('Beep-05-12', '2019-as-12', '2019-05-as')
        for invalid_date in invalid_dates:
            with self.subTest():
                with self.assertRaises(ValidationError, msg=invalid_date) as cm:
                    PartialDateField().to_python(invalid_date)
            self.assertEqual(cm.exception.code, 'invalid_date')

    def test_to_python_takes_partial_date(self):
        pd = PartialDate(year=2019)
        value = PartialDateField().to_python(pd)
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, pd)

    def test_to_python_takes_date_instance(self):
        """Assert that to_python converts a date value to a PartialDate."""
        value = PartialDateField().to_python(datetime.date(2019, 5, 20))
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, PartialDate(2019, 5, 20))

    def test_from_db_value(self):
        """Assert that a value, as fetched from the db, becomes a PartialDate."""
        self.assertIsInstance(PartialDateField().from_db_value('2019-05-20'), PartialDate)
        self.assertIsNone(PartialDateField().from_db_value(None))

    def test_get_prep_value(self):
        """Assert that a PartialDate value is prepared as a string."""
        test_data = [
            '2019-05-20', '2019-05-00', '2019-00-20', '2019-00-00',
            '0000-05-20', '0000-05-00', '0000-00-20', '0000-00-00',
        ]
        for data in test_data:
            with self.subTest():
                pd = PartialDate.from_string(data)
                prepped_value = PartialDateField().get_prep_value(value=pd)
                self.assertEqual(prepped_value, data)

    def test_formfield(self):
        """Assert that PartialDateField's formfield is a PartialDateFormField instance."""
        self.assertIsInstance(PartialDateField().formfield(), PartialDateFormField)


class PartialDateModel(models.Model):
    datum = PartialDateField()


class TestPartialDateFieldQueries(DataTestCase):
    """Test various queries using PartialDateField."""

    model = PartialDateModel

    def setUp(self):
        super().setUp()
        # noinspection PyUnresolvedReferences
        self.queryset = self.model.objects.all()

    def test_create_partial_date(self):
        """Assert that a model instance can be created with a PartialDate."""
        obj = self.queryset.create(datum=PartialDate(2019, 5, 20))
        self.assertEqual(self.queryset.get(pk=obj.pk).datum, PartialDate(2019, 5, 20))

    def test_create_string(self):
        """Assert that a model instance can be created with a string."""
        obj = self.queryset.create(datum='2019-05-20')
        self.assertEqual(self.queryset.get(pk=obj.pk).datum, PartialDate(2019, 5, 20))

    def test_filter_with_partial_date(self):
        """Assert that partial date instances can be used to filter with."""
        obj1 = make(self.model, datum='2019-05-20')
        obj2 = make(self.model, datum='2019-05-22')
        qs = self.queryset.filter(datum=PartialDate(2019, 5, 20))
        self.assertIn(obj1, qs)
        self.assertNotIn(obj2, qs)

    def test_lookup_range(self):
        """Assert that the range lookup works with partial dates."""
        obj1 = make(self.model, datum='2019-05-20')
        obj2 = make(self.model, datum='2019-05-22')
        qs = self.queryset.filter(datum__range=('2019-05-19', '2019-05-21'))
        self.assertIn(obj1, qs)
        self.assertNotIn(obj2, qs)
