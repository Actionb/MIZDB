from unittest import mock

from django import forms
from django.contrib.admin.helpers import Fieldset
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.utils.translation import override as translation_override

from dbentry.base.forms import (
    DiscogsFormMixin, DynamicChoiceFormMixin, FieldGroup, MIZAdminFormMixin, MIZAdminInlineFormBase,
    MinMaxRequiredFormMixin
)
from tests.case import MIZTestCase
from tests.factory import make
from tests.test_base.models import Audio, Band, Musiker, MusikerAudioM2M


class FieldGroupTest(MIZTestCase):
    class TestForm(forms.Form):
        name = forms.CharField(required=False)
        nickname = forms.CharField(required=False)

        is_musician = forms.BooleanField(required=False)
        is_scientist = forms.BooleanField(required=False)

        def get_group_error_messages(self, *_args, **_kwargs):
            # FieldGroup expects this method of 'MinMaxRequiredFormMixin'.
            return ''

    def test_fields_with_values(self):
        form = self.TestForm(
            data={
                'name': 'Bob', 'nickname': 'Bobby',  # this group's fields has values
                'is_musician': [], 'is_scientist': False,  # this group's fields are 'empty'
            }
        )
        form.full_clean()
        name_group = FieldGroup(form=form, fields=['name', 'nickname'], min_fields=1)
        job_group = FieldGroup(form=form, fields=['is_musician', 'is_scientist'], max_fields=1)
        self.assertEqual(name_group.fields_with_values(), 2)
        self.assertEqual(job_group.fields_with_values(), 0)

    def test_fields_with_values_unknown_fields(self):
        """
        fields_with_values should just ignore fields that do not exist on the
        form.
        """
        form = self.TestForm(data={'name': 'Bob'})
        form.full_clean()
        nonsense_group = FieldGroup(form, fields=['name', 'hovercraft', 'eels'])
        self.assertEqual(nonsense_group.fields_with_values(), 1)

    def test_has_min_error(self):
        group = FieldGroup(self.TestForm(), fields=['name'], min_fields=1)
        self.assertTrue(group.has_min_error(fields_with_values=0))
        self.assertFalse(group.has_min_error(fields_with_values=1))

    def test_has_min_error_min_is_zero(self):
        group = FieldGroup(self.TestForm(), fields=['name'], min_fields=0)
        self.assertFalse(group.has_min_error(fields_with_values=0))
        self.assertFalse(group.has_min_error(fields_with_values=1))

    def test_has_max_error(self):
        group = FieldGroup(self.TestForm(), fields=['name'], max_fields=1)
        self.assertFalse(group.has_max_error(fields_with_values=1))
        self.assertTrue(group.has_max_error(fields_with_values=2))

    def test_has_min_error_max_is_zero(self):
        group = FieldGroup(self.TestForm(), fields=['name'], max_fields=0)
        self.assertFalse(group.has_max_error(fields_with_values=0))
        self.assertFalse(group.has_max_error(fields_with_values=1))

    def test_check(self):
        form = self.TestForm(
            data={'name': 'Brian', 'nickname': 'May', 'is_musician': True, 'is_scientist': True}
        )
        form.full_clean()
        name_group = FieldGroup(form=form, fields=['name', 'nickname'], min_fields=1)
        job_group = FieldGroup(form=form, fields=['is_musician', 'is_scientist'], max_fields=1)
        self.assertEqual(name_group.check(), (False, False))
        self.assertEqual(job_group.check(), (False, True))

        form.cleaned_data['name'] = ''
        form.cleaned_data['nickname'] = ''
        self.assertEqual(name_group.check(), (True, False))

        # Should always return (False, False) if there are no limits set.
        null_group = FieldGroup(form=form, fields=['name', 'nickname'])
        self.assertEqual(null_group.check(), (False, False))


