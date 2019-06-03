from .base import MyTestCase, DataTestCase

from django.db import transaction
from django.core.exceptions import ValidationError
from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

import datetime
from stdnum import isbn
from unittest.mock import patch

from DBentry.fields import (
    StdNumWidget, YearField, 
     PartialDate, PartialDateField, PartialDateWidget, PartialDateFormField
)
from DBentry import models as _models
from DBentry.factory import make
from DBentry.constants import MIN_JAHR, MAX_JAHR

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

# Reminder: the field's cleaning methods will reraise any ValidationError subtypes as a new ValidationError, so we cannot
# test for the correct subtype here.

class StdNumFieldTestsMixin(object):
        
    prototype_data = None # the data necessary to create a partial prototype of a model instance 
        
    def create_model_instance(self, **kwargs):
        if not self.prototype_data is None:
            instance_data = self.prototype_data.copy()
        else:
            instance_data = {}
        instance_data.update(kwargs)
        return self.model(**instance_data)
        
    def test_no_save_with_invalid_data(self):
        # Assert that no records can be saved with invalid data
        with self.collect_fails() as collector:
            for invalid_number in self.invalid:
                model_instance = self.create_model_instance(**{self.model_field.name:invalid_number})
                with collector():
                    with transaction.atomic():
                        with self.assertRaises(ValidationError, msg = "for invalid input: " + str(invalid_number)):
                            model_instance.save()
            
    def test_no_query_with_invalid_data(self):
        # Assert that no query can be attempted with invalid data (much like DateFields)
        with self.collect_fails() as collector:
            for invalid_number in self.invalid:
                with collector():
                    with self.assertRaises(ValidationError, msg = "for invalid input: " + str(invalid_number)):
                        self.model.objects.filter(**{self.model_field.name:invalid_number})
                        
    def test_query_with_any_format(self):
        # Assert queries are possible regardless of the format (pretty/compact) of the valid input
        with self.collect_fails() as collector:
            for valid_number in self.valid:
                with collector():
                    with self.assertNotRaises(ValidationError, msg = "for valid input: " + str(valid_number)):
                        self.model.objects.filter(**{self.model_field.name:valid_number})
     
    def test_query_with_any_format_returns_results(self):
        # Assert that the correct results are returned by querying for a std number no matter the format of the input
        # For this test to make any real sense, it is required that test_saves_as_compact passes.
        valid_seen = set()
        with self.collect_fails() as collector:
            for valid_number in self.valid:
                # Save as compact, query with pretty format
                compact = self.model_field.stdnum.compact(valid_number)
                pretty = self.model_field.get_format_callback()(valid_number)
                if compact in valid_seen:
                    continue
                valid_seen.add(compact)
                if compact == pretty:
                    continue
                
                model_instance = self.create_model_instance(**{self.model_field.name:compact})
                model_instance.save()
                qs = self.model.objects.filter(**{self.model_field.name:pretty})
                with collector():
                    msg_info = "Querying for {filter_kwargs}\nIn database: {values}\n".format(
                        filter_kwargs = {self.model_field.name:pretty}, 
                        values = list(self.model.objects.values_list(self.model_field.name, flat=True))
                    )
                    self.assertEqual(qs.count(), 1, msg = "Query returned unexpected number of records. " + msg_info)
                    self.assertEqual(qs.get(), model_instance, msg = "Query returned unexpected record.")
                model_instance.delete()
        
    def test_saves_as_compact(self):
        # Assert that all std number are saved to the db in their compact format
        with self.collect_fails() as collector:
            for valid_number in self.valid:
                model_instance = self.create_model_instance(**{self.model_field.name:valid_number})
                model_instance.save()
                model_instance.refresh_from_db()
                with collector():
                    self.assertNotIn('-', getattr(model_instance, self.model_field.name))
                    
    def test_modelform_uses_pretty_format(self):
        # Assert that the value displayed on a modelform is the 'pretty' and not the compact version (if applicable).
        # We're using str(boundfield) for this as this renders the widget for the formfield.
        # Note that this test will always succeed for EAN fields as they have nothing but compact.
        model_form_class = forms.modelform_factory(self.model, fields=[self.model_field.name])
        
        with self.collect_fails() as collector:            
            for valid_number in self.valid:
                model_instance = self.create_model_instance(**{self.model_field.name:valid_number})
                model_instance.save()
                model_instance.refresh_from_db()
                model_form = model_form_class(instance = model_instance)
                with collector():
                    self.assertIn(
                        'value="' + self.model_field.get_format_callback()(valid_number) + '"',  
                        str(model_form[self.model_field.name])
                    )
          
    def test_min_max_parameter_passed_to_formfield(self):
        # Assert that the correct min and max length parameters are passed to the field's formfield.
        formfield = self.model_field.formfield()
        self.assertEqual(formfield.min_length, self.model_field.min_length)
        self.assertEqual(formfield.max_length, self.model_field.max_length)    
        
    def test_widget_class_passed_to_formfield(self):
        # Assert that the widget class needed to render the value in the correct format is provided to the formfield.
        formfield = self.model_field.formfield()
        
        self.assertIsInstance(formfield.widget, StdNumWidget)
        
    def test_modelform_handles_formats_as_the_same_data(self):
        # Assert that a model form is not flagged as 'changed' when field's initial value is of another format than 
        # the bound data.
        model_form_class = forms.modelform_factory(self.model, fields=[self.model_field.name])
        
        with self.collect_fails() as collector:            
            for valid_number in self.valid:
                if self.model_field.get_format_callback()(valid_number) == valid_number:
                    # No point in checking if valid_number is already 'pretty'
                    continue
                model_instance = self.create_model_instance(**{self.model_field.name:valid_number})
                # This should save the compact form of the number
                model_instance.save()
                model_instance.refresh_from_db()
                # Create the model form with the number's pretty format as initial value.
                model_form = model_form_class(
                    data = {self.model_field.name:self.model_field.get_format_callback()(valid_number)}, 
                    instance = model_instance
                )
                with collector():
                    msg_info = "\nform initial: {}, form data: {}\n".format(
                        model_form[self.model_field.name].initial, 
                        model_form[self.model_field.name].value()
                    )
                    self.assertFalse(model_form.has_changed(), msg = "ModelForm is flagged as changed for using different formats of the same stdnum. " + msg_info)
   
