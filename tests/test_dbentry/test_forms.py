from unittest.mock import patch

from dal import autocomplete
from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.utils.translation import override as translation_override

from dbentry import models as _models
from dbentry.admin.autocomplete.widgets import RemoteModelWidgetWrapper, TabularResultsMixin
from dbentry.forms import (ArtikelForm, AusgabeMagazinFieldForm, AutorForm, BuchForm, PersonForm)
from dbentry.validators import DNBURLValidator
from tests.case import ModelFormTestCase
from tests.model_factory import make


class TestAusgabeMagazinFieldForm(ModelFormTestCase):
    form_class = AusgabeMagazinFieldForm
    model = _models.Artikel
    fields = ['ausgabe']

    def test_init_initial_magazin(self):
        """Assert that init sets the initial value for ausgabe__magazin."""
        magazin = make(_models.Magazin)
        ausgabe = make(_models.Ausgabe, magazin=magazin)
        artikel = make(_models.Artikel, ausgabe=ausgabe)
        form = self.get_form(instance=artikel)
        self.assertEqual(form.initial.get('ausgabe__magazin'), magazin)

    def test_ausgabe_includes_forward(self):
        """
        Assert that the autocomplete widget for 'ausgabe' includes forwarding
        to 'ausgabe__magazin'.
        """
        form = self.get_form()
        widget = form.fields['ausgabe'].widget
        self.assertEqual(widget.forward[0].src, 'ausgabe__magazin')


class TestArtikelForm(ModelFormTestCase):
    form_class = ArtikelForm
    model = _models.Artikel
    fields = ['ausgabe', 'schlagzeile']

    def test_init_initial_magazin(self):
        """Assert that init sets the initial value for ausgabe__magazin."""
        # Yes: this is the same test method as in TestAusgabeMagazinFieldForm.
        # Setting the value for Magazin is very important to the function of
        # the ArtikelForm - so test this specifically for that form.
        magazin = make(_models.Magazin)
        ausgabe = make(_models.Ausgabe, magazin=magazin)
        artikel = make(_models.Artikel, ausgabe=ausgabe)
        form = self.get_form(instance=artikel)
        self.assertEqual(form.initial.get('ausgabe__magazin'), magazin)

    def test_form_widgets(self):
        form = self.get_form()

        self.assertIn('schlagzeile', form.fields)
        widget = form.fields['schlagzeile'].widget
        self.assertIsInstance(widget, forms.Textarea)
        self.assertEqual(widget.attrs['rows'], 2)
        self.assertEqual(widget.attrs['cols'], 90)

        self.assertIn('ausgabe', form.fields)
        self.assertIsInstance(form.fields['ausgabe'].widget, autocomplete.ModelSelect2)
        self.assertIsInstance(form.fields['ausgabe'].widget, TabularResultsMixin)
        self.assertIn('ausgabe__magazin', form.fields)
        self.assertIsInstance(form.fields['ausgabe__magazin'].widget, RemoteModelWidgetWrapper)


class TestAutorForm(ModelFormTestCase):
    form_class = AutorForm
    model = _models.Autor
    fields = ['person', 'kuerzel']

    @translation_override(language=None)
    def test_clean(self):
        """
        An error should be raised, if the user did not provide data for either
        of the two fields 'kuerzel' and 'person'.
        """
        p = make(_models.Person)
        expected_error_message = 'Bitte mindestens 1 dieser Felder ausfüllen: Kürzel, Person.'

        form = self.get_form(data={})
        form.full_clean()
        self.assertIn(expected_error_message, form.errors.get(forms.ALL_FIELDS))

        form = self.get_form(data={'kuerzel': 'Beep'})
        form.full_clean()
        self.assertFalse(form.errors)

        form = self.get_form(data={'person': p.pk})
        form.full_clean()
        self.assertFalse(form.errors)

        form = self.get_form(data={'kuerzel': 'Beep', 'person': p.pk})
        form.full_clean()
        self.assertFalse(form.errors)


