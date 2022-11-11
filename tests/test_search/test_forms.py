from itertools import chain
from unittest.mock import Mock, patch

from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH
from django.test import TestCase

from dbentry import models as _models
from dbentry.fields import PartialDate, PartialDateFormField
from dbentry.search.forms import RangeFormField, RangeWidget, SearchFormFactory
from tests.factory import make
from .models import Artikel, Ausgabe, Genre, InheritedPKModel, Magazin


class TestRangeWidget(TestCase):

    def test_init_duplicates_widget(self):
        """
        Assert that init duplicates the given widget instance for the
        MultiWidget constructor.
        """
        widget = forms.TextInput()
        with patch('django.forms.MultiWidget.__init__') as super_mock:
            RangeWidget(widget=widget)
        self.assertTrue(super_mock.called)
        _args, kwargs = super_mock.call_args
        self.assertIn('widgets', kwargs)
        self.assertEqual(kwargs['widgets'], [widget] * 2)


class TestRangeFormField(TestCase):

    def test_init_duplicates_formfield(self):
        """
        Assert that init duplicates the given formfield instance for the
        MultiValueField constructor.
        """
        field = forms.CharField()
        with patch('django.forms.MultiValueField.__init__') as super_mock:
            RangeFormField(formfield=field)
        self.assertTrue(super_mock.called)
        _args, kwargs = super_mock.call_args
        self.assertIn('fields', kwargs)
        self.assertEqual(kwargs['fields'], [field] * 2)

    def test_init_formfield_widget_to_range_widget(self):
        """Assert that init creates a RangeWidget if no widget kwarg was provided."""
        widget = forms.DateInput()
        with patch('django.forms.MultiValueField.__init__') as super_mock:
            for widget_kwarg in (None, RangeWidget(widget)):
                with self.subTest(widget=widget_kwarg):
                    RangeFormField(formfield=forms.CharField(), widget=widget_kwarg)
                    self.assertTrue(super_mock.called)
                    _args, kwargs = super_mock.call_args
                    self.assertIn('widget', kwargs)
                    self.assertIsInstance(kwargs['widget'], RangeWidget)
                    if widget_kwarg:
                        self.assertEqual(kwargs['widget'].widgets, [widget] * 2)

    def test_get_initial(self):
        """Assert that get_initial returns the correct data."""
        initial = {'seite_0': 10, 'seite_1': 20, 'foo_0': 'bar'}
        formfield = RangeFormField(formfield=forms.IntegerField())
        self.assertEqual(formfield.get_initial(initial, 'seite'), [10, 20])

    def test_get_initial_multi_value_fields(self):
        """
        Assert that get_initial returns the compressed values if its subfields
        are MultiValueFields.
        """

        class W(forms.MultiWidget):
            def __init__(self):
                super().__init__(widgets=[forms.NumberInput()] * 3)

        class F(forms.MultiValueField):

            def __init__(self):
                super().__init__(
                    fields=[forms.IntegerField(required=False)] * 3,
                    widget=W()
                )

            def compress(self, data_list):
                if not data_list:
                    return [None] * 3
                return "-".join(str(v).zfill(2) for v in data_list)

        initial = {
            'datum_0_0': 2019, 'datum_0_1': 5, 'datum_0_2': 19,
            'datum_1_0': 2019, 'datum_1_1': 5, 'datum_1_2': 20
        }
        formfield = RangeFormField(formfield=F())
        self.assertEqual(
            formfield.get_initial(initial, 'datum'),
            ["2019-05-19", "2019-05-20"]
        )

    def test_compress(self):
        formfield = RangeFormField(formfield=forms.IntegerField())
        for test_data in (None, [], [10, 20]):
            with self.subTest(data_list=test_data):
                expected = [None, None]
                if test_data:
                    expected = [10, 20]
                self.assertEqual(formfield.compress(test_data), expected)


