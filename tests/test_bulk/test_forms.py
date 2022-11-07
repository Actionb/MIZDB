from unittest.mock import Mock, patch

from django import forms
from django.core.exceptions import ValidationError
from django.test import tag
from django.utils.translation import override as translation_override

from dbentry import models as _models
from dbentry.tools.bulk.fields import BulkField, BulkJahrField
from dbentry.tools.bulk.forms import BulkForm, BulkFormAusgabe
from tests.case import DataTestCase, MIZTestCase
from tests.factory import batch, make


class TestBulkForm(MIZTestCase):
    class TestForm(BulkForm):
        name = forms.CharField(required=False)
        num = BulkField(required=False, label='num')
        years = BulkJahrField(required=False)
        description = forms.CharField(required=False)

        model = _models.Ausgabe
        each_fields = ['description', 'name']
        split_fields = ['years', 'num']
        field_order = ['name', 'num', 'years', 'description']

    def test_init_sets_fieldsets(self):
        """Assert that the form's fieldsets are set up during init."""
        form = self.TestForm()
        # The 'each' fieldset:
        self.assertEqual(form.fieldsets[0][1]['fields'], ['name', 'description'])
        # The 'split_fields' fieldset:
        self.assertEqual(form.fieldsets[1][1]['fields'], ['num', 'years'])

    def test_has_changed(self):
        """_row_data should be empty, if anything about the form data has changed."""
        form = self.TestForm(data={'years': '2001'}, initial={'years': '2000'})
        form._row_data = [1]  # put *something* into _row_data
        self.assertTrue(form.has_changed())
        self.assertFalse(form._row_data)
        self.assertFalse(form.row_data)

    def test_clean_errors_uneven_item_count(self):
        """Assert that a mismatch in item_counts results in a field error."""
        form = self.TestForm(data={'num': '1,2', 'years': '2000'})
        self.assertFalse(form.is_valid())
        # num sets total_count to 2: conflicting with item_count of years.
        self.assertTrue(form.has_error('years'))

    def test_clean_populating_split_data(self):
        """Check that split_data was populated correctly."""
        form = self.TestForm(data={'num': '1,2', 'years': '2000,2001', 'name': '4,5'})
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertTrue(hasattr(form, 'split_data'))
        test_data = [
            ('num', ['1', '2']),
            ('years', ['2000', '2001'])
        ]
        for field_name, expected in test_data:
            with self.subTest(field_name=field_name):
                self.assertIn(field_name, form.split_data)
                self.assertEqual(form.split_data[field_name], expected)

    @tag("bug")
    def test_clean_handles_field_validation_errors(self):
        """
        Assert that clean does not attempt to process data that other clean
        methods have found to be invalid.
        """
        # If a BulkField raises a ValidationError during its cleaning process
        # the field's value is removed from cleaned_data.
        # The form's clean method needs to be able to handle an expected,
        # but missing, field in cleaned_data.
        form = self.TestForm(data={'num': 'ABC', 'years': '2000A', 'name': '4,5'})
        with self.assertNotRaises(KeyError):
            form.is_valid()