class TestBuchForm(ModelFormTestCase):
    form_class = BuchForm
    fields = ['is_buchband', 'buchband']
    model = _models.Buch

    @translation_override(language=None)
    def test_clean(self):
        """
        An error should be raised, if the user filled out both the 'is_buchband'
        and the 'buchband' field.
        """
        b = make(_models.Buch, is_buchband=True)
        expected_error_message = 'Ein Buchband kann nicht selber Teil eines Buchbandes sein.'

        form = self.get_form(data={'is_buchband': True, 'buchband': b.pk})
        form.full_clean()
        self.assertIn(expected_error_message, form.errors.get(forms.ALL_FIELDS))

        form = self.get_form(data={'is_buchband': True})
        form.full_clean()
        self.assertFalse(form.errors)

        form = self.get_form(data={'buchband': b.pk})
        form.full_clean()
        self.assertFalse(form.errors)

        form = self.get_form(data={})
        form.full_clean()
        self.assertFalse(form.errors)

    def test_is_buchband_to_false(self):
        """
        The form should not allow setting 'is_buchband' to False on a Buch
        instance which is still referenced by other Buch instances.
        """
        buchband = make(self.model, titel='Der Buchband', is_buchband=True)
        related = make(self.model, titel='Der Aufsatz', buchband=buchband)
        form = self.get_form(instance=buchband, data={'is_buchband': False})
        # self.assertFalse(form.is_valid())
        form.full_clean()
        self.assertEqual(
            form.errors['is_buchband'],
            ["Nicht abwählbar für Buchband mit existierenden Aufsätzen."]
        )
        # Delete the instance that references buchband. It should now be
        # possible to set 'is_buchband' to False.
        related.delete()
        form = self.get_form(instance=buchband, data={'is_buchband': False})
        self.assertTrue(form.is_valid())