class TestSearchFormFactory(TestCase):

    def setUp(self):
        super().setUp()
        self.factory = SearchFormFactory()

    @patch("dbentry.search.forms.make_widget")
    def test_formfield_for_dbfield_dal(self, make_widget_mock):
        """
        Assert that formfield_for_dbfield attempts to create a dal widget for
        many-to-one relations.
        """
        dbfield = Ausgabe._meta.get_field('magazin')
        self.factory.formfield_for_dbfield(dbfield)
        make_widget_mock.assert_called()
        _args, kwargs = make_widget_mock.call_args
        self.assertEqual(kwargs['model'], Magazin)
        self.assertEqual(kwargs['multiple'], False)
        self.assertEqual(kwargs['wrap'], False)
        self.assertEqual(kwargs['can_add_related'], False)
        self.assertEqual(kwargs['tabular'], False)

    @patch("dbentry.search.forms.make_widget")
    def test_formfield_for_dbfield_dal_m2m(self, make_widget_mock):
        """
        Assert that formfield_for_dbfield attempts to create a dal widget for
        many-to-many relations.
        """
        dbfield = Artikel._meta.get_field('genre')
        self.factory.formfield_for_dbfield(dbfield)
        make_widget_mock.assert_called()
        _args, kwargs = make_widget_mock.call_args
        self.assertEqual(kwargs['model'], Genre)
        self.assertEqual(kwargs['multiple'], True)
        self.assertEqual(kwargs['wrap'], False)
        self.assertEqual(kwargs['can_add_related'], False)
        self.assertEqual(kwargs['tabular'], False)

    @patch("dbentry.search.forms.make_widget")
    def test_formfield_for_dbfield_dal_with_forward(self, make_widget_mock):
        """Assert that forwarding declared for dal widgets is respected."""
        dbfield = Ausgabe._meta.get_field('magazin')
        self.factory.formfield_for_dbfield(dbfield, forward=['ausgabe'])
        make_widget_mock.assert_called()
        _args, kwargs = make_widget_mock.call_args
        self.assertIn('forward', kwargs)
        self.assertEqual(kwargs['forward'], ['ausgabe'])

    def test_formfield_for_dbfield_form_class(self):
        """
        Assert that test_formfield_for_dbfield respects the formfield class
        provided in the kwargs.
        """
        db_field = Ausgabe._meta.get_field('e_datum')
        self.assertIsInstance(
            self.factory.formfield_for_dbfield(db_field, form_class=forms.CharField),
            forms.CharField,
        )

    def test_formfield_for_dbfield_fallback_form_class(self):
        """
        Assert that formfield_for_dbfield creates a CharField formfield for
        fields that do not provide a formfield (such as AutoFields).
        """
        db_field = Ausgabe._meta.get_field('id')
        self.assertIsInstance(
            self.factory.formfield_for_dbfield(db_field),
            forms.CharField
        )

    def test_formfield_for_dbfield_adds_empty_choice(self):
        """
        Assert that formfield_for_dbfield adds an 'empty' choice for formfields
        with choices.
        """
        db_field = Ausgabe._meta.get_field('status')
        formfield = self.factory.formfield_for_dbfield(db_field)
        self.assertIn(BLANK_CHOICE_DASH[0], formfield.choices)

    def test_get_search_form_ignores_invalid_fields(self):
        """Assert that get_search_form ignores invalid fields/lookups."""
        fields = [
            'seite__gt', 'schlagzeile', 'genre__genre', 'notafield',
            'ausgabe__notalookup'
        ]
        valid = ['seite', 'schlagzeile', 'genre__genre']
        invalid = ['notafield', 'ausgabe', 'ausgabe__notalookup']
        form_fields = self.factory.get_search_form(Artikel, fields).base_fields
        for field_name in chain(valid, invalid):
            should_be_valid = field_name in valid
            with self.subTest(valid=should_be_valid, field_name=field_name):
                if should_be_valid:
                    self.assertIn(field_name, form_fields)
                else:
                    self.assertNotIn(field_name, form_fields)

    def test_get_search_form_takes_formfield_callback(self):
        """
        Assert that custom formfield_callback can be passed to the factory
        and that it uses that callback to create formfields for db fields.
        """

        def callback(_dbfield, **kwargs):
            return forms.DateField(**kwargs)

        form_class = self.factory.get_search_form(
            model=Artikel, formfield_callback=callback, fields=['seite']
        )
        self.assertIn('seite', form_class.base_fields)
        self.assertIsInstance(form_class.base_fields['seite'], forms.DateField)

    def test_get_search_form_callback_not_callable(self):
        """Assert that an exception is raised if the callback that is not callable."""
        with self.assertRaises(TypeError):
            self.factory(_models.Artikel, formfield_callback=1)

    def test_get_search_form_formfield_kwargs(self):
        """Assert that get_search_form passes on kwargs for the formfield."""
        callback = Mock(return_value=forms.CharField())
        formfield_kwargs = {
            'widgets': {'seite': forms.TextInput},
            'localized_fields': ['seite'],
            'labels': {'seite': 'Seiten'},
            'help_texts': {'seite': 'Please enter a page number.'},
            'error_messages': {'seite': 'You did not enter a page number.'},
            'field_classes': {'seite': forms.CharField},
            'forwards': {'seite': 'Forward.'},
            'tabular': {'seite': True},
        }
        # Have the factory process the PK field 'id' before 'seite, so that
        # callback.call_args returns the kwargs for 'seite'.
        self.factory.get_search_form(
            model=Artikel, formfield_callback=callback, fields=['id', 'seite'],
            **formfield_kwargs,
        )
        callback.assert_called()
        _args, kwargs = callback.call_args
        self.assertIn('widget', kwargs)
        self.assertEqual(kwargs['widget'], forms.TextInput)
        self.assertEqual(kwargs['localize'], True)
        self.assertEqual(kwargs['label'], 'Seiten')
        self.assertEqual(kwargs['help_text'], 'Please enter a page number.')
        self.assertEqual(kwargs['error_messages'], 'You did not enter a page number.')
        self.assertEqual(kwargs['form_class'], forms.CharField)
        self.assertEqual(kwargs['forward'], 'Forward.')
        self.assertEqual(kwargs['tabular'], True)

    def test_get_search_form_range_lookup(self):
        """
        Assert that get_search_form recognizes range lookups in a field's path
        and creates a RangeFormField for it.
        """
        form_class = self.factory.get_search_form(model=Artikel, fields=['seite__range'])
        self.assertIn('seite', form_class.base_fields)
        self.assertIsInstance(form_class.base_fields['seite'], RangeFormField)

    def test_get_search_form_adds_pk_field(self):
        """Assert that get_search_form adds a search field for the primary key field."""
        form_class = self.factory(model=Artikel, fields=['seite'])
        self.assertIn('id__in', form_class.base_fields)
        # Make sure that there no extra lookups were registered with this field,
        # as the lookup is included in the name of the formfield.
        self.assertNotIn('id', form_class.lookups)
        self.assertNotIn('id__in', form_class.lookups)

        # The factory should not overwrite an explicit primary key search field.
        form_class = self.factory(model=Artikel, fields=['seite', 'id__in'])
        self.assertIn('id', form_class.base_fields)
        self.assertIn('id', form_class.lookups)
        self.assertEqual(form_class.lookups['id'], ['in'])

    def test_get_search_form_relational_pk_field(self):
        """
        Assert that get_search_form can handle relational primary key fields
        (i.e. from multi-table inheritance) and creates a search field based on
        the parent's primary key field.
        """
        form_class = self.factory(model=InheritedPKModel, fields=[])
        self.assertIn('id__in', form_class.base_fields)
        field = form_class.base_fields['id__in']
        # Should be the fallback CharField, since the db field is a parent_link
        # and formfield() will return None.
        self.assertIsInstance(field, forms.CharField)
        # Should be the CharField's default widget, instead of some select
        # widget created for the relational field.
        self.assertNotIsInstance(form_class.base_fields['id__in'].widget, forms.Select)
        self.assertIsInstance(form_class.base_fields['id__in'].widget, forms.TextInput)


