from .base import FormTestCase, ModelFormTestCase, MyTestCase
from .mixins import TestDataMixin

from django import forms
from django.contrib.admin.helpers import Fieldset
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.utils.translation import override as translation_override

from DBentry import models as _models
from DBentry.base.forms import (
    DynamicChoiceFormMixin, MIZAdminForm, MinMaxRequiredFormMixin,
    MIZAdminInlineFormBase
)
from DBentry.forms import (
    AusgabeMagazinFieldForm, ArtikelForm, AutorForm, BuchForm, AudioForm
)
from DBentry.ac.widgets import EasyWidgetWrapper
from DBentry.factory import make

from dal import autocomplete


class TestAusgabeMagazinFieldForm(ModelFormTestCase):

    form_class = AusgabeMagazinFieldForm
    model = _models.Ausgabe.audio.through
    fields = ['ausgabe']
    test_data_count = 1

    def test_init_initial_magazin(self):
        # test if initial for ausgabe.magazin is set properly during init
        kwargs = {'instance': self.obj1}
        form = self.get_form(**kwargs)
        self.assertEqual(form.instance, self.obj1)
        self.assertEqual(form.initial.get('ausgabe__magazin'), self.obj1.ausgabe.magazin)

    def test_form_widgets(self):
        form = self.get_form()
        self.assertTrue('ausgabe' in form.fields)
        self.assertIsInstance(form.fields['ausgabe'].widget, autocomplete.ModelSelect2)
        self.assertTrue('ausgabe__magazin' in form.fields)
        self.assertIsInstance(form.fields['ausgabe__magazin'].widget, EasyWidgetWrapper)


class TestArtikelForm(ModelFormTestCase):

    form_class = ArtikelForm
    model = _models.Artikel
    fields = ['ausgabe', 'schlagzeile', 'zusammenfassung', 'beschreibung', 'bemerkungen']
    test_data_count = 1

    def test_init_initial_magazin(self):
        # test if initial for ausgabe.magazin is set properly during init
        kwargs = {'instance': self.obj1}
        form = self.get_form(**kwargs)
        self.assertEqual(form.instance, self.obj1)
        self.assertEqual(form.initial.get('ausgabe__magazin'), self.obj1.ausgabe.magazin)

    def test_form_widgets(self):
        form = self.get_form()

        self.assertTrue('schlagzeile' in form.fields)
        w = form.fields['schlagzeile'].widget
        self.assertIsInstance(w, forms.Textarea)
        self.assertEqual(w.attrs['rows'], 2)
        self.assertEqual(w.attrs['cols'], 90)

        self.assertTrue('zusammenfassung' in form.fields)
        self.assertIsInstance(form.fields['zusammenfassung'].widget, forms.Textarea)
        self.assertTrue('beschreibung' in form.fields)
        self.assertIsInstance(form.fields['beschreibung'].widget, forms.Textarea)
        self.assertTrue('bemerkungen' in form.fields)
        self.assertIsInstance(form.fields['bemerkungen'].widget, forms.Textarea)
        self.assertTrue('ausgabe' in form.fields)
        self.assertIsInstance(form.fields['ausgabe'].widget, autocomplete.ModelSelect2)
        self.assertTrue('ausgabe__magazin' in form.fields)
        self.assertIsInstance(form.fields['ausgabe__magazin'].widget, EasyWidgetWrapper)


class TestAutorForm(ModelFormTestCase):
    form_class = AutorForm
    fields = ['person', 'kuerzel']
    model = _models.Autor

    @translation_override(language=None)
    def test_clean(self):
        # clean should raise a ValidationError if either kuerzel or person data is missing
        p = make(_models.Person)
        expected_error_message = 'Bitte mindestens 1 dieser Felder ausfüllen: Kürzel, Person.'

        form = self.get_form(data={'beschreibung': 'Boop'})
        form.full_clean()
        self.assertIn(expected_error_message, form.errors.get('__all__'))

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
        # clean should raise a ValidationError if both is_buchband and buchband
        # data is present.
        b = make(_models.Buch, is_buchband=True)
        expected_error_message = 'Ein Buchband kann nicht selber Teil eines Buchbandes sein.'

        form = self.get_form(data={'is_buchband': True, 'buchband': b.pk})
        form.full_clean()
        self.assertIn(expected_error_message, form.errors.get('__all__'))

        form = self.get_form(data={'is_buchband': True})
        form.full_clean()
        self.assertFalse(form.errors)

        form = self.get_form(data={'buchband': b.pk})
        form.full_clean()
        self.assertFalse(form.errors)

        form = self.get_form(data={})
        form.full_clean()
        self.assertFalse(form.errors)


