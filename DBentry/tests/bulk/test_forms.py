from django import forms as django_forms
from django.core.exceptions import ValidationError
from django.test import tag
from django.utils.translation import override as translation_override

import DBentry.models as _models
from DBentry.bulk.forms import BulkForm, BulkFormAusgabe
from DBentry.bulk.fields import BulkField, BulkJahrField
from DBentry.factory import make, batch
from DBentry.tests.base import FormTestCase
from DBentry.tests.mixins import TestDataMixin


class TestBulkForm(FormTestCase):

    form_class = BulkForm
    dummy_attrs = {
            'some_fld': django_forms.CharField(required=False),
            'some_bulkfield': BulkField(required=False, label='num'),
            'req_fld': BulkJahrField(required=False),
            'another': django_forms.CharField(required=False),
            'model': _models.ausgabe,
            'each_fields': ['another', 'some_fld'],
            'split_fields': ['req_fld', 'some_bulkfield'],
            'field_order': ['some_fld', 'some_bulkfield', 'req_fld', 'another'],
        }
    dummy_bases = (BulkForm, )

    def test_init_sets_fieldsets(self):
        # Assert that the form's fieldsets are set up properly during init.
        form = self.get_dummy_form()
        # The 'each' fieldset
        self.assertEqual(form.fieldsets[0][1]['fields'], ['some_fld', 'another'])
        # The 'split_fields' fieldset
        self.assertEqual(
            form.fieldsets[1][1]['fields'],
            ['some_bulkfield', 'req_fld']
        )

    def test_has_changed(self):
        # _row_data should be empty if anything about the form data has changed.
        data = {'req_fld': '2001'}
        initial = {'req_fld': '2000'}
        form = self.get_dummy_form(data=data, initial=initial)
        form._row_data = [1]  # put *something* into _row_data
        self.assertTrue(form.has_changed())
        self.assertEqual(len(form._row_data), 0)

    def test_clean_errors_uneven_item_count(self):
        # Assert that a mismatch in item_counts results in a field error.
        data = {'some_bulkfield': '1,2', 'req_fld': '2000'}
        form = self.get_dummy_form(data=data)
        self.assertFalse(form.is_valid())
        # some_bulkfield sets total_count to 2;
        # conflicting with item_count of req_fld.
        self.assertTrue(form.has_error('req_fld'))

    def test_clean_populating_split_data(self):
        # Check if split_data was populated correctly.
        data = {'some_bulkfield': '1,2', 'req_fld': '2000,2001', 'some_fld': '4,5'}
        form = self.get_dummy_form(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertTrue(hasattr(form, 'split_data'))
        test_data = [
            ('some_bulkfield', ['1', '2']),
            ('req_fld', ['2000', '2001'])
        ]
        for field_name, expected in test_data:
            with self.subTest(field_name=field_name):
                self.assertIn(field_name, form.split_data)
                self.assertEqual(form.split_data[field_name], expected)

    @tag("bug")
    def test_clean_handles_field_validation_errors(self):
        # If a BulkField raises a ValidationError during its cleaning process
        # the field's value is removed from cleaned_data.
        # The form's clean method needs to be able to handle an expected,
        # but missing, field in cleaned_data.
        data = {'some_bulkfield': 'ABC', 'req_fld': '2000A', 'some_fld': '4,5'}
        form = self.get_dummy_form(data=data)
        with self.assertNotRaises(KeyError):
            form.is_valid()


class TestBulkFormAusgabe(TestDataMixin, FormTestCase):

    form_class = BulkFormAusgabe
    model = _models.ausgabe

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.magazin, magazin_name='Testmagazin')
        cls.zraum = make(_models.lagerort, ort='Bestand LO')
        cls.dublette = make(_models.lagerort, ort='Dubletten LO')
        cls.audio_lo = make(_models.lagerort)
        cls.prov = make(_models.provenienz)
        cls.updated = make(
            cls.model,
            magazin=cls.mag,
            ausgabe_jahr__jahr=[2000, 2001],
            ausgabe_num__num=1
        )
        cls.multi1, cls.multi2 = batch(
            cls.model, 2,
            magazin=cls.mag,
            ausgabe_jahr__jahr=[2000, 2001],
            ausgabe_num__num=5
        )
        cls.test_data = [cls.updated, cls.multi1, cls.multi2]
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.valid_data = {
            'magazin': self.mag.pk,
            'jahrgang': '11',
            'jahr': '2000,2001',
            'num': '1,2,3,4,4,5',
            'monat': '',
            'lnum': '',
            'audio': True,
            'audio_lagerort': self.audio_lo.pk,
            'ausgabe_lagerort': self.zraum.pk,
            'dublette': self.dublette.pk,
            'provenienz': self.prov.pk,
            'beschreibung': '',
            'status': 'unb'
        }

    def test_init_fieldsets(self):
        # Investigate the each_field and split_field fieldsets.
        form = self.get_form()
        # each_field fieldset:
        expected = [
            'magazin', 'jahrgang', 'jahr', 'status', 'beschreibung', 'bemerkungen',
            'audio', 'audio_lagerort', 'ausgabe_lagerort', 'dublette', 'provenienz'
        ]
        self.assertEqual(form.fieldsets[0][1]['fields'], expected)
        # split_field fieldset:
        expected = ['num', 'monat', 'lnum']
        self.assertEqual(form.fieldsets[1][1]['fields'], expected)

    def test_clean_errors_audio_but_no_audio_lagerort(self):
        # Assert that 'audio_lagerort' is required if data for 'audio' is present.
        data = self.valid_data.copy()
        del data['audio_lagerort']
        form = self.get_form(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('audio_lagerort'))

    def test_clean_errors_uneven_item_count(self):
        # Assert that a mismatch in item_counts results in a field error.
        data = self.valid_data.copy()
        data['monat'] = '1'
        form = self.get_form(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('monat'))

    def test_lookup_instance(self):
        # Assert that lookup_instance returns the expected number of results
        # for a given row.
        test_data = [
            ({'num': '2', 'jahr': '2000', 'lnum': '312', 'monat': '12'}, 0),
            ({'num': '1', 'jahr': ['2000', '2001']}, 1),
            ({'num': '5', 'jahr': ['2000', '2001']}, 2)
        ]
        form = self.get_valid_form()
        for row_data, expected in test_data:
            with self.subTest(data=row_data):
                self.assertEqual(form.lookup_instance(row_data).count(), expected)

    def test_lookup_instance_jahrgang(self):
        form = self.get_valid_form()
        # Assert that lookup_instance can now find matching instances via their
        # jahrgang.
        instance = make(
            self.model,
            magazin=self.mag,
            jahrgang=1,
            ausgabe_num__num=5,
            ausgabe_jahr__jahr=2002
        )
        row_data = {'jahrgang': '1', 'num': '5'}
        lookuped = form.lookup_instance(row_data)
        self.assertEqual(lookuped.count(), 1)
        self.assertIn(instance, lookuped)

        # Assert that lookup_instance will use jahrgang OR jahr to find
        # matching instances.
        row_data = {'jahrgang': '1', 'num': '5', 'jahr': '2001'}
        lookuped = form.lookup_instance(row_data)
        # Should find 3 instances:
        # the created instance, plus self.multi1, self.multi2.
        self.assertEqual(lookuped.count(), 3)
        self.assertIn(instance, lookuped)

        # Assert that lookup_instance will use jahrgang AND jahr
        # if there are instances that can be found like that.
        instance = make(
            self.model,
            magazin=self.mag,
            jahrgang=2,
            ausgabe_num__num=5,
            ausgabe_jahr__jahr=2002
        )
        # Create a control instance that should not be included in the result.
        make(
            self.model,
            magazin=self.mag,
            jahrgang=2,
            ausgabe_num__num=5,
            ausgabe_jahr__jahr=2003
        )
        row_data = {'jahrgang': '2', 'num': '5', 'jahr': '2002'}
        lookuped = form.lookup_instance(row_data)
        self.assertEqual(lookuped.count(), 1)
        self.assertIn(instance, lookuped)

    def test_row_data_prop(self):
        # Verify that form.row_data contains the expected data.
        form = self.get_valid_form()

        row_template = {
            'magazin': self.mag,
            'jahrgang': 11,
            'jahr': ['2000', '2001'],
            'audio': True,
            'audio_lagerort': self.audio_lo,
            'ausgabe_lagerort': self.zraum,
            'dublette': self.dublette,
            'provenienz': self.prov,
            'status': 'unb'
        }
        # valid_data contains 6 rows.
        # Prepare expected results for each of those rows:
        row_1 = row_template.copy()
        # The first row should add a dublette to self.obj1:
        row_1.update(
            {'num': '1', 'ausgabe_lagerort': self.dublette,  'instance': self.obj1}
        )
        row_2 = row_template.copy()
        # Rows 2 through 4 should create new objects:
        row_2.update({'num': '2'})
        row_3 = row_template.copy()
        row_3.update({'num': '3'})
        row_4 = row_template.copy()
        row_4.update({'num': '4', })
        # Row 5 should be considered a dupe of the previous row and should be
        # marked as a dublette of the previous row.
        row_5 = row_template.copy()
        row_5.update(
            {'num': '4', 'ausgabe_lagerort': self.dublette, 'dupe_of': row_4}
        )
        row_6 = row_template.copy()
        # Data for this row will find more than one instance;
        # expected to show up in 'multiples'.
        row_6.update({
            'num': '5',
            'multiples': self.model.objects.filter(pk__in=[self.obj2.pk, self.obj3.pk])
        })
        expected = [row_1, row_2, row_3, row_4, row_5, row_6]

        self.assertEqual(len(form.row_data), len(expected))

        for c, row in enumerate(form.row_data):
            row_name = 'row_%s' % (c + 1)
            with self.subTest(row=row_name):
                if c in [1, 2, 3]:
                    # Assert that row_2, _3, _4 do not have an instance
                    # assigned to them (they represent new instances):
                    self.assertIsNone(row.get('instance', None))
                if 'multiples' in row and 'multiples' in expected[c]:
                    # Need to compare the QuerySets of key 'multiples' separately.
                    # assertQuerysetEqual doesn't transform the second parameter.
                    self.assertEqual(
                        list(row.pop('multiples').values_list('pk', flat=True)),
                        list(expected[c].pop('multiples').values_list('pk', flat=True))
                    )
                self.assertEqual(row, expected[c])


    def test_row_data_prop_invalid(self):
        # If the form is invalid, row_data should return empty
        form = self.get_form()
        self.assertEqual(form.row_data, [])

    def test_row_data_prop_homeless_fielddata_present(self):
        # Assert that a field that does not belong to either each_fields or
        # split_fields is not included in row_data.
        form_class = type('DummyForm', (self.form_class, ), {'homeless': BulkField()})
        data = self.valid_data.copy()
        data['homeless'] = '9,8,7,6,5,5'
        form = form_class(data=data)
        self.assertFormValid(form)
        self.assertFalse(all('homeless' in row for row in form.row_data))

    @translation_override(language = None)
    def test_clean_handles_month_gt_12(self):
        data = self.valid_data.copy()
        data['monat'] = '13'
        data['num'] = ''
        form = self.get_form(data=data)
        with self.assertRaises(ValidationError) as cm:
            form.clean_monat()
        self.assertEqual(
            cm.exception.args[0],
            'Monat-Werte müssen zwischen 1 und 12 liegen.'
        )