class TestSearchForm(TestCase):
    model = Artikel

    def setUp(self):
        super().setUp()
        self.factory = SearchFormFactory()

    def test_media_js(self):
        media = self.factory(self.model)().media
        expected = [
            'admin/js/vendor/jquery/jquery.min.js',
            'admin/js/jquery.init.js',
            'admin/js/remove_empty_fields.js',
            'admin/js/collapse.js'
        ]
        for js in expected:
            with self.subTest(js=js):
                self.assertIn(js, media._js)

    def test_media_css(self):
        media = self.factory(self.model)().media
        for css in ('admin/css/forms.css', 'admin/css/search_form.css'):
            with self.subTest(css=css):
                self.assertIn(css, media._css['all'])

    def test_get_filters_params_invalid_form(self):
        """Assert that get_filters_params returns early if the form is invalid."""
        form_class = self.factory(self.model, fields=['seite', 'ausgabe'])
        form = form_class(data={'seite': '1', 'ausgabe': 'NOPE'})
        self.assertFalse(form.is_valid())
        self.assertFalse(form.get_filters_params())

    def test_get_filters_params_ignores_empty_values(self):
        """Assert that get_filters_params does not return empty query values."""
        data = {
            'seite': 1,
            'ausgabe__magazin': make(Magazin).pk,
            'genre': []
        }
        form_class = self.factory(self.model, fields=data.keys())
        form = form_class(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertIn('seite', filter_params)
        self.assertIn('ausgabe__magazin', filter_params)
        self.assertNotIn('genre__in', filter_params)

    def test_get_filters_params_boolean_false(self):
        """Assert that an unchecked BooleanField is not evaluated as False."""
        form_class = self.factory(_models.Ausgabe, fields=['sonderausgabe'])
        form = form_class(data={})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertNotIn('sonderausgabe', filter_params)

    def test_get_filters_params_boolean_true(self):
        """Assert that a checked BooleanField is evaluated as True."""
        form_class = self.factory(_models.Ausgabe, fields=['sonderausgabe'])
        form = form_class(data={'sonderausgabe': True})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertIn('sonderausgabe', filter_params)
        self.assertEqual(filter_params['sonderausgabe'], True)

    def test_get_filters_params_range(self):
        """Assert that get_filters_params handles range lookups correctly."""
        form_class = self.factory(self.model, fields=['seite__range'])
        form = form_class(data={'seite_0': '1', 'seite_1': '2'})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertIn('seite__range', filter_params)
        self.assertEqual(filter_params['seite__range'], [1, 2])

    def test_get_filters_params_range_skipped_when_empty(self):
        """Assert that empty values for range lookups are ignored."""
        form_class = self.factory(self.model, fields=['seite__range'])
        form = form_class(data={'seite__range_0': None, 'seite__range_1': None})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertFalse(filter_params)

    def test_get_filters_params_range_no_end(self):
        """
        Assert that get_filters_params replaces a range lookup with an 'exact'
        lookup when the range's end value is empty.
        """
        form_class = self.factory(self.model, fields=['seite__range'])
        form = form_class(data={'seite_0': '1', 'seite_1': None})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertNotIn('seite__range', filter_params)
        self.assertIn('seite', filter_params)
        self.assertEqual(filter_params['seite'], 1)

    def test_get_filters_params_range_no_start(self):
        """
        Assert that get_filters_params replaces a range lookup with a 'lte'
        lookup when the range's start value is empty.
        """
        form_class = self.factory(self.model, fields=['seite__range'])
        data = {'seite_0': None, 'seite_1': '1'}
        form = form_class(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertNotIn('seite__range', filter_params)
        self.assertIn('seite__lte', filter_params)
        self.assertEqual(filter_params['seite__lte'], 1)

    def test_get_filters_params_range_partial_date(self):
        """
        Assert that get_filters_params returns the correct parameters for a
        range lookup with PartialDate objects.
        """
        form_class = self.factory(
            Ausgabe, fields=['e_datum__range'],
            field_classes={'e_datum__range': PartialDateFormField},
        )
        form = form_class(
            data={
                'e_datum_0_0': 2020, 'e_datum_0_1': 5, 'e_datum_0_2': 20,
                'e_datum_1_0': 2020, 'e_datum_1_1': 5, 'e_datum_1_2': 21,
            }
        )
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertIn('e_datum__range', filter_params)
        self.assertEqual(
            filter_params['e_datum__range'],
            [PartialDate(2020, 5, 20), PartialDate(2020, 5, 21)]
        )

    def test_get_filters_params_range_no_end_partial_date(self):
        """
        Assert that get_filters_params replaces a range lookup on PartialDate
        objects with a 'contains' lookup the range's end value is empty.
        """
        form_class = self.factory(
            Ausgabe, fields=['e_datum__range'],
            field_classes={'e_datum__range': PartialDateFormField},
        )
        form = form_class(data={'e_datum_0_0': 2020, 'e_datum_0_1': 5, 'e_datum_0_2': 20})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertNotIn('e_datum__range', filter_params)
        self.assertIn('e_datum__contains', filter_params)

    def test_get_filters_params_comma_separated_values_for_relations(self):
        """
        Assert that get_filters_params creates a string of comma separated
        values for the 'in' lookup on a relation, as expected by django admin.
        """
        genres = [make(Genre, genre="genre1"), make(Genre, genre="genre2")]
        pks = [o.pk for o in genres]
        form_class = self.factory(Artikel, fields=['genre'])
        form = form_class(data={'genre': pks})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertEqual(filter_params['genre__in'], f"{pks[0]},{pks[1]}")

    def test_clean_id__in(self):
        """Assert that clean_id__in filters out alphabetic characters."""
        form_class = self.factory(self.model, fields=['id__in'])
        form = form_class()
        form.cleaned_data = {'id__in': 'A20'}
        self.assertEqual(form.clean_id__in(), '20')

    def test_clean_id__in_keeps_sep(self):
        """Assert that clean_id__in doesn't remove the value separator (i.e. comma)."""
        form_class = self.factory(self.model, fields=['id__in'])
        form = form_class()
        form.cleaned_data = {'id__in': '1,2'}
        self.assertEqual(form.clean_id__in(), '1,2')