class TestMIZAdminForm(FormTestCase):

    dummy_attrs = {
        'some_int': forms.IntegerField(),
        'wrap_me': forms.CharField(widget=autocomplete.ModelSelect2(url='acmagazin')),
    }
    dummy_bases = (MIZAdminForm, )

    def test_iter(self):
        form = self.get_dummy_form()
        for fs in form:
            self.assertIsInstance(fs, Fieldset)

    def test_media_prop(self):
        # Make sure jquery is loaded in the right order:
        # jquery > jquery.init > whatever requires jquery
        from django.conf import settings
        media = self.get_dummy_form().media
        extra = '' if settings.DEBUG else '.min'
        # The jquery base must always be loaded first
        self.assertIn('admin/js/vendor/jquery/jquery%s.js' % extra, media._js)
        self.assertEqual(media._js.index('admin/js/vendor/jquery/jquery%s.js' % extra), 0)
        self.assertIn('admin/js/jquery.init.js', media._js)
        self.assertEqual(media._js.index('admin/js/jquery.init.js'), 1)

    def test_changed_data_prop_no_change(self):
        kwargs = dict(data=dict(some_int='10'), initial=dict(some_int='10'))
        form = self.get_dummy_form(**kwargs)
        self.assertFalse(form.changed_data)

    def test_changed_data_prop_change(self):
        kwargs = dict(data=dict(some_int='11'), initial=dict(some_int='10'))
        form = self.get_dummy_form(**kwargs)
        self.assertTrue(form.changed_data)


class TestDynamicChoiceForm(TestDataMixin, FormTestCase):

    dummy_bases = (DynamicChoiceFormMixin, forms.Form)
    dummy_attrs = {
        'cf': forms.ChoiceField(choices=[]),
        'cf2': forms.ChoiceField(choices=[])
    }
    model = _models.Genre
    raw_data = [{'genre': 'Very Last'}, {'genre': 'First'}, {'genre': 'Middle'}]

    def test_set_choices(self):
        # choices is list of iterables with len == 2 - ideal case
        choices = {forms.ALL_FIELDS: [('1', '1'), ('2', '3'), ('3', '0')]}
        expected = [('1', '1'), ('2', '3'), ('3', '0')]
        form = self.get_dummy_form(choices=choices)
        self.assertEqual(form.fields['cf'].choices, expected)
        self.assertEqual(form.fields['cf2'].choices, expected)

    def test_set_choices_manager(self):
        # choices is a BaseManager
        choices = {forms.ALL_FIELDS: _models.Genre.objects}
        expected = [
            (str(o.pk), str(o))
            for o in [self.obj2, self.obj3, self.obj1]
        ]
        form = self.get_dummy_form(choices=choices)
        self.assertEqual(form.fields['cf'].choices, expected)
        self.assertEqual(form.fields['cf2'].choices, expected)

    def test_set_choices_queryset(self):
        # choices is a QuerySet
        choices = {forms.ALL_FIELDS: _models.Genre.objects.all()}
        expected = [
            (str(o.pk), str(o))
            for o in [self.obj2, self.obj3, self.obj1]
        ]
        form = self.get_dummy_form(choices=choices)
        self.assertEqual(form.fields['cf'].choices, expected)
        self.assertEqual(form.fields['cf2'].choices, expected)

    def test_set_choices_preserved(self):
        # preset choices are preserved
        fields = {
            'cf': forms.ChoiceField(choices=[]),
            'cf2': forms.ChoiceField(choices=[('1', 'a')])
        }
        choices = {forms.ALL_FIELDS: [(i, i) for i in ['1', '2', '3']]}
        expected = [('1', '1'), ('2', '2'), ('3', '3')]
        form = self.get_dummy_form(attrs=fields, choices=choices)
        self.assertEqual(form.fields['cf'].choices, expected)
        self.assertEqual(form.fields['cf2'].choices, [('1', 'a')])