class MinMaxRequiredFormMixinTest(MIZTestCase):
    class TestForm(MinMaxRequiredFormMixin, forms.Form):
        first_name = forms.CharField()
        last_name = forms.CharField(required=True)
        favorite_pet = forms.CharField()
        favorite_sport = forms.CharField()

        minmax_required = [
            {'min_fields': 1, 'fields': ['first_name', 'last_name']},
            {'max_fields': 1, 'fields': ['favorite_pet', 'favorite_sport']}
        ]

    def test_init_resets_required(self):
        """
        Assert that __init__ sets any fields declared in minmax_required to not
        be required.
        """
        form = self.TestForm()
        self.assertFalse(form.fields['last_name'].required)

        form.minmax_required = None
        form.__init__()
        self.assertTrue(form.fields['last_name'].required)

    def test_init_invalid_field_name(self):
        """
        Assert that __init__ ignores declared groups if one of its specified
        field names cannot be found on the form.
        """
        form = self.TestForm()
        form.minmax_required = [
            {'min_fields': 1, 'fields': ['a']},
            {'min_fields': 1, 'fields': ['first_name', 'last_name']}
        ]
        form.__init__()
        self.assertEqual(len(form._groups), 1)
        self.assertEqual(form._groups[0], {'min_fields': 1, 'fields': ['first_name', 'last_name']})

    @translation_override(language=None)
    def test_clean(self):
        """Assert that the expected errors are added to the form's errors."""
        form = self.TestForm(data={'favorite_pet': 'Cat', 'favorite_sport': 'Coffee drinking.'})
        form.full_clean()
        self.assertIn(
            'Bitte mindestens 1 dieser Felder ausfüllen: First Name, Last Name.',
            form.non_field_errors()
        )
        self.assertIn(
            'Bitte höchstens 1 dieser Felder ausfüllen: Favorite Pet, Favorite Sport.',
            form.non_field_errors()
        )

    def test_get_group_error_messages(self):
        form = self.TestForm()
        error_messages = {'min': "Too few favorites!", 'max': "Too many favorites!"}
        group = FieldGroup(
            form, fields=['first_name', 'last_name'], min_fields=1, max_fields=1,
            error_messages=error_messages
        )
        grp_msgs = form.get_group_error_messages(group, error_messages, format_callback=None)
        self.assertEqual(grp_msgs, error_messages)

    def test_get_group_error_messages_form_method_callback(self):
        """
        Assert that get_group_error_messages calls the callback method given by
        name in the 'format_callback' argument.
        """
        callback_mock = mock.Mock(return_value={})
        form_class = type('Form', (self.TestForm,), {'my_callback': callback_mock})
        form = form_class()
        group = mock.Mock(form=form, fields=['first_name', 'last_name'], min=1, max=0)
        msg_format_kwargs = {'fields': 'First Name, Last Name', 'min': 1, 'max': '0'}
        with mock.patch.object(form, 'get_error_message_format_kwargs') as m:
            m.return_value = msg_format_kwargs
            form.get_group_error_messages(group, {}, format_callback='my_callback')
            callback_mock.assert_called_with(form, group, {}, msg_format_kwargs)

    def test_get_group_error_messages_callback(self):
        """
        Assert that get_group_error_messages calls the provided callback
        callable.
        """
        callback_mock = mock.Mock(return_value={})
        form = self.TestForm()
        group = mock.Mock(form=form, fields=['first_name', 'last_name'], min=1, max=0)
        msg_format_kwargs = {'fields': 'First Name, Last Name', 'min': 1, 'max': '0'}
        form.get_group_error_messages(group, {}, format_callback=callback_mock)
        callback_mock.assert_called_with(form, group, {}, msg_format_kwargs)


class MIZAdminFormMixinTest(MIZTestCase):
    class TestForm(MIZAdminFormMixin, forms.Form):
        first_name = forms.CharField()
        last_name = forms.CharField(required=True)

    def test_iter(self):
        """Assert that __iter__ returns Fieldset instances."""
        for fs in self.TestForm().__iter__():
            self.assertIsInstance(fs, Fieldset)

    def test_media_adds_collapse_js(self):
        """
        The form's media should contain collapse.js if any of the fieldsets
        have 'collapse' in their classes.
        """
        form = self.TestForm()
        form.fieldsets = (
            ['Name', {'fields': ['first_name', 'last_name'], 'classes': ()}],
        )
        self.assertNotIn('admin/js/collapse.js', form.media._js)
        form.fieldsets = (
            ['Name', {'fields': ['first_name', 'last_name'], 'classes': ('collapse',)}],
        )
        self.assertIn('admin/js/collapse.js', form.media._js)


