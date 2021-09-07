from itertools import chain

from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH

from dbentry import models as _models
from dbentry.ac import widgets as autocomplete_widgets
from dbentry.factory import make
from dbentry.fields import PartialDate, PartialDateFormField
from dbentry.search import forms as search_forms
from dbentry.tests.base import MyTestCase


class TestSearchFormFactory(MyTestCase):

    def setUp(self):
        super().setUp()
        self.factory = search_forms.SearchFormFactory()

    def test_formfield_for_dbfield_dal(self):
        # Assert that formfield_for_dbfield prepares an
        # autocomplete ready formfield for many to one relations.
        dbfield = _models.Ausgabe._meta.get_field('magazin')
        formfield = self.factory.formfield_for_dbfield(dbfield)
        widget = formfield.widget
        self.assertIsInstance(widget, autocomplete_widgets.MIZModelSelect2)
        self.assertEqual(widget.model_name, _models.Magazin._meta.model_name)
        msg = "Should not be allowed to create new records from inside a search form."
        self.assertFalse(widget.create_field, msg=msg)
        self.assertEqual(formfield.queryset.model, _models.Magazin)
        self.assertFalse(formfield.required)

    def test_formfield_for_dbfield_dal_m2m(self):
        # Assert that formfield_for_dbfield prepares an
        # autocomplete ready formfield for many to many relations.
        dbfield = _models.Artikel._meta.get_field('genre')
        formfield = self.factory.formfield_for_dbfield(dbfield)
        widget = formfield.widget
        self.assertIsInstance(widget, autocomplete_widgets.MIZModelSelect2Multiple)
        self.assertEqual(widget.model_name, _models.Genre._meta.model_name)
        msg = "Should not be allowed to create new records from inside a search form."
        self.assertFalse(widget.create_field, msg=msg)
        self.assertEqual(formfield.queryset.model, _models.Genre)
        self.assertFalse(formfield.required)

    def test_formfield_for_dbfield_dal_with_forward(self):
        # Assert that dal forwards are added.
        dbfield = _models.Ausgabe._meta.get_field('magazin')
        formfield = self.factory.formfield_for_dbfield(dbfield, forward=['ausgabe'])
        widget = formfield.widget
        self.assertIsInstance(widget, autocomplete_widgets.MIZModelSelect2)
        self.assertTrue(widget.forward)

    def test_get_search_form(self):
        # Assert that the form class is created only with proper fields/lookups.
        fields = [
            'seite__gt', 'seitenumfang', 'genre__genre', 'notafield',
            'schlagwort__notalookup'
        ]
        valid = ['seite', 'seitenumfang', 'genre__genre']
        invalid = ['notafield', 'schlagwort', 'schlagwort__notalookup']
        form_fields = self.factory(_models.Artikel, fields).base_fields
        for field_name in chain(valid, invalid):
            should_be_valid = field_name in valid
            with self.subTest(valid=should_be_valid, field_name=field_name):
                if should_be_valid:
                    self.assertIn(field_name, form_fields)
                else:
                    self.assertNotIn(field_name, form_fields)

    def test_takes_formfield_callback(self):
        # Assert that custom formfield_callback can be passed to the factory
        # and that it uses that to create formfields for dbfields.
        callback = lambda dbfield, **kwargs: forms.DateField(**kwargs)
        form_class = self.factory(
            model=_models.Artikel,
            formfield_callback=callback,
            fields=['seite']
        )
        self.assertIn('seite', form_class.base_fields)
        self.assertIsInstance(form_class.base_fields['seite'], forms.DateField)

    def test_takes_formfield_callback_callable(self):
        # A callback that is not a callable should raise a TypeError.
        with self.assertRaises(TypeError):
            self.factory(_models.Artikel, formfield_callback=1)

    def test_factory_forward(self):
        # Assert that 'forward' arguments to the factory are respected.
        form_class = self.factory(
            model=_models.Artikel,
            fields=['ausgabe'],
            forwards={'ausgabe': 'magazin'}
        )
        self.assertIn('ausgabe', form_class.base_fields)
        self.assertTrue(form_class.base_fields['ausgabe'].widget.forward)

    def test_factory_range_lookup(self):
        # Assert that the factory recognizes range lookups in a field's path
        # and creates a RangeFormField for it.
        form_class = self.factory(
            model=_models.Ausgabe,
            fields=['jahrgang__range'],
        )
        self.assertIn('jahrgang', form_class.base_fields)
        self.assertIsInstance(
            form_class.base_fields['jahrgang'],
            search_forms.RangeFormField
        )

    def test_formfield_for_dbfield_form_class(self):
        # Assert that test_formfield_for_dbfield respects the formfield class
        # provided in the kwargs.
        db_field = _models.Ausgabe._meta.get_field('jahrgang')
        self.assertIsInstance(
            self.factory.formfield_for_dbfield(db_field, form_class=forms.CharField),
            forms.CharField,
            msg="formfield_for_dbfield should respect a provided formfield "
                "class."
        )
        # Default formfield:
        self.assertIsInstance(
            self.factory.formfield_for_dbfield(db_field),
            forms.IntegerField
        )

    def test_formfield_for_dbfield_fallback_form_class(self):
        # Assert that formfield_for_dbfield falls back to a forms.CharField
        # formfield if no formfield instance was created.
        db_field = _models.Ausgabe._meta.get_field('id')
        self.assertIsInstance(
            self.factory.formfield_for_dbfield(db_field),
            forms.CharField
        )

    def test_formfield_choices(self):
        # Assert that the choice formfield includes an 'empty' choice even if
        # the model field's choices does not include one.
        db_field = _models.Ausgabe._meta.get_field('status')
        formfield = self.factory.formfield_for_dbfield(db_field)
        choices = formfield.choices
        self.assertIn(BLANK_CHOICE_DASH[0], choices)

    def test_factory_adds_pk_field(self):
        # Assert that the factory adds a search field for the primary key field.
        form_class = self.factory(
            model=_models.Ausgabe,
            fields=['magazin']
        )
        self.assertIn('id__in', form_class.base_fields)
        # Make sure that there is no extra lookup registered to this field.
        self.assertNotIn('id', form_class.lookups)
        self.assertNotIn('id__in', form_class.lookups)

        # The factory should not overwrite an explicit primary key search field.
        form_class = self.factory(
            model=_models.Ausgabe,
            fields=['magazin', 'id__in']
        )
        self.assertIn('id', form_class.base_fields)
        self.assertIn('id', form_class.lookups)
        self.assertEqual(form_class.lookups['id'], ['in'])