class TestMinMaxRequiredFormMixin(FormTestCase):

    dummy_attrs = {
        'first_name': forms.CharField(),  'last_name': forms.CharField(required=True),
        'favorite_pet': forms.CharField(), 'favorite_sport': forms.CharField(),
    }
    dummy_bases = (MinMaxRequiredFormMixin, forms.Form)

    def test_init_resets_required(self):
        # Assert that __init__ sets any fields declared in minmax_required to not required
        form = self.get_dummy_form()
        self.assertTrue(form.fields['last_name'].required)
        minmax_required = [{'min': 1, 'fields': ['first_name', 'last_name']}]
        form = self.get_dummy_form(attrs={'minmax_required': minmax_required})
        self.assertFalse(form.fields['last_name'].required)

    def test_init_raises_keyerror(self):
        # Assert that __init__ reraises a KeyError if a group's fields contains field names
        # not found on the form.
        minmax_required = [{'min': 1, 'fields': ['a']}]
        form_class = self.get_dummy_form_class(attrs={'minmax_required': minmax_required})
        with self.assertRaises(KeyError):
            form_class()

    def test_get_groups_raises_typeerror(self):
        # Assert that get_groups() raises a TypeError from bad kwargs.
        minmax_required = [{'min': 1, 'fields': ['first_name', 'last_name'], 'bad':'kwarg'}]
        form = self.get_dummy_form(attrs={'minmax_required': minmax_required})
        with self.assertRaises(TypeError):
            list(form.get_groups())

    @translation_override(language=None)
    def test_clean(self):
        attrs = {
            'minmax_required': [
                {'min': 1, 'fields': ['first_name', 'last_name']},
                {'max': 1, 'fields': ['favorite_pet', 'favorite_sport']}
            ]
        }
        form_data = {'favorite_pet': 'Cat', 'favorite_sport': 'Coffee drinking.'}
        form = self.get_dummy_form(attrs=attrs, data=form_data)
        form.is_valid()
        self.assertIn(
            'Bitte mindestens 1 dieser Felder ausfüllen: First Name, Last Name.',
            form.non_field_errors()
        )
        self.assertIn(
            'Bitte höchstens 1 dieser Felder ausfüllen: Favorite Pet, Favorite Sport.',
            form.non_field_errors()
        )

    def test_get_group_error_messages_form_callback(self):
        # Assert that custom callbacks are handled correctly and return
        # the expected error messages.
        def callback(form, group, error_messages, format_kwargs):
            fields = " or ".join(f.replace('_', ' ').title() for f in group.fields)
            return {'max': "%s! Cannot have both!" % fields}

        minmax_required = [{'max': 1, 'fields': ['favorite_pet', 'favorite_sport']}]
        base_attrs = {'minmax_required': minmax_required}
        form_data = {'favorite_pet': 'Cat', 'favorite_sport': 'Coffee drinking.'}
        expected = "Favorite Pet or Favorite Sport! Cannot have both!"
        # Try both valid values for a callback declaration:
        # - the name of a method owned by the form
        # - a standalone callable
        for cb in ('form_cb', callback):
            if isinstance(cb, str):
                callback_type = "form owned method"
            else:
                callback_type = "standalone function"
            with self.subTest(callback_type=callback_type):
                minmax_required[0]['format_callback'] = cb
                attrs = base_attrs.copy()
                if isinstance(cb, str):
                    # Add the callback to the form's methods
                    attrs[cb] = callback
                form = self.get_dummy_form(attrs=attrs, data=form_data)
                self.assertFalse(form.is_valid())

                self.assertIn(expected, form.non_field_errors())