class DynamicChoiceFormMixinTest(MIZTestCase):
    class TestForm(DynamicChoiceFormMixin, forms.Form):
        good = forms.ChoiceField(choices=[])
        bad = forms.ChoiceField(choices=[])
        ugly = forms.ChoiceField(choices=[('-1', 'The Ugly Ones')])

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(Band, band_name='Tool')
        cls.obj2 = make(Band, band_name='Led Zeppelin')
        cls.obj3 = make(Band, band_name='BRMC')
        cls.band_choices = [
            # Account for default ordering of the Band model:
            (str(o.pk), str(o)) for o in [cls.obj3, cls.obj2, cls.obj1]
        ]

    def test_set_choices_list(self):
        """set_choices should be able to set the choices from a list object."""
        choices = [('1', 'Beatles'), ('2', 'Stones'), ('3', 'AC/DC')]
        form = self.TestForm()
        form.set_choices(choices={'good': choices})
        self.assertEqual(form.fields['good'].choices, choices)

    def test_set_choices_manager(self):
        """set_choices should be able to set the choices from a manager object."""
        form = self.TestForm()
        form.set_choices(choices={'good': Band.objects})
        self.assertEqual(form.fields['good'].choices, self.band_choices)

    def test_set_choices_queryset(self):
        """set_choices should be able to set the choices from a queryset object."""
        form = self.TestForm()
        form.set_choices(choices={'good': Band.objects.all()})
        self.assertEqual(form.fields['good'].choices, self.band_choices)

    def test_set_choices_all_fields(self):
        """
        Choices provided under the key 'forms.ALL_FIELDS' should apply to all
        fields that do not have choices set.
        """
        all_choices = [('1', 'Beatles'), ('2', 'Stones'), ('3', 'AC/DC')]
        form = self.TestForm()
        form.set_choices(choices={'good': Band.objects.all(), forms.ALL_FIELDS: all_choices})
        self.assertEqual(form.fields['good'].choices, self.band_choices)
        self.assertEqual(form.fields['bad'].choices, all_choices)
        self.assertEqual(form.fields['ugly'].choices, [('-1', 'The Ugly Ones')])

    def test_set_choices_preserved(self):
        """Assert that preset choices are preserved and not overwritten."""
        form = self.TestForm()
        form.set_choices(choices={'ugly': Band.objects.all()})
        self.assertEqual(form.fields['ugly'].choices, [('-1', 'The Ugly Ones')])

    def test_set_choices_raises_type_error(self):
        """
        set_choices should raise an exception if the 'choices' argument is not 
        a dictionary.
        """
        form = self.TestForm()
        with self.assertRaises(TypeError):
            form.set_choices(choices=[1, 2, 3])


