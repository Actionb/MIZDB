import datetime
from stdnum import isbn
from unittest.mock import patch

from django import forms
from django.contrib.admin.widgets import AdminTextInputWidget
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction
from django.test import tag

from dbentry import models as _models
from dbentry.factory import make
from dbentry.fields import (
    StdNumWidget, YearField,
    PartialDate, PartialDateField, PartialDateWidget, PartialDateFormField
)
from dbentry.tests.base import MyTestCase, DataTestCase


class TestYearField(MyTestCase):

    def test_formfield(self):
        # Assert that formfield() passes the MaxValue and the MinValue
        # validators on to the formfield.
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


# Reminder: the field's cleaning methods will reraise any ValidationError subtypes as a new
# ValidationError, meaning we cannot test for the correct subtype here.
class StdNumFieldTestsMixin(object):

    # the data necessary to create a partial prototype of a model instance:
    prototype_data = None

    def create_model_instance(self, **kwargs):
        if self.prototype_data is not None:
            instance_data = self.prototype_data.copy()
        else:
            instance_data = {}
        instance_data.update(kwargs)
        return self.model(**instance_data)

    def test_empty_values_modelfield(self):
        # Assert that 'empty' values are left untouched by the modelfield.
        for empty_value in self.model_field.empty_values:
            with self.subTest(value=empty_value):
                self.assertEqual(self.model_field.to_python(empty_value), empty_value)

    def test_empty_values_widget(self):
        # Assert that 'empty' values are left untouched by the widget.
        widget = self.model_field.formfield().widget
        for empty_value in self.model_field.empty_values:
            with self.subTest(value=empty_value):
                self.assertEqual(widget.format_value(empty_value), empty_value)

    def test_no_save_with_invalid_data(self):
        # Assert that no records can be saved with invalid data.
        for invalid_number in self.invalid:
            model_instance = self.create_model_instance(
                **{self.model_field.name: invalid_number})
            with self.subTest(invalid_number=invalid_number):
                with transaction.atomic():
                    msg = "for invalid input: %s" % invalid_number
                    with self.assertRaises(ValidationError, msg=msg):
                        model_instance.save()

    def test_no_query_with_invalid_data(self):
        # Assert that no query can be attempted with invalid data (much like DateFields).
        for invalid_number in self.invalid:
            with self.subTest(invalid_number=invalid_number):
                msg = "for invalid input: %s" % invalid_number
                with self.assertRaises(ValidationError, msg=msg):
                    self.model.objects.filter(**{self.model_field.name: invalid_number})

    def test_query_with_any_format(self):
        # Assert queries are possible regardless of the format (pretty/compact)
        # of the valid input.
        for valid_number in self.valid:
            with self.subTest(valid_number=valid_number):
                msg = "for valid input: %s" % valid_number
                with self.assertNotRaises(ValidationError, msg=msg):
                    self.model.objects.filter(**{self.model_field.name: valid_number})

    def test_query_with_any_format_returns_results(self):
        # Assert that the correct results are returned by querying for a std number no matter
        # the format of the input.
        # For this test to make any real sense, it is required that
        # test_saves_as_compact passes.
        valid_seen = set()
        for valid_number in self.valid:
            # Save as compact, query with pretty format
            compact = self.model_field.stdnum.compact(valid_number)
            pretty = self.model_field.get_format_callback()(valid_number)
            if compact in valid_seen:
                continue
            valid_seen.add(compact)
            if compact == pretty:
                continue

            model_instance = self.create_model_instance(**{self.model_field.name: compact})
            model_instance.save()
            qs = self.model.objects.filter(**{self.model_field.name: pretty})
            with self.subTest(valid_number=valid_number):
                msg = (
                    "Query returned unexpected number of records."
                    "Querying for {filter_kwargs}\nIn database: {values}\n".format(
                        filter_kwargs={self.model_field.name: pretty},
                        values=list(
                            self.model.objects.values_list(self.model_field.name, flat=True))
                    ))
                self.assertEqual(qs.count(), 1, msg=msg)
                self.assertEqual(
                    qs.get(), model_instance,
                    msg="Query returned unexpected record."
                )
            model_instance.delete()

    def test_saves_as_compact(self):
        # Assert that all std number are saved to the db in their compact format.
        for valid_number in self.valid:
            model_instance = self.create_model_instance(
                **{self.model_field.name: valid_number})
            model_instance.save()
            model_instance.refresh_from_db()
            with self.subTest(valid_number=valid_number):
                self.assertNotIn('-', getattr(model_instance, self.model_field.name))

    def test_modelform_uses_pretty_format(self):
        # Assert that the value displayed on a modelform is the 'pretty' and
        # not the compact version (if applicable).
        # We're using str(boundfield) for this as this renders the widget for
        # the formfield. Note that this test will always succeed for EAN fields
        # as they have nothing but compact.
        model_form_class = forms.modelform_factory(self.model, fields=[self.model_field.name])
        for valid_number in self.valid:
            formatted_number = self.model_field.get_format_callback()(valid_number)
            model_instance = self.create_model_instance(
                **{self.model_field.name: valid_number})
            model_instance.save()
            model_instance.refresh_from_db()
            model_form = model_form_class(instance=model_instance)
            with self.subTest(valid_number=valid_number):
                value_displayed = 'value="%s"' % formatted_number
                self.assertIn(value_displayed, str(model_form[self.model_field.name]))

    def test_min_max_parameter_passed_to_formfield(self):
        # Assert that the correct min and max length parameters are passed to
        # the field's formfield.
        formfield = self.model_field.formfield()
        self.assertEqual(formfield.min_length, self.model_field.min_length)
        self.assertEqual(formfield.max_length, self.model_field.max_length)

    def test_widget_class_passed_to_formfield(self):
        # Assert that the widget class needed to render the value in the
        # correct format is provided to the formfield.
        formfield = self.model_field.formfield()
        self.assertIsInstance(formfield.widget, StdNumWidget)

    def test_modelform_handles_formats_as_the_same_data(self):
        # Assert that a model form is not flagged as 'changed' when field's
        # initial value is of another format than the bound data.
        model_form_class = forms.modelform_factory(self.model, fields=[self.model_field.name])
        for valid_number in self.valid:
            formatted_number = self.model_field.get_format_callback()(valid_number)
            if formatted_number == valid_number:
                # No point in checking if valid_number is already 'pretty'
                continue
            model_instance = self.create_model_instance(
                **{self.model_field.name: valid_number})
            # This should save the compact form of the number
            model_instance.save()
            model_instance.refresh_from_db()
            # Create the model form with the number's pretty format as initial value.
            model_form = model_form_class(
                data={self.model_field.name: formatted_number},
                instance=model_instance
            )
            with self.subTest(valid_number=valid_number):
                msg = (
                    "ModelForm is flagged as changed for using different formats of the same "
                    "stdnum.\nform initial: {},\nform data: {}\n".format(
                        model_form[self.model_field.name].initial,
                        model_form[self.model_field.name].value()
                    ))
                self.assertFalse(model_form.has_changed(), msg=msg)