class TestISBNField(StdNumFieldTestsMixin, MyTestCase):
    model = _models.buch
    model_field = _models.buch._meta.get_field('ISBN')
    prototype_data = {'titel':'Testbuch'} 
    
    valid = [
        '123456789X',  # ISBN-10 w/o hyphens
        '1-234-56789-X', # ISBN-10 w/ hyphens
        '9780471117094', # ISBN-13 w/o hyphens
        '978-0-471-11709-4', # ISBN-13 w/ hyphens
        '9791234567896', # ISBN-13 w/o hyphens with 979 bookmark
        '979-1-234-56789-6', # ISBN-13 w/ hyphens with 979 bookmark
    ]
    invalid = [
        "9999!)()/?1*", #InvalidFormat 
        "9"*20, #InvalidLength 
        "1234567890128", #InvalidComponent prefix != 978 
        '1234567890', #InvalidChecksum 
        '1-234-56789-0', #InvalidChecksum
        '9781234567890', #InvalidChecksum 
        '978-1-234-56789-0', #InvalidChecksum
    ]
            
    def test_modelform_handles_isbn10_as_isbn13(self):
        # Assert that the form treats an initial value of ISBN13 as the same as an equal value of ISBN10 passed in as data. Ugh, what is English?
        model_form_class = forms.modelform_factory(self.model, fields=[self.model_field.name])
        isbn10_seen = set()
        with self.collect_fails() as collector:
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
                
                model_instance = self.create_model_instance(**{self.model_field.name:isbn13})
                model_instance.save()
                model_instance.refresh_from_db()
                model_form = model_form_class(
                    data = {self.model_field.name:isbn10}, 
                    instance = model_instance
                )
                with collector():
                    msg_info = "\nform initial: {}, form data: {}\n".format(
                        model_form[self.model_field.name].initial, 
                        model_form[self.model_field.name].value()
                    )
                    self.assertFalse(model_form.has_changed(), msg = "ModelForm is flagged as changed for using different ISBN types of the same stdnum. " + msg_info)

    def test_converts_isbn10_to_isbn13_on_save(self):
        # Assert that only numbers of the isbn13 standard are saved
        with self.collect_fails() as collector:            
            for valid_number in self.valid:
                model_instance = self.create_model_instance(**{self.model_field.name:valid_number})
                model_instance.save()
                model_instance.refresh_from_db()
                with collector():
                    self.assertEqual(getattr(model_instance, self.model_field.name), isbn.compact(isbn.to_isbn13(valid_number)))
                    
    def test_query_for_isbn10_finds_isbn13(self):
        isbn_10 = '123456789X'
        self.create_model_instance(ISBN=isbn.to_isbn13(isbn_10)).save()
        
        qs = self.model.objects.filter(ISBN=isbn_10)
        msg_info = "\nISBN10: {}, in database: {}\n".format(
            isbn_10, 
            list(self.model.objects.values_list('ISBN', flat = True))
        )
        self.assertTrue(qs.exists(), msg = "Querying for ISBN10 did not return records with equivalent ISBN13. " + msg_info)
                