class TestAudioForm(ModelFormTestCase):
    form_class = AudioForm
    model = _models.audio
    fields = ['release_id', 'discogs_url']

    def test_clean_continues_on_empty_data(self):
        # Assert that the clean method does not complain if both fields are empty.
        form = self.get_form(data={'titel': 'Beep'})
        form.full_clean()
        self.assertFalse(form.errors)

    def test_clean_handles_integer_release_id(self):
        # Assert that clean can properly cast any valid input for release_id into a string.
        form = self.get_form(data={'release_id': 1234})
        form.full_clean()
        self.assertNotIn('release_id', form._errors)

        form = self.get_form(data={'release_id': '1234'})
        form.full_clean()
        self.assertNotIn('release_id', form._errors)

    def test_clean_aborts_on_invalid_releaseid_or_discogsurl(self):
        # Assert that clean does not mess with release_id or discogs_url if
        # both/either of them are invalid.
        # release_id invalid, discogs_url should not have been changed:
        form = self.get_form(data={
            'release_id': 'numbers',
            'discogs_url': 'https://www.discogs.com/release/3512181'
        })
        form.full_clean()
        self.assertNotIn('discogs_url', form._errors)
        self.assertIn('discogs_url', form.cleaned_data)
        self.assertEqual(
            form.cleaned_data['discogs_url'],
            'https://www.discogs.com/release/3512181'
        )

        # url invalid, release_id should not have been changed
        form = self.get_form(data={'release_id': 1234, 'discogs_url': 'a real url'})
        form.full_clean()
        self.assertEqual(form.cleaned_data.get('release_id', ''), 1234)

        # both invalid
        form = self.get_form(data={'release_id': 'numbers', 'discogs_url': 'a real url'})
        form.full_clean()
        self.assertNotIn('release_id', form.cleaned_data)
        self.assertNotIn('discogs_url', form.cleaned_data)

    @translation_override(language=None)
    def test_clean_raises_error_when_releaseid_and_discogsurl_dont_fit(self):
        # Assert that clean raises a ValidationError when release_id and the
        # release_id given in discogs_url don't fit.
        form = self.get_form(data={
            'release_id': '1234',
            'discogs_url': 'http://www.discogs.com/release/3512181'
        })
        form.full_clean()
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        expected_error_message = (
            "Die angegebene Release ID stimmt nicht mit der ID im Discogs Link überein.")
        self.assertIn(expected_error_message, form.errors[NON_FIELD_ERRORS])

    def test_clean_sets_release_id_from_url(self):
        # Assert that clean sets the correct release_id from a given valid url if a release_id
        # was missing.
        form = self.get_form(data={'discogs_url': 'http://www.discogs.com/release/3512181'})
        form.full_clean()
        self.assertTrue(form.is_valid())
        self.assertIn('release_id', form.cleaned_data)
        self.assertEqual(form.cleaned_data['release_id'], '3512181')

    def test_clean_sets_url_from_release_id(self):
        # Assert that clean creates the correct url from a given valid release_id if an url
        # was missing
        form = self.get_form(data={'release_id': 1234})
        form.full_clean()
        self.assertIn('discogs_url', form.cleaned_data)
        self.assertEqual(
            form.cleaned_data['discogs_url'],
            'http://www.discogs.com/release/1234'
        )

    def test_clean_strips_slug(self):
        # Assert that clean strips the url from any slugs
        form = self.get_form(data={
            'release_id': 3512181,
            'discogs_url': 'https://www.discogs.com/Manderley--Fliegt-Gedanken-Fliegt-/release/3512181'
        })
        form.full_clean()
        self.assertEqual(
            form.cleaned_data['discogs_url'],
            'http://www.discogs.com/release/3512181'
        )

    @translation_override(language=None)
    def test_invalid_urls_keep_old_error_message(self):
        # Assert that invalid urls are validated through the default URLValidator also
        form = self.get_form(data={'titel': 'Beep', 'discogs_url': 'notavalidurl'})
        self.assertIn('discogs_url', form.errors)
        self.assertIn('Enter a valid URL.', form.errors['discogs_url'])
        self.assertIn(
            "Bitte nur Adressen von discogs.com eingeben.",
            form.errors['discogs_url']
        )

    @translation_override(language=None)
    def test_urls_only_valid_from_discogs(self):
        # Assert that only urls with domain discogs.com are valid
        form = self.get_form(data={'titel': 'Beep', 'discogs_url': 'http://www.google.com'})
        self.assertIn('discogs_url', form.errors)
        self.assertIn(
            "Bitte nur Adressen von discogs.com eingeben.", form.errors['discogs_url'])

    def test_urls_with_slug_valid(self):
        # Assert that discogs urls with a slug are not regarded as invalid.
        form = self.get_form(data={
            'titel': 'Beep',
            'discogs_url': 'https://www.discogs.com/release/3512181'
        })
        self.assertNotIn('discogs_url', form.errors)

    def test_urls_without_slug_valid(self):
        # Assert that discogs urls without a slug are not regarded as invalid.
        form = self.get_form(data={
            'titel': 'Beep',
            'discogs_url': 'https://www.discogs.com/Manderley--Fliegt-Gedanken-Fliegt-/release/3512181'
        })
        self.assertNotIn('discogs_url', form.errors)