class TestStdNumField(MyTestCase):

    def test_formfield_widget(self):
        # Assert that the widget of the formfield is always an instance of StdNumWidget.
        model_field = _models.Buch._meta.get_field('ISBN')
        dummy_widget_class = type('Dummy', (StdNumWidget, ), {})
        widgets = [
            None,
            str, '1',
            AdminTextInputWidget, AdminTextInputWidget(),
            dummy_widget_class, dummy_widget_class()
        ]
        for widget in widgets:
            formfield_widget = model_field.formfield(widget=widget).widget
            with self.subTest(widget=str(widget)):
                self.assertTrue(isinstance(formfield_widget, StdNumWidget))


class TestISBNField(StdNumFieldTestsMixin, MyTestCase):
    model = _models.Buch
    model_field = _models.Buch._meta.get_field('ISBN')
    prototype_data = {'titel': 'Testbuch'}

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

    def test_modelform_handles_isbn10_as_isbn13(self):
        # Assert that the form treats a value of ISBN13 passed in as initial as the same as an
        # equal value of ISBN10 passed in as data.
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

        # Test for empty string
        model_instance = self.create_model_instance(**{self.model_field.name: ''})
        model_instance.save()
        model_instance.refresh_from_db()
        model_form = model_form_class(
            data={self.model_field.name: ''},
            instance=model_instance
        )
        self.assertFalse(model_form.has_changed())

    def test_converts_isbn10_to_isbn13_on_save(self):
        # Assert that only numbers of the isbn13 standard are saved
        for valid_number in self.valid:
            model_instance = self.create_model_instance(
                **{self.model_field.name: valid_number})
            model_instance.save()
            model_instance.refresh_from_db()
            with self.subTest(valid_number=valid_number):
                self.assertEqual(
                    getattr(model_instance, self.model_field.name),
                    isbn.compact(isbn.to_isbn13(valid_number))
                )

    def test_query_for_isbn10_finds_isbn13(self):
        isbn_10 = '123456789X'
        self.create_model_instance(ISBN=isbn.to_isbn13(isbn_10)).save()
        qs = self.model.objects.filter(ISBN=isbn_10)
        msg = (
            "Querying for ISBN10 did not return records with equivalent ISBN13."
            "\nISBN10: {}, in database: {}\n".format(
                isbn_10, list(self.model.objects.values_list('ISBN', flat=True))
            ))
        self.assertTrue(qs.exists(), msg=msg)