class TestBulkFormAusgabe(DataTestCase):
    form_class = BulkFormAusgabe
    model = _models.Ausgabe

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.lo = make(_models.Lagerort, ort='Bestand LO')
        cls.dublette = make(_models.Lagerort, ort='Dubletten LO')
        cls.audio_lo = make(_models.Lagerort)
        cls.prov = make(_models.Provenienz)
        # noinspection PyUnresolvedReferences
        cls.updated = make(
            cls.model,
            magazin=cls.mag,
            ausgabejahr__jahr=[2000, 2001],
            ausgabenum__num=1
        )
        # noinspection PyUnresolvedReferences
        cls.multi1, cls.multi2 = batch(
            cls.model, 2,
            magazin=cls.mag,
            ausgabejahr__jahr=[2000, 2001],
            ausgabenum__num=5,
            jahrgang=2
        )
        # noinspection PyUnresolvedReferences
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
            'ausgabe_lagerort': self.lo.pk,
            'dublette': self.dublette.pk,
            'provenienz': self.prov.pk,
            'beschreibung': '',
            'status': 'unb'
        }

    def test_init_fieldsets(self):
        """Assert that the form's fieldsets are set up during init."""
        form = self.form_class()
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
        """Assert that 'audio_lagerort' is required, if data for 'audio' is present."""
        data = self.valid_data.copy()
        del data['audio_lagerort']
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('audio_lagerort'))

    def test_clean_errors_uneven_item_count(self):
        """Assert that a mismatch in item_counts results in a field error."""
        data = self.valid_data.copy()
        data['monat'] = '1'
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error('monat'))

    def test_lookup_instance(self):
        """
        Assert that lookup_instance returns the expected number of results
        for a given row.
        """
        test_data = [
            ({'num': '2', 'jahr': '2000', 'lnum': '312', 'monat': '12'}, 0),
            ({'num': '1', 'jahr': '2000'}, 1),
            ({'num': '1', 'jahr': ['2000', '2001']}, 1),
            ({'num': '5', 'jahr': '2000'}, 2),
            ({'num': '5', 'jahr': ['2000', '2001']}, 2),
            ({'num': '5', 'jahrgang': '2'}, 2),
            ({'num': '5', 'jahrgang': '2', 'jahr': '2000'}, 2),
            ({'num': '5', 'jahrgang': '1'}, 0),
            ({'jahrgang': '2', 'num': '5', 'jahr': '2002'}, 0)
        ]
        form = self.form_class(data=self.valid_data)
        form.is_valid()
        for row_data, expected in test_data:
            with self.subTest(data=row_data):
                self.assertEqual(form.lookup_instance(row_data).count(), expected)

    def test_row_data_prop(self):
        """Verify that form.row_data contains the expected data."""
        form = self.form_class(data=self.valid_data)
        form.is_valid()

        row_template = {
            'magazin': self.mag,
            'jahrgang': 11,
            'jahr': ['2000', '2001'],
            'audio': True,
            'audio_lagerort': self.audio_lo,
            'ausgabe_lagerort': self.lo,
            'dublette': self.dublette,
            'provenienz': self.prov,
            'status': 'unb'
        }
        # valid_data contains 6 rows.
        # Prepare expected results for each of those rows:
        row_1 = row_template.copy()
        # The first row should add a dublette to self.updated:
        row_1.update(
            {'num': '1', 'ausgabe_lagerort': self.dublette, 'instance': self.updated}
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
        row_6.update(
            {
                'num': '5',
                'multiples': self.model.objects.filter(pk__in=[self.multi1.pk, self.multi2.pk])
            }
        )
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
                        sorted(list(row.pop('multiples').values_list('pk', flat=True))),
                        sorted(list(expected[c].pop('multiples').values_list('pk', flat=True)))
                    )
                self.assertEqual(row, expected[c])

    def test_row_data_form_invalid(self):
        """If the form is invalid, row_data should return empty."""
        form = self.form_class()
        self.assertEqual(form.row_data, [])

    def test_row_data_form_has_not_changed(self):
        """
        row_data should return the previously calculated _row_data, if the form
        has not changed and if _row_data is not empty.
        """
        form = self.form_class(data=self.valid_data)
        with patch.object(form, 'has_changed', new=Mock(return_value=False)):
            form._row_data = 'Not changed!'
            self.assertEqual(form.row_data, 'Not changed!')
            form._row_data = []
            self.assertNotEqual(form.row_data, 'Not changed!')

    def test_row_data_unknown_field(self):
        """
        Assert that a field that is not listed in either each_fields or
        split_fields is not included in row_data.
        """

        class TestForm(BulkFormAusgabe):
            unknown = BulkField()

        data = self.valid_data.copy()
        data['unknown'] = '9,8,7,6,5,5'
        form = TestForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertFalse(any('unknown' in row for row in form.row_data))

    @translation_override(language=None)
    def test_clean_monat_invalid(self):
        """Assert that clean_monat raises an error for invalid values for monat."""
        data = self.valid_data.copy()
        for invalid_value in ('0', '13'):
            with self.subTest(invalid_value=invalid_value):
                data['monat'] = invalid_value
                form = self.form_class(data=data)
                with self.assertRaises(ValidationError) as cm:
                    form.clean_monat()
                self.assertEqual(
                    cm.exception.args[0], 'Monat-Werte müssen zwischen 1 und 12 liegen.'
                )