class MIZAdminInlineFormBaseTest(MIZTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.audio = make(Audio)
        cls.musiker = make(Musiker)
        cls.m2m = MusikerAudioM2M.objects.create(audio=cls.audio, musiker=cls.musiker)

    def test_validate_unique(self):
        """Assert that MIZAdminInlineFormBase flags duplicates for deletion."""
        data = {
            'musikeraudiom2m_set-INITIAL_FORMS': '1',
            'musikeraudiom2m_set-TOTAL_FORMS': '2',
            # First form displays the existing relation:
            'musikeraudiom2m_set-0-id': self.m2m.pk,
            'musikeraudiom2m_set-0-musiker': self.musiker.pk,
            # The second form is the new duplicate:
            'musikeraudiom2m_set-1-id': '',
            'musikeraudiom2m_set-1-musiker': self.musiker.pk,
        }
        formset_class = forms.inlineformset_factory(
            parent_model=Audio, model=MusikerAudioM2M,
            form=MIZAdminInlineFormBase, fields=forms.ALL_FIELDS, extra=1,
        )
        formset = formset_class(instance=self.audio, data=data)
        original, duplicate = formset.forms
        original.full_clean()
        duplicate.full_clean()

        msg = ("Neither of the formset's forms should raise a ValidationError "
               "when validating unique constraints.")
        with self.assertNotRaises(ValidationError, msg=msg):
            original.validate_unique()
            duplicate.validate_unique()
        self.assertTrue(
            duplicate.cleaned_data['DELETE'],
            msg="Expected the duplicate form to be flagged for deletion."
        )
        self.assertFalse(original.cleaned_data['DELETE'])


class TestDiscogsFormMixin(MIZTestCase):
    class TestForm(DiscogsFormMixin, forms.Form):
        url_field_name = 'discogs_url'
        release_id_field_name = 'release_id'

        discogs_url = forms.URLField(required=False)
        release_id = forms.IntegerField(required=False)

    def test_clean_no_data(self):
        """Assert that clean does not require both fields to be filled."""
        form = self.TestForm()
        form._errors, form.cleaned_data = {}, {}
        form.clean()
        self.assertFalse(form.errors)

    @translation_override(language=None)
    def test_clean_no_match_id_and_url(self):
        """
        Assert that clean raises a ValidationError when release_id and the
        release_id given in discogs_url don't match.
        """
        form = self.TestForm(
            data={
                'release_id': '1234',
                'discogs_url': 'http://www.discogs.com/release/3512181'
            }
        )
        form.full_clean()
        self.assertIn(NON_FIELD_ERRORS, form.errors)
        expected_error_message = (
            "Die angegebene Release ID (1234) stimmt nicht mit der ID im Discogs"
            " Link überein (3512181)."
        )
        self.assertIn(expected_error_message, form.errors[NON_FIELD_ERRORS])

    def test_clean_sets_release_id_from_url(self):
        """
        Assert that a release_id is derived from the URL if no release_id was
        provided.
        """
        form = self.TestForm(data={'discogs_url': 'http://www.discogs.com/release/3512181'})
        form.full_clean()
        self.assertEqual(form.cleaned_data['release_id'], '3512181')

    def test_clean_sets_url_from_release_id(self):
        """
        Assert that a URL is created with a given valid release_id if no URL
        was provided.
        """
        form = self.TestForm(data={'release_id': 1234})
        form.full_clean()
        self.assertIn('discogs_url', form.cleaned_data)
        self.assertEqual(form.cleaned_data['discogs_url'], 'https://www.discogs.com/release/1234')

    def test_urls_with_slug_valid(self):
        """Assert that discogs urls with slugs are not regarded as invalid."""
        urls = [
            'https://www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            'www.discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            'discogs.com/release/4126-Led-Zeppelin-Led-Zeppelin',
            # I believe discogs has since stopped using this URL format:
            'https://www.discogs.com/Manderley--Fliegt-Gedanken-Fliegt-/release/3512181',
        ]
        for url in urls:
            with self.subTest(url=url):
                form = self.TestForm(data={'titel': 'Beep', 'discogs_url': url})
                self.assertNotIn('discogs_url', form.errors)

    def test_urls_without_slug_valid(self):
        """Assert that discogs urls without slugs are not regarded as invalid."""
        urls = [
            'https://www.discogs.com/release/4126',
            'www.discogs.com/release/4126',
            'discogs.com/release/4126',
        ]
        for url in urls:
            with self.subTest(url=url):
                form = self.TestForm(data={'discogs_url': url})
                self.assertNotIn('discogs_url', form.errors)

    def test_clean_strips_slug(self):
        """Assert any slugs are stripped from the URL."""
        urls = [
            'https://www.discogs.com/de/release/3512181-Manderley-Fliegt-Gedanken-Fliegt',
            'www.discogs.com/de/release/3512181-Manderley-Fliegt-Gedanken-Fliegt',
            'discogs.com/de/release/3512181-Manderley-Fliegt-Gedanken-Fliegt',
            # I believe discogs has since stopped using this URL format:
            'https://www.discogs.com/Manderley--Fliegt-Gedanken-Fliegt-/release/3512181',
        ]
        for url in urls:
            with self.subTest(url=url):
                form = self.TestForm(data={'release_id': 3512181, 'discogs_url': url})
                form.full_clean()
                self.assertEqual(
                    form.cleaned_data['discogs_url'],
                    'https://www.discogs.com/release/3512181'
                )

    @translation_override(language=None)
    def test_invalid_urls_include_field_error_message(self):
        """
        Assert that the default error message of URLFields is included in the
        error messages on an invalid URL.
        """
        form = self.TestForm(data={'discogs_url': 'notavalidurl'})
        form.full_clean()
        self.assertIn('discogs_url', form.errors)
        self.assertIn('Enter a valid URL.', form.errors['discogs_url'])
        self.assertIn(
            "Bitte nur Adressen von discogs.com eingeben.",
            form.errors['discogs_url']
        )

    @translation_override(language=None)
    def test_urls_only_valid_from_discogs(self):
        """Assert that only urls with domain discogs.com can be valid."""
        form = self.TestForm(data={'discogs_url': 'http://www.google.com'})
        form.full_clean()
        self.assertIn('discogs_url', form.errors)
        self.assertIn(
            "Bitte nur Adressen von discogs.com eingeben.", form.errors['discogs_url']
        )
        form = self.TestForm(data={'discogs_url': 'https://www.discogs.com/release/3512181'})
        form.full_clean()
        self.assertNotIn('discogs_url', form.errors)