class TestISSNField(StdNumFieldTestsMixin, MyTestCase):
    model = _models.Magazin
    model_field = _models.Magazin._meta.get_field('issn')
    prototype_data = {'magazin_name': 'Testmagazin'}

    valid = ["12345679", "1234-5679"]
    invalid = [
        "123%&/79",  # InvalidFormat
        "9" * 20,  # InvalidLength
        '12345670',  # InvalidChecksum
        "1234-5670",  # InvalidChecksum
    ]

    def test_min_max_parameter_passed_to_formfield(self):
        # Assert that the correct min and max length parameters are passed
        # to the field's formfield.
        formfield = self.model_field.formfield()
        self.assertEqual(formfield.min_length, self.model_field.min_length)
        self.assertEqual(formfield.max_length, 17)


class TestEANField(StdNumFieldTestsMixin, MyTestCase):
    model = _models.Buch
    model_field = _models.Buch._meta.get_field('EAN')
    prototype_data = {'titel': 'Testbuch'}

    valid = ['73513537', "1234567890128"]
    invalid = [
        "123%&/()90128",  # InvalidFormat
        "9" * 20,  # InvalidLength
        '73513538',  # InvalidChecksum
        "1234567890123",  # InvalidChecksum
    ]


@tag("partial_date")
class TestPartialDate(MyTestCase):

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
        self.assertAttrsSet(PartialDate(year=2019, month=5, day=20), 2019, 5, 20, '%d %B %Y')
        # year and month
        self.assertAttrsSet(PartialDate(year=2019, month=5), 2019, 5, None, '%B %Y')
        self.assertAttrsSet(PartialDate(year=2019, month=5, day=0), 2019, 5, None, '%B %Y')
        # year and day
        self.assertAttrsSet(PartialDate(year=2019, day=20), 2019, None, 20, '%d %Y')
        self.assertAttrsSet(PartialDate(year=2019, month=0, day=20), 2019, None, 20, '%d %Y')
        # month and day
        self.assertAttrsSet(PartialDate(month=5, day=20), None, 5, 20, '%d %B')
        self.assertAttrsSet(PartialDate(year=0, month=5, day=20), None, 5, 20, '%d %B')
        # year only
        self.assertAttrsSet(PartialDate(year=2019), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year=2019, month=0), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year=2019, month=0, day=0), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(PartialDate(month=5), None, 5, None, '%B')
        self.assertAttrsSet(PartialDate(year=0, month=5), None, 5, None, '%B')
        self.assertAttrsSet(PartialDate(year=0, month=5, day=0), None, 5, None, '%B')
        # day only
        self.assertAttrsSet(PartialDate(day=20), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(month=0, day=20), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(year=0, month=0, day=20), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(PartialDate(day=0), None, None, None, '')
        self.assertAttrsSet(PartialDate(month=0, day=0), None, None, None, '')
        self.assertAttrsSet(PartialDate(year=0, month=0, day=0), None, None, None, '')

    def test_new_with_string_kwargs(self):
        # Full date
        self.assertAttrsSet(
            PartialDate(year='2019', month='5', day='20'), 2019, 5, 20, '%d %B %Y')
        # year and month
        self.assertAttrsSet(
            PartialDate(year='2019', month='05'), 2019, 5, None, '%B %Y')
        self.assertAttrsSet(
            PartialDate(year='2019', month='05', day='0'), 2019, 5, None, '%B %Y')
        # year and day
        self.assertAttrsSet(
            PartialDate(year='2019', day='20'), 2019, None, 20, '%d %Y')
        self.assertAttrsSet(
            PartialDate(year='2019', month='0', day='20'), 2019, None, 20, '%d %Y')
        # month and day
        self.assertAttrsSet(
            PartialDate(month='5', day='20'), None, 5, 20, '%d %B')
        self.assertAttrsSet(
            PartialDate(year='0000', month='5', day='20'), None, 5, 20, '%d %B')
        # year only
        self.assertAttrsSet(
            PartialDate(year='2019'), 2019, None, None, '%Y')
        self.assertAttrsSet(
            PartialDate(year='2019', month='00'), 2019, None, None, '%Y')
        self.assertAttrsSet(
            PartialDate(year='2019', month='00', day='0'), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(
            PartialDate(month='5'), None, 5, None, '%B')
        self.assertAttrsSet(
            PartialDate(year='0', month='05'), None, 5, None, '%B')
        self.assertAttrsSet(
            PartialDate(year='0000', month='05', day='00'), None, 5, None, '%B')
        # day only
        self.assertAttrsSet(
            PartialDate(day='20'), None, None, 20, '%d')
        self.assertAttrsSet(
            PartialDate(month='00', day='20'), None, None, 20, '%d')
        self.assertAttrsSet(
            PartialDate(year='0000', month='00', day='20'), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(
            PartialDate(day='0'), None, None, None, '')
        self.assertAttrsSet(
            PartialDate(month='0', day='0'), None, None, None, '')
        self.assertAttrsSet(
            PartialDate(year='0', month='0', day='0'), None, None, None, '')

    def test_new_with_string(self):
        # Full date
        self.assertAttrsSet(PartialDate.from_string('2019-05-20'), 2019, 5, 20, '%d %B %Y')
        # year and month
        self.assertAttrsSet(PartialDate.from_string('2019-05'), 2019, 5, None, '%B %Y')
        self.assertAttrsSet(PartialDate.from_string('2019-05-00'), 2019, 5, None, '%B %Y')
        # year and day
        self.assertAttrsSet(PartialDate.from_string('2019-00-20'), 2019, None, 20, '%d %Y')
        # month and day
        self.assertAttrsSet(PartialDate.from_string('05-20'), None, 5, 20, '%d %B')
        self.assertAttrsSet(PartialDate.from_string('0000-05-20'), None, 5, 20, '%d %B')
        # year only
        self.assertAttrsSet(PartialDate.from_string('2019'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate.from_string('2019-00'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate.from_string('2019-00-00'), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(PartialDate.from_string('0000-05'), None, 5, None, '%B')
        self.assertAttrsSet(PartialDate.from_string('0000-05-00'), None, 5, None, '%B')
        # day only
        self.assertAttrsSet(PartialDate.from_string('0000-00-20'), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate.from_string('00-20'), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(PartialDate.from_string(''), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('00'), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('0000-00'), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('0000-00-00'), None, None, None, '')

    def test_new_with_date(self):
        self.assertAttrsSet(
            PartialDate.from_date(datetime.date(2019, 5, 20)), 2019, 5, 20, '%d %B %Y')
        self.assertAttrsSet(
            PartialDate.from_date(datetime.datetime(2019, 5, 20)), 2019, 5, 20, '%d %B %Y')

    def test_new_validates_date(self):
        # Assert that PartialDate does not accept invalid dates (31st of February, etc.).
        invalid_dates = ('02-31', '04-31')
        for date in invalid_dates:
            with self.subTest():
                with self.assertRaises(ValueError, msg="Date used: %s" % date):
                    PartialDate.from_string(date)

        for date_args in (d.split('-') for d in invalid_dates):
            with self.subTest():
                with self.assertRaises(ValueError, msg="Date args used: %s" % date_args):
                    PartialDate(*date_args)

    def test_only_accepts_integers(self):
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
        with self.assertNotRaises(Exception):
            pd = PartialDate()
        self.assertAttrsSet(pd, year=None, month=None, day=None, date_format='')

    def test_db_value(self):
        test_data = [
            '2019-05-20', '2019-05-00', '2019-00-20', '2019-00-00',
            '0000-05-20', '0000-05-00', '0000-00-20', '0000-00-00',
        ]
        for data in test_data:
            with self.subTest():
                pd = PartialDate.from_string(data)
                self.assertEqual(pd.db_value, data)

    def test_equality_partial_date_to_partial_date(self):
        # Assert that two equal PartialDate objects equate.
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
        # Assert that a PartialDate and a string of the same value equate.
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
        self.assertTrue(PartialDate(4, 1, 1).__eq__(datetime.date(4, 1, 1)))
        msg = "An empty partial date should not equate to any datetime.date."
        self.assertFalse(PartialDate().__eq__(datetime.date(4, 1, 1)), msg=msg)

    def test_str(self):
        test_data = [
            ('2019-05-20', '20 May 2019'), ('2019-05-00', 'May 2019'),
            ('2019-00-20', '20 2019'), ('2019-00-00', '2019'),
            ('0000-05-20', '20 May'), ('0000-05-00', 'May'),
            ('0000-00-20', '20'), ('0000-00-00', ''),
        ]
        for data, expected in test_data:
            with self.subTest(data=data):
                pd = PartialDate.from_string(data)
                self.assertEqual(str(pd), expected)

        with_date = PartialDate.from_date(datetime.date(2019, 5, 20))
        self.assertEqual(str(with_date), '20 May 2019')


@tag("partial_date")
class TestPartialDateField(MyTestCase):

    def test_to_python_only_accepts_integers(self):
        # Assert that a ValidationError is raised when day/month/year are not integer.
        invalid_dates = ('Beep-05-12', '2019-as-12', '2019-05-as')
        for invalid_date in invalid_dates:
            with self.subTest():
                with self.assertRaises(ValidationError, msg=invalid_date) as cm:
                    PartialDateField().to_python(invalid_date)
            self.assertEqual(cm.exception.code, 'invalid_date')

    def test_from_db(self):
        # Assert that a value read from the db becomes a PartialDate.
        # (from_db_value)
        from_db = PartialDateField().from_db_value(
            value='2019-05-20', expression=None, connection=None)
        self.assertIsInstance(from_db, PartialDate)

    def test_to_db(self):
        # Assert that a PartialDate value is prepared as a string
        # (get_prep_value)
        test_data = [
            '2019-05-20', '2019-05-00', '2019-00-20', '2019-00-00',
            '0000-05-20', '0000-05-00', '0000-00-20', '0000-00-00',
        ]
        for data in test_data:
            with self.subTest():
                pd = PartialDate.from_string(data)
                prepped_value = PartialDateField().get_prep_value(value=pd)
                self.assertEqual(prepped_value, data)

    def test_to_python_takes_None(self):
        # Note that None should only be allowed if null=True;
        # which it shouldn't if it's a CharField.
        with self.assertNotRaises(Exception):
            value = PartialDateField().to_python(None)
        self.assertEqual(value, PartialDate())

    def test_to_python_takes_empty_string(self):
        with self.assertNotRaises(Exception):
            value = PartialDateField().to_python('')
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, PartialDate.from_string(''))

    def test_to_python_takes_string(self):
        pd = PartialDate.from_string('2019')
        with self.assertNotRaises(Exception):
            value = PartialDateField().to_python('2019')
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, pd)

    def test_to_python_takes_partial_date_instance(self):
        pd = PartialDate(year=2019, month=5, day=20)
        date = datetime.date(2019, 5, 20)
        with self.assertNotRaises(Exception):
            value = PartialDateField().to_python(date)
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, pd)

    def test_to_python_takes_date_instance(self):
        pd = PartialDate(year=2019)
        with self.assertNotRaises(Exception):
            value = PartialDateField().to_python(pd)
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, pd)

    def test_formfield(self):
        # Assert that PartialDateField's formfield is a MultiValueField instance.
        formfield = PartialDateField().formfield()
        self.assertIsInstance(formfield, forms.MultiValueField)


@tag("partial_date")
class TestPartialDateFieldQueries(DataTestCase):
    # Test various queries using PartialDateField.
    model = _models.Bildmaterial

    def test_constructor_partial_date(self):
        # Assert that a model instance can be created with a PartialDate.
        date = '2019-05-20'
        pd = PartialDate.from_string(date)
        obj = make(self.model)
        obj.datum = pd
        with self.assertNotRaises(Exception):
            obj.save()
        from_db = self.model.objects.filter(pk=obj.pk).values_list('datum', flat=True)[0]
        self.assertIsInstance(from_db, PartialDate)
        self.assertEqual(pd, from_db)

    def test_constructor_string(self):
        # Assert that a model instance can be created with a string.
        date = '2019-05-20'
        pd = PartialDate.from_string(date)
        obj = make(self.model)
        obj.datum = date
        with self.assertNotRaises(Exception):
            obj.save()
        from_db = self.model.objects.filter(pk=obj.pk).values_list('datum', flat=True)[0]
        self.assertIsInstance(from_db, PartialDate)
        self.assertEqual(pd, from_db)

    def test_lookup_range(self):
        # Assert that __range works as expected for dates even if the field is CharField.
        obj = make(self.model, datum='2019-05-20')
        qs = self.model.objects.filter(datum__range=('2019-05-19', '2019-05-21'))
        self.assertIn(obj, qs)

    def test_from_db(self):
        # Assert that a value read from the db becomes a PartialDate.
        # (from_db_value)
        obj = make(self.model, datum='2019-05-20')
        qs = self.model.objects.filter(pk=obj.pk)
        from_db = qs.values_list('datum', flat=True)[0]
        self.assertIsInstance(from_db, PartialDate)

    def test_to_db(self):
        # Assert that a PartialDate value is prepared as a string (or date)?
        # (get_prep_value)
        pd = PartialDate.from_string('2019-05-20')
        obj = make(self.model, datum=pd)
        qs = self.model.objects.filter(datum=pd)
        self.assertIn(obj, qs)

    def test_clean(self):
        date = '2019-05-20'
        pd = PartialDate.from_string(date)
        obj = self.model(titel='Whatever', datum=date)
        with self.assertNotRaises(Exception):
            cleaned = PartialDateField().clean(date, obj)
        self.assertEqual(cleaned, pd)

        with self.assertRaises(ValidationError):
            PartialDateField().clean('12019-05-20', obj)


@tag("partial_date")
class TestPartialDateFormField(MyTestCase):

    def test_widgets(self):
        # Assert that the formfield's widget is a MultiWidget.
        self.assertIsInstance(PartialDateFormField().widget, PartialDateWidget)

    def test_compress(self):
        data_list = [2019, 5, 20]
        field = PartialDateFormField()
        self.assertEqual(field.compress(data_list), PartialDate(year=2019, month=5, day=20))

        invalid_dates = ('Beep-05-12', '2019-as-12', '2019-05-as')
        for invalid_date in invalid_dates:
            invalid_date = invalid_date.split('-')
            with self.subTest():
                with self.assertRaises(ValidationError, msg=invalid_date) as cm:
                    field.compress(invalid_date)
                self.assertEqual(cm.exception.code, 'invalid')

    def test_clean(self):
        field = PartialDateFormField(required=False)
        for data in ([], [2019], [2019, 5], [2019, 5, 20], [None, 5, 20]):
            with self.assertNotRaises(ValidationError):
                cleaned = field.clean(data)
            self.assertEqual(cleaned, PartialDate(*data))

    def prepare_form_data(self, data):
        # The form data for a MultiValueField should be of the format:
        # <field_name>_[0,1...]
        return {
            k + '_%s' % i: v
            for k, values_list in data.items()
            for i, v in enumerate(values_list)
        }

    def assertNoFormErrors(self, form, field_name):
        # Assert that form does not produce errors with various data.
        f = field_name
        test_data = [
            # full
            {f: ['2019', '5', '20']},
            # year only
            {f: ['2019']},
            {f: ['2019', None]}, {f: ['2019', None, None]},
            {f: ['2019', '']}, {f: ['2019', '', '']},
            # year and month
            {f: ['2019', '5', None]}, {f: ['2019', '5', '']},
            # year and day
            {f: ['2019', None, '20']}, {f: ['2019', '', '20']},
            # month and day
            {f: [None, '5', '20']}, {f: ['', '5', '20']},
            # month only
            {f: [None, '5', None]}, {f: ['', '5', '']},
            # day only
            {f: [None, None, '20']}, {f: ['', '', '20']},

        ]
        for data in test_data:
            with self.subTest():
                self.assertFalse(form(data=self.prepare_form_data(data)).errors, msg=data)

    def test_as_form_required(self):
        form = type('Form', (forms.Form, ), {'datum': PartialDateFormField(required=True)})
        self.assertNoFormErrors(form, 'datum')
        for data in ({'datum': [None] * 3}, {'datum': [''] * 3}):
            with self.subTest():
                self.assertTrue(form(data=self.prepare_form_data(data)).errors, msg=data)

    def test_as_form_not_required(self):
        form = type('Form', (forms.Form, ), {'datum': PartialDateFormField(required=False)})
        self.assertNoFormErrors(form, 'datum')
        # Test 'empty'
        for data in ({'datum': [None] * 3}, {'datum': [''] * 3}):
            with self.subTest():
                self.assertFalse(form(data=self.prepare_form_data(data)).errors, msg=data)

    def test_as_modelform_required(self):
        form = forms.modelform_factory(model=_models.Veranstaltung, fields=['datum'])
        self.assertNoFormErrors(form, 'datum')
        for data in ({'datum': [None] * 3}, {'datum': [''] * 3}):
            with self.subTest():
                self.assertTrue(form(data=self.prepare_form_data(data)).errors, msg=data)

    def test_as_modelform_not_required(self):
        form = forms.modelform_factory(model=_models.Bildmaterial, fields=['datum'])
        self.assertNoFormErrors(form, 'datum')
        # Test 'empty'
        for data in ({'datum': [None] * 3}, {'datum': [''] * 3}):
            with self.subTest():
                self.assertFalse(form(data=self.prepare_form_data(data)).errors, msg=data)

    def assertIsInstanceOrSubclass(self, stuff, klass):
        if not isinstance(klass, type):
            klass = klass.__class__
        if isinstance(stuff, type):
            self.assertEqual(stuff, klass)
        else:
            self.assertIsInstance(stuff, klass)

    @patch.object(forms.MultiValueField, '__init__')
    def test_widget_kwarg(self, mocked_init):
        # Assert that only subclasses/instances of PartialDateWidget are
        # accepted as a custom widget.
        for valid_widget in (PartialDateWidget, PartialDateWidget()):
            with self.subTest():
                PartialDateFormField(widget=valid_widget)
                args, kwargs = mocked_init.call_args
                self.assertIn('widget', kwargs)
                self.assertIsInstanceOrSubclass(kwargs['widget'], PartialDateWidget)

        for invald_widget in (None, forms.NumberInput, forms.NumberInput()):
            with self.subTest():
                PartialDateFormField(widget=invald_widget)
                args, kwargs = mocked_init.call_args
                self.assertIn('widget', kwargs)
                self.assertIsInstanceOrSubclass(kwargs['widget'], PartialDateWidget)


@tag("partial_date")
class TestPartialDateWidget(MyTestCase):

    def test_subwidgets_are_number_inputs(self):
        for subwidget in PartialDateWidget().widgets:
            with self.subTest():
                self.assertIsInstance(subwidget, forms.widgets.NumberInput)

    def test_decompress(self):
        pd = PartialDate(year=2019, month=5, day=20)
        self.assertEqual(PartialDateWidget().decompress(pd), [2019, 5, 20])

        self.assertEqual(PartialDateWidget().decompress(None), [None] * 3)