class TestSearchForm(MyTestCase):

    model = _models.Artikel

    def setUp(self):
        super().setUp()
        self.factory = search_forms.SearchFormFactory()

    def test_get_filters_params_returns_empty_on_invalid(self):
        # get_filters_params should shortcircuit if the form is invalid.
        form_class = self.factory(self.model)
        form = form_class()
        # Empty form without data => is_valid == False
        self.assertFalse(form.get_filters_params())

    def test_get_filters_params_skips_empty(self):
        # Assert that get_filters_params does not return empty query values.
        data = {
            'seite': 1,
            'ausgabe__magazin': make(_models.Magazin).pk,
            'musiker': []
        }
        form_class = self.factory(self.model, fields=data.keys())
        form = form_class(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertIn('seite', filter_params)
        self.assertIn('ausgabe__magazin', filter_params)
        self.assertNotIn('musiker__in', filter_params)

    def test_get_filters_params_boolean_false(self):
        # Assert that an unchecked BooleanField is not evaluated as False.
        form_class = self.factory(_models.Ausgabe, fields=['sonderausgabe'])
        form = form_class(data={})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertNotIn('sonderausgabe', filter_params)

    def test_get_filters_params_boolean_true(self):
        # Assert that an checked BooleanField is evaluated as True.
        form_class = self.factory(_models.Ausgabe, fields=['sonderausgabe'])
        form = form_class(data={'sonderausgabe': True})
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertIn('sonderausgabe', filter_params)
        self.assertEqual(filter_params['sonderausgabe'], True)

    def test_get_filters_params_range(self):
        # Check that get_filters_params handles range lookups correctly.
        form_class = self.factory(self.model, fields=['seite__range'])
        data = {'seite_0': '1', 'seite_1': '2'}
        form = form_class(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertIn('seite__range', filter_params)
        self.assertEqual(filter_params['seite__range'], [1, 2])

    def test_get_filters_params_range_skipped_when_empty(self):
        form_class = self.factory(self.model, fields=['seite__range'])
        data = {'seite__range_0': None, 'seite__range_1': None}
        form = form_class(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertFalse(filter_params)

    def test_get_filters_params_replaces_range_exact(self):
        # Assert that get_filters_params replaces a range query with a query
        # for exact when 'end' is 'empty'.
        form_class = self.factory(self.model, fields=['seite__range'])
        data = {'seite_0': '1', 'seite_1': None}
        form = form_class(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertNotIn('seite__range', filter_params)
        self.assertIn('seite', filter_params)

    def test_get_filters_params_replaces_range_lte(self):
        # Assert that get_filters_params replaces a range query with a query
        # for lte when 'start' is 'empty'.
        form_class = self.factory(self.model, fields=['seite__range'])
        data = {'seite_0': None, 'seite_1': '1'}
        form = form_class(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        filter_params = form.get_filters_params()
        self.assertNotIn('seite__range', filter_params)
        self.assertIn('seite__lte', filter_params)

    def test_get_filters_params(self):
        form_class = self.factory(_models.Plakat, fields=['datum'])
        form = form_class(data={'datum_0': 2020, 'datum_1': 5, 'datum_2': 20})
        self.assertTrue(form.is_valid())
        self.assertIn('datum', form.cleaned_data)
        expected = PartialDate(2020, 5, 20)
        self.assertEqual(form.cleaned_data['datum'], expected)
        self.assertEqual(form.get_filters_params(), {'datum': expected})

    def test_get_filters_params_in_lookup_with_qs(self):
        # Assert that get_filters_params creates a comma separated string of
        # values for the 'in' lookup with querysets.
        genre1 = make(_models.Genre, genre="genre1", pk=1)
        genre2 = make(_models.Genre, genre="genre2", pk=2)
        form_class = self.factory(_models.Plakat, fields=['genre'])
        form = form_class(data={'genre': [genre1.pk, genre2.pk]})
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertIn('genre', form.cleaned_data)
        self.assertEqual(list(form.cleaned_data['genre']), [genre1, genre2])
        self.assertEqual(form.get_filters_params(), {'genre__in': "1,2"})

    def test_clean_id__in(self):
        # Assert that clean_id__in filters out alphabetic characters.
        form_class = self.factory(self.model, fields=['id__in'])
        form = form_class()
        form.cleaned_data = {'id__in': 'A20'}
        self.assertEqual(form.clean_id__in(), '20')

    def test_clean_id__in_keeps_sep(self):
        # Assert that clean_id__in keeps the separator character.
        form_class = self.factory(self.model, fields=['id__in'])
        form = form_class()
        form.cleaned_data = {'id__in': '1,2'}
        self.assertEqual(form.clean_id__in(), '1,2')


class TestRangeFormField(MyTestCase):

    def test_get_initial(self):
        # Assert that get_initial recognizes that its subfields are
        # MultiValueFields and thus returns the compressed values.
        initial = {
            'datum_0_0': 2019, 'datum_0_1': 5, 'datum_0_2': 19,
            'datum_1_0': 2019, 'datum_1_1': 5, 'datum_1_2': 20
        }
        formfield = search_forms.RangeFormField(PartialDateFormField())
        expected = [PartialDate(2019, 5, 19), PartialDate(2019, 5, 20)]
        self.assertEqual(formfield.get_initial(initial, 'datum'), expected)