class TestISSNField(StdNumFieldTestsMixin, MyTestCase):
    model = _models.magazin
    model_field = _models.magazin._meta.get_field('issn')
    prototype_data = {'magazin_name':'Testmagazin'}
    
    valid = ["12345679", "1234-5679"]
    invalid = [
        "123%&/79", #InvalidFormat
        "9"*20, #InvalidLength
        '12345670', #InvalidChecksum 
        "1234-5670", #InvalidChecksum
    ]
    
class TestEANField(StdNumFieldTestsMixin, MyTestCase):
    model = _models.buch
    model_field = _models.buch._meta.get_field('EAN')
    prototype_data = {'titel':'Testbuch'} 
    
    valid = ['73513537', "1234567890128"]
    invalid = [
        "123%&/()90128", #InvalidFormat
        "9"*20, #InvalidLength
        '73513538', #InvalidChecksum
        "1234567890123", #InvalidChecksum
    ]
    

from django.test import tag
@tag("field")
@tag("wip")    
class TestPartialDate(MyTestCase):
    
    def assertAttrsSet(self, partial_date, year, month, day, date_format, msg = None):
        """
        Assert that the attributes 'year', 'month' and 'day' were set 
        correctly during the creation of the PartialDate.
        """
        attrs = ('__year', '__month', '__day', 'date_format')
        expected = dict(zip(attrs, (year, month, day, date_format)))
        with self.collect_fails(msg = msg) as collector:
            for attr in attrs:
                with collector():
                    self.assertEqual(getattr(partial_date, attr), expected[attr], msg = attr)
                    
    def test_new_with_int_kwargs(self):
        # Full date
        self.assertAttrsSet(PartialDate(year = 2019, month = 5, day = 20), 2019, 5, 20, '%d %b %Y')
        # year and month
        self.assertAttrsSet(PartialDate(year = 2019, month = 5), 2019, 5, None, '%b %Y')
        self.assertAttrsSet(PartialDate(year = 2019, month = 5, day = 0), 2019, 5, None, '%b %Y')
        # year and day
        self.assertAttrsSet(PartialDate(year = 2019, day = 20), 2019, None, 20, '%d %Y')
        self.assertAttrsSet(PartialDate(year = 2019, month = 0, day = 20), 2019, None, 20, '%d %Y')
        # month and day
        self.assertAttrsSet(PartialDate(month = 5, day = 20), None, 5, 20, '%d %b')
        self.assertAttrsSet(PartialDate(year = 0, month = 5, day = 20), None, 5, 20, '%d %b')
        # year only
        self.assertAttrsSet(PartialDate(year = 2019), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year = 2019, month = 0), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year = 2019, month = 0, day = 0), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(PartialDate(month = 5), None, 5, None, '%b')
        self.assertAttrsSet(PartialDate(year = 0, month = 5), None, 5, None, '%b')
        self.assertAttrsSet(PartialDate(year = 0000, month = 5, day = 0), None, 5, None, '%b')
        # day only
        self.assertAttrsSet(PartialDate(day = 20), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(month = 0, day = 20), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(year = 0, month = 0, day = 20), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(PartialDate(day = 0), None, None, None, '')
        self.assertAttrsSet(PartialDate(month = 0, day = 0), None, None, None, '')
        self.assertAttrsSet(PartialDate(year = 0, month = 0, day = 0), None, None, None, '')
        
    def test_new_with_string_kwargs(self):
        # Full date
        self.assertAttrsSet(PartialDate(year = '2019', month = '5', day = '20'), 2019, 5, 20, '%d %b %Y')
        # year and month
        self.assertAttrsSet(PartialDate(year = '2019', month = '05'), 2019, 5, None, '%b %Y')
        self.assertAttrsSet(PartialDate(year = '2019', month = '05', day = '0'), 2019, 5, None, '%b %Y')
        # year and day
        self.assertAttrsSet(PartialDate(year = '2019', day = '20'), 2019, None, 20, '%d %Y')
        self.assertAttrsSet(PartialDate(year = '2019', month = '0', day = '20'), 2019, None, 20, '%d %Y')
        # month and day
        self.assertAttrsSet(PartialDate(month = '5', day = '20'), None, 5, 20, '%d %b')
        self.assertAttrsSet(PartialDate(year = '0000', month = '5', day = '20'), None, 5, 20, '%d %b')
        # year only
        self.assertAttrsSet(PartialDate(year = '2019'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year = '2019', month = '00'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate(year = '2019', month = '00', day = '0'), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(PartialDate(month = '5'), None, 5, None, '%b')
        self.assertAttrsSet(PartialDate(year = '0', month = '05'), None, 5, None, '%b')
        self.assertAttrsSet(PartialDate(year = '0000', month = '05', day = '00'), None, 5, None, '%b')
        # day only
        self.assertAttrsSet(PartialDate(day = '20'), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(month = '00', day = '20'), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate(year = '0000', month = '00', day = '20'), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(PartialDate(day = '0'), None, None, None, '')
        self.assertAttrsSet(PartialDate(month = '0', day = '0'), None, None, None, '')
        self.assertAttrsSet(PartialDate(year = '0', month = '0', day = '0'), None, None, None, '')
    
    def test_new_with_string(self):
        # Full date
        self.assertAttrsSet(PartialDate.from_string('2019-05-20'), 2019, 5, 20, '%d %b %Y')
        # year and month
        self.assertAttrsSet(PartialDate.from_string('2019-05'), 2019, 5, None, '%b %Y')
        self.assertAttrsSet(PartialDate.from_string('2019-05-00'), 2019, 5, None, '%b %Y')
        # year and day
        self.assertAttrsSet(PartialDate.from_string('2019-00-20'), 2019, None, 20, '%d %Y')
        # month and day
        self.assertAttrsSet(PartialDate.from_string('05-20'), None, 5, 20, '%d %b')
        self.assertAttrsSet(PartialDate.from_string('0000-05-20'), None, 5, 20, '%d %b')
        # year only
        self.assertAttrsSet(PartialDate.from_string('2019'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate.from_string('2019-00'), 2019, None, None, '%Y')
        self.assertAttrsSet(PartialDate.from_string('2019-00-00'), 2019, None, None, '%Y')
        # month only
        self.assertAttrsSet(PartialDate.from_string('0000-05'), None, 5, None, '%b')
        self.assertAttrsSet(PartialDate.from_string('0000-05-00'), None, 5, None, '%b')
        # day only
        self.assertAttrsSet(PartialDate.from_string('0000-00-20'), None, None, 20, '%d')
        self.assertAttrsSet(PartialDate.from_string('00-20'), None, None, 20, '%d')
        # empty
        self.assertAttrsSet(PartialDate.from_string(''), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('00'), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('0000-00'), None, None, None, '')
        self.assertAttrsSet(PartialDate.from_string('0000-00-00'), None, None, None, '')
        
    def test_new_with_date(self):
        self.assertAttrsSet(PartialDate.from_date(datetime.date(2019, 5, 20)), 2019, 5, 20, '%d %b %Y')
        self.assertAttrsSet(PartialDate.from_date(datetime.datetime(2019, 5, 20)), 2019, 5, 20, '%d %b %Y')
        
    def test_new_validates_date(self):
        # Assert that PartialDate does not accept invalid dates (31st of February, etc.).
        invalid_dates = ('02-31', '04-31')
        for date in invalid_dates:
            with self.subTest():
                with self.assertRaises(ValueError, msg = "Date used: %s" % date):
                    PartialDate.from_string(date)
                    
        for date_args in (d.split('-') for d in invalid_dates):
            with self.subTest():
                with self.assertRaises(ValueError, msg = "Date args used: %s" % date_args):
                    PartialDate(*date_args)
                    
    def test_only_accepts_integers(self):
        invalid_dates = ('Beep-05-12', '2019-as-12', '2019-05-as')
        for date in invalid_dates:
            with self.subTest():
                with self.assertRaises(ValueError, 
                    msg = 'from_string should raise a ValueError if it cannot match its regex.'):
                    PartialDate.from_string(date)
        
        for date_args in (d.split('-') for d in invalid_dates):
            with self.subTest():
                with self.assertRaises(ValueError,
                    msg = "casting a string literal to int should raise a ValueError"):
                    PartialDate(*date_args)
                    
    def test_empty_date(self):
        with self.assertNotRaises(Exception):
            pd = PartialDate()
        self.assertAttrsSet(pd, year = None, month = None, day = None, date_format = '')
        
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
        date = '2019-05-20'
        self.assertTrue(PartialDate.from_string(date) == PartialDate.from_string(date))
        self.assertTrue(PartialDate(*date.split('-')) == PartialDate(*date.split('-')))
        
    def test_equality_string_to_partial_date(self):
        # Assert that a PartialDate and a string of the same value equate.
        date = '2019-05-20'
        self.assertTrue(PartialDate.from_string(date).__eq__(date))
        self.assertFalse(PartialDate.from_string(date).__eq__('Nota-valid-date'), msg = 'Invalid string should equate to false.')
        
    def test_str(self):
        test_data = [
            ('2019-05-20', '20 May 2019'), ('2019-05-00', 'May 2019'), 
            ('2019-00-20', '20 2019'), ('2019-00-00', '2019'), 
            ('0000-05-20', '20 May'), ('0000-05-00', 'May'), 
            ('0000-00-20', '20'), ('0000-00-00', ''), 
        ]
        for data, expected in test_data:
            with self.subTest():
                pd = PartialDate.from_string(data)
                self.assertEqual(str(pd), expected)
                
        with_date = PartialDate.from_date(datetime.date(2019, 5, 20))
        self.assertEqual(str(with_date), '20 May 2019')
        
#    def test_bool(self):
#        # bool(PartialDate()) and bool(PartialDate(4,1,1)) seem*ed* to be False?? but it's fixed now?
#        self.assertTrue(PartialDate())
#        self.assertTrue(PartialDate(2019, 5, 20))

@tag("field")
@tag("wip")    
class TestPartialDateField(MyTestCase):
    
    def test_to_python_only_accepts_integers(self):
        # Assert that a ValidationError is raised when day/month/year are not integer.
        invalid_dates = ('Beep-05-12', '2019-as-12', '2019-05-as')
        for invalid_date in invalid_dates:
            with self.subTest():
                with self.assertRaises(ValidationError, msg = invalid_date) as cm:
                    PartialDateField().to_python(invalid_date)
            self.assertEqual(cm.exception.code, 'invalid_date')
    
    def test_from_db(self):
        # Assert that a value read from the db becomes a PartialDate.
        #(from_db_value)
        from_db = PartialDateField().from_db_value(value = '2019-05-20', expression = None, connection = None)
        self.assertIsInstance(from_db, PartialDate)
        
    def test_to_db(self):
        # Assert that a PartialDate value is prepared as a string
        #(get_prep_value)
        test_data = [
            '2019-05-20', '2019-05-00', '2019-00-20', '2019-00-00', 
            '0000-05-20', '0000-05-00', '0000-00-20', '0000-00-00', 
        ]
        for data in test_data:
            with self.subTest():
                pd = PartialDate.from_string(data)
                prepped_value = PartialDateField().get_prep_value(value = pd)
                self.assertEqual(prepped_value, data)
        
    def test_to_python_takes_None(self):
        #NOTE: should only be allowed if null=True; which it shouldn't if it's a CharField
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
        pd = PartialDate(year = 2019, month = 5, day = 20)
        date = datetime.date(2019, 5, 20)
        with self.assertNotRaises(Exception):
            value = PartialDateField().to_python(date)
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, pd)        
        
    def test_to_python_takes_date_instance(self):
        pd = PartialDate(year = 2019)
        with self.assertNotRaises(Exception):
            value = PartialDateField().to_python(pd)
        self.assertIsInstance(value, PartialDate)
        self.assertEqual(value, pd)
        
    def test_formfield(self):
        # Assert that PartialDateField's formfield is a MultiValueField instance
        formfield = PartialDateField().formfield()
        self.assertIsInstance(formfield, forms.MultiValueField)

@tag("field")
@tag("wip")    
class TestPartialDateFieldQueries(DataTestCase):
    # Test various queries using PartialDateField
    model = _models.bildmaterial
    
    def test_constructor_partial_date(self):
        # Assert that a model instance can be created with a PartialDate.
        date = '2019-05-20'
        pd = PartialDate.from_string(date)
        obj = make(self.model)
        obj.datum = pd
        with self.assertNotRaises(Exception):
            obj.save()
        from_db = self.model.objects.filter(pk = obj.pk).values_list('datum', flat = True)[0]
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
        from_db = self.model.objects.filter(pk = obj.pk).values_list('datum', flat = True)[0]
        self.assertIsInstance(from_db, PartialDate)
        self.assertEqual(pd, from_db)
        
    def test_lookup_range(self):
        # Assert that __range works as expected for dates even if the field is CharField.
        obj = make(self.model, datum = '2019-05-20')
        qs = self.model.objects.filter(datum__range = ('2019-05-19', '2019-05-21'))
        self.assertIn(obj, qs)
        
    def test_from_db(self):
        # Assert that a value read from the db becomes a PartialDate.
        #(from_db_value)
        obj = make(self.model, datum = '2019-05-20')
        qs = self.model.objects.filter(pk = obj.pk)
        from_db = qs.values_list('datum', flat = True)[0]
        self.assertIsInstance(from_db, PartialDate)
        
    def test_to_db(self):
        # Assert that a PartialDate value is prepared as a string (or date)?
        #(get_prep_value)
        pd = PartialDate.from_string('2019-05-20')
        obj = make(self.model, datum = pd)
        qs = self.model.objects.filter(datum = pd)
        self.assertIn(obj, qs)
        
    def test_clean(self):
        date = '2019-05-20'
        pd = PartialDate.from_string(date)
        obj = self.model(titel = 'Whatever', datum = date)
        with self.assertNotRaises(Exception):
            cleaned = PartialDateField().clean(date, obj)
        self.assertEqual(cleaned, pd)
        
        with self.assertRaises(ValidationError):
            PartialDateField().clean('12019-05-20', obj)
        
@tag("field")
@tag("wip")    
class TestPartialDateFormField(MyTestCase):
    
    def test_widgets(self):
        # Assert that the formfield's widget is a MultiWidget.
        self.assertIsInstance(PartialDateFormField().widget, PartialDateWidget)
        
    def test_compress(self):
        data_list = [2019, 5, 20]
        field = PartialDateFormField()
        self.assertEqual(field.compress(data_list), PartialDate(year = 2019, month = 5, day = 20))
        
        invalid_dates = ('Beep-05-12', '2019-as-12', '2019-05-as')
        for invalid_date in invalid_dates:
            invalid_date = invalid_date.split('-')
            with self.subTest():
                with self.assertRaises(ValidationError, msg = invalid_date) as cm:
                    field.compress(invalid_date)   
                self.assertEqual(cm.exception.code, 'invalid')
        
    def test_clean(self):
        field = PartialDateFormField(required = False)
        for data in ([], [2019], [2019, 5], [2019, 5, 20], [None, 5, 20]):
            with self.assertNotRaises(ValidationError):
                cleaned = field.clean(data)
            self.assertEqual(cleaned, PartialDate(*data))
            
    def assertNoFormErrors(self, form):
        # Assert that form does not produce errors with various data
        test_data = [
            # Empty stuff
            {'a':[None]*3}, {'a':['']*3},
            # full
            {'a':['2019', '5', '20']}, 
            # year only
            {'a':['2019']}, 
            {'a':['2019', None]}, {'a':['2019', None, None]}, 
            {'a':['2019', '']}, {'a':['2019', '', '']}, 
            # year and month
            {'a':['2019', '5', None]}, {'a':['2019', '5', '']}, 
            # year and day
            {'a':['2019', None, '20']}, {'a':['2019', '', '20']}, 
            # month and day
            {'a':[None, '5', '20']}, {'a':['', '5', '20']}, 
            # month only
            {'a':[None, '5', None]}, {'a':['', '5', '']}, 
            # day only
            {'a':[None, None, '20']}, {'a':['', '', '20']}
        ]
        for data in test_data:
            with self.subTest():
                self.assertFalse(form(data = data).errors, msg = data)
            
    def test_as_form(self):
        form = type('Form', (forms.Form, ), {'a': PartialDateFormField(required = False)})
        self.assertNoFormErrors(form)
        
    def test_as_modelform(self):
        form = forms.modelform_factory(model = _models.bildmaterial, fields = ['datum'])
        self.assertNoFormErrors(form)
        
    def assertIsInstanceOrSubclass(self, stuff, klass):
        if not isinstance(klass, type):
            klass = klass.__class__
        if isinstance(stuff, type):
            self.assertEqual(stuff, klass)
        else:
            self.assertIsInstance(stuff, klass)
            
    @patch.object(forms.MultiValueField, '__init__')
    def test_widget_kwarg(self, mocked_init):
        # Assert that only subclasses/instances of PartialDateWidget are accepted as a custom widget.
        for valid_widget in (PartialDateWidget, PartialDateWidget()):
            with self.subTest():
                PartialDateFormField(widget = valid_widget)
                args, kwargs = mocked_init.call_args
                self.assertIn('widget', kwargs)
                self.assertIsInstanceOrSubclass(kwargs['widget'], PartialDateWidget)
        
        for invald_widget in (None, forms.NumberInput, forms.NumberInput()):
            with self.subTest():
                PartialDateFormField(widget = invald_widget)
                args, kwargs = mocked_init.call_args
                self.assertIn('widget', kwargs)
                self.assertIsInstanceOrSubclass(kwargs['widget'], PartialDateWidget)

        
@tag("field")
@tag("wip")    
class TestPartialDateWidget(MyTestCase):
    
    def test_subwidgets_are_number_inputs(self):
        for subwidget in PartialDateWidget().widgets:
            with self.subTest():
                self.assertIsInstance(subwidget, forms.widgets.NumberInput)
                
    def test_decompress(self):
        pd = PartialDate(year = 2019, month = 5, day = 20)
        self.assertEqual(PartialDateWidget().decompress(pd), [2019, 5, 20])
        
        self.assertEqual(PartialDateWidget().decompress(None), [None]*3)