#x = {
#    'm2m_band_musiker_set-INITIAL_FORMS': ['1'],
#    'm2m_band_musiker_set-MIN_NUM_FORMS': ['0'],
#    'm2m_band_musiker_set-MAX_NUM_FORMS': ['1000'],
#    'm2m_band_musiker_set-TOTAL_FORMS': ['2'],
#
#    'band_name': ['Test Band'],
#
#    'm2m_band_musiker_set-0-id': ['21348'],
#    'm2m_band_musiker_set-0-band': ['4449'],
#    'm2m_band_musiker_set-0-musiker': ['35627'],
#    'm2m_band_musiker_set-1-id': [''],
#    'm2m_band_musiker_set-1-band': ['4449']}
#    'm2m_band_musiker_set-1-musiker': ['35627'],
#
#    'm2m_band_musiker_set-__prefix__-id': [''],


#    'm2m_band_musiker_set-__prefix__-band': ['4449'],
#    'm2m_band_musiker_set-__prefix__-musiker': [''],
#}

class TestMIZAdminInlineFormBase(MyTestCase):
    form = MIZAdminInlineFormBase
    model = _models.Band.musiker.through
    fields = ['band', 'musiker']

    @classmethod
    def setUpTestData(cls):
        cls.band = make(_models.Band)
        cls.musiker = make(_models.Musiker)
        cls.m2m = _models.Band.musiker.through.objects.create(
            band=cls.band, musiker=cls.musiker)
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.formset_class = forms.inlineformset_factory(
            _models.Band, _models.Band.musiker.through,
            form=self.form,
            fields=forms.ALL_FIELDS,
            extra=1,
        )

    def test_validate_unique(self):
        # Assert that MIZAdminInlineFormBase handles duplicate entries as
        # expected.
        data = {
            'm2m_band_musiker_set-INITIAL_FORMS': '1',
            'm2m_band_musiker_set-TOTAL_FORMS': '2',
            'm2m_band_musiker_set-0-id': self.m2m.pk,
            'm2m_band_musiker_set-0-musiker': self.musiker.pk,
            'm2m_band_musiker_set-0-band': self.band.pk,
            'm2m_band_musiker_set-1-id': '',
            'm2m_band_musiker_set-1-musiker': self.musiker.pk,
            'm2m_band_musiker_set-1-band': self.band.pk,
        }
        formset = self.formset_class(instance=self.band, data=data)
        for form in formset.forms:
            self.assertTrue(form.is_valid())
            self.assertIsNone(
                form.validate_unique(),
                msg="Expected validation on uniqueness to always succeed."
            )
            # Assert that the duplicate entry indeed throws a ValidationError
            # and was then flagged to be deleted:
            self.assertIn('DELETE', form.cleaned_data)
            if not form.instance.pk:
                msg_text = (
                    "Expected instance.validate_unique to throw a "
                    "ValidationError for duplicate instances."
                )
                with self.assertRaises(ValidationError, msg=msg_text):
                    form.instance.validate_unique()
                self.assertTrue(form.cleaned_data['DELETE'])
            else:
                self.assertFalse(form.cleaned_data['DELETE'])