@patch('dbentry.forms.searchgnd', return_value=([('1234', 'Robert Plant')], 1))
class TestPersonForm(ModelFormTestCase):
    form_class = PersonForm
    model = _models.Person
    fields = ['nachname', 'gnd_id', 'gnd_name', 'dnb_url']

    def test_clean_id_and_url_empty(self, searchgnd_mock):
        """Assert that both fields 'gnd_id' and 'dnb_url' can be left empty."""
        form = self.get_form(data={'nachname': 'Plant'})
        form.full_clean()
        self.assertFalse(form.errors)
        # If either of the fields are empty, clean should not attempt a search.
        searchgnd_mock.assert_not_called()

    @translation_override(language=None)
    def test_clean_raises_error_no_match_id_and_url(self, _searchgnd_mock):
        """
        Assert that clean raises a ValidationError when gnd_id and the gnd_id
        given in dnb_url don't match.
        """
        form = self.get_form(data={'gnd_id': '1234', 'dnb_url': 'http://d-nb.info/gnd/11863996X'})
        form.full_clean()
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        expected_error_message = (
            "Die angegebene GND ID (1234) stimmt nicht mit der ID im DNB"
            " Link überein (11863996X)."
        )
        self.assertIn(expected_error_message, form.errors[NON_FIELD_ERRORS])

    def test_clean_sets_id_from_url(self, _searchgnd_mock):
        """
        Assert that clean sets the correct gnd_id from a given valid url, if a
        gnd_id was missing.
        """
        form = self.get_form(
            data={'dnb_url': 'http://d-nb.info/gnd/11863996X', 'nachname': 'Plant'}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('gnd_id', form.cleaned_data)
        self.assertEqual(form.cleaned_data['gnd_id'], '11863996X')

    def test_clean_sets_id_from_url_when_id_removed(self, _searchgnd_mock):
        """
        Assert that clean sets the correct gnd_id from a given valid url, if the
        initial value for the id was removed from the form.
        """
        form = self.get_form(
            data={
                'dnb_url': 'http://d-nb.info/gnd/11863996X',
                'nachname': 'Plant',
            },
            initial={
                'gnd_id': '1234',
                'dnb_url': 'http://d-nb.info/gnd/1234',
                'nachname': 'Plant'
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('gnd_id', form.cleaned_data)
        self.assertEqual(form.cleaned_data['gnd_id'], '11863996X')

    def test_clean_sets_gnd_id_from_url_when_url_changes(self, _searchgnd_mock):
        """
        Assert that clean sets the correct gnd_id from a given valid url, if
        the 'dnb_url' was changed, but 'gnd_id' was not.
        """
        form = self.get_form(
            data={
                'gnd_id': '1234',
                'dnb_url': 'http://d-nb.info/gnd/11863996X',
                'nachname': 'Plant'
            },
            initial={
                'gnd_id': '1234',
                'dnb_url': 'http://d-nb.info/gnd/1234',
                'nachname': 'Plant'
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('dnb_url', form.changed_data)
        self.assertNotIn('gnd_id', form.changed_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('gnd_id', form.cleaned_data)
        self.assertEqual(form.cleaned_data['gnd_id'], '11863996X')

    def test_clean_sets_url_from_gnd_id_when_url_missing(self, _searchgnd_mock):
        """
        Assert that clean creates the correct url from a given valid gnd_id if
        a URL was missing.
        """
        form = self.get_form(data={'gnd_id': '11863996X', 'nachname': 'Plant'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('dnb_url', form.cleaned_data)
        self.assertEqual(
            form.cleaned_data['dnb_url'],
            'http://d-nb.info/gnd/11863996X'
        )

    def test_clean_sets_url_from_gnd_id_when_gnd_id_changes(self, _searchgnd_mock):
        """
        Assert that clean updates the url from a given valid gnd_id if 'gnd_id'
        was changed, but the URL was not.
        """
        form = self.get_form(
            data={
                'gnd_id': '11863996X',
                'dnb_url': 'http://d-nb.info/gnd/1234',
                'nachname': 'Plant'
            },
            initial={
                'gnd_id': '1234',
                'dnb_url': 'http://d-nb.info/gnd/1234',
                'nachname': 'Plant'
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('gnd_id', form.changed_data)
        self.assertNotIn('dnb_url', form.changed_data)
        self.assertIn('dnb_url', form.cleaned_data)
        self.assertEqual(
            form.cleaned_data['dnb_url'],
            'http://d-nb.info/gnd/11863996X'
        )

    @translation_override(language=None)
    def test_invalid_urls(self, _searchgnd_mock):
        """Assert that invalid URLs produce the expected error messages."""
        form = self.get_form(data={'nachname': 'Plant', 'dnb_url': 'notavalidurl'})
        self.assertIn('dnb_url', form.errors)
        # Default URL validator error message:
        self.assertIn('Enter a valid URL.', form.errors['dnb_url'])
        # DNBURLValidator error message:
        self.assertIn(
            "Bitte nur Adressen der DNB eingeben (d-nb.info oder portal.dnb.de).",
            form.errors['dnb_url']
        )

    def test_valid_urls(self, _searchgnd_mock):
        """Assert that valid urls will be reformatted to a uniform format."""
        urls = [
            'http://d-nb.info/gnd/11863996X',
            'https://d-nb.info/gnd/11863996X',
            'https://portal.dnb.de/opac.htm?method=simpleSearch&cqlMode=true&query=nid%3D11863996X',
        ]
        for url in urls:
            form = self.get_form(data={'nachname': 'Plant', 'dnb_url': url})
            with self.subTest(url=url):
                self.assertTrue(form.is_valid(), form.errors)
                self.assertIn('dnb_url', form.cleaned_data)
                self.assertEqual(
                    form.cleaned_data['dnb_url'],
                    'http://d-nb.info/gnd/11863996X',
                )

    @translation_override(language=None)
    def test_clean_validates_gnd_id(self, searchgnd_mock):
        """Assert that clean validates the gnd_id via an SRU request."""
        # An SRU query with an invalid gnd_id would return no results.
        searchgnd_mock.return_value = ([], 0)
        form = self.get_form(data={'gnd_id': 'invalid'})
        form.full_clean()
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        self.assertIn("Die GND ID ist ungültig.", form.errors[NON_FIELD_ERRORS])

    def test_clean_saves_preferred_name(self, _searchgnd_mock):
        """Assert that clean saves the 'preferred name' (RDFxml) of the result."""
        form = self.get_form(data={'gnd_id': '1234', 'nachname': 'Plant'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIn('gnd_name', form.cleaned_data)
        self.assertEqual((form.cleaned_data['gnd_name']), 'Robert Plant')

    def test_save(self, _searchgnd_mock):
        """Assert that gnd_id and gnd_name are saved to the form's model instance."""
        form = self.get_form(data={'nachname': 'Plant', 'gnd_id': '1234'})
        self.assertTrue(form.is_valid(), form.errors)
        plant = form.save()
        self.assertEqual(plant.nachname, 'Plant')
        self.assertEqual(plant.gnd_id, '1234')
        self.assertEqual(plant.gnd_name, 'Robert Plant')

    def test_init_adds_url_validator(self, _searchgnd_mock):
        """
        Assert that the DNBURLValidator is added to the list of validators of
        the 'dnb_url' field.
        """
        form = self.get_form()
        self.assertTrue(
            any(isinstance(v, DNBURLValidator) for v in form.fields['dnb_url'].validators)
        )

    def test_init_sets_gnd_id_initial_choice(self, _searchgnd_mock):
        """Assert that init sets the initial choice of the 'gnd_id' field."""
        obj = make(
            self.model, vorname='Robert', nachname='Plant',
            gnd_id='1234', gnd_name='Plant, Robert'
        )
        form = self.get_form(instance=obj)
        self.assertEqual(
            form.fields['gnd_id'].widget.choices,
            [('1234', 'Plant, Robert')]
        )
