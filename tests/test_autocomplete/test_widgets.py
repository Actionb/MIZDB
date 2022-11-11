from unittest.mock import patch

from dal import forward
from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.forms import Media, widgets
from django.test import override_settings
from django.utils.translation import override as translation_override

from dbentry.ac.widgets import (
    EXTRA_DATA_KEY, GenericURLWidgetMixin, MIZModelSelect2, MIZModelSelect2Multiple,
    MIZModelSelect2MultipleTabular, MIZModelSelect2Tabular, MIZWidgetMixin,
    RemoteModelWidgetWrapper, TabularResultsMixin, make_widget
)
from tests.case import MIZTestCase
from tests.test_autocomplete.models import Artikel, Ausgabe, Inherited


class ArtikelForm(forms.ModelForm):
    class Meta:
        model = Artikel
        fields = '__all__'


@override_settings(ROOT_URLCONF='tests.test_autocomplete.urls')
class TestRemoteModelWidgetWrapper(MIZTestCase):

    def setUp(self):
        super().setUp()
        form = ArtikelForm()
        self.widget = RemoteModelWidgetWrapper(form.fields['ausgabe'].widget, Ausgabe, 'id')

    def test_get_related_url(self):
        url = self.widget.get_related_url(('test_autocomplete', 'ausgabe'), 'change', '__fk__')
        self.assertEqual(url, "/admin/test_autocomplete/ausgabe/__fk__/change/", )

        url = self.widget.get_related_url(('test_autocomplete', 'ausgabe'), 'add')
        self.assertEqual(url, "/admin/test_autocomplete/ausgabe/add/")

        url = self.widget.get_related_url(('test_autocomplete', 'ausgabe'), 'delete', '__fk__')
        self.assertEqual(url, "/admin/test_autocomplete/ausgabe/__fk__/delete/")

    def test_get_context_can_change(self):
        with patch.object(self.widget, 'can_change_related', True):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertTrue(context.get('can_change_related', False))
            self.assertEqual(
                context.get('change_related_template_url'),
                "/admin/test_autocomplete/ausgabe/__fk__/change/"
            )

        with patch.object(self.widget, 'can_change_related', False):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertNotIn('can_change_related', context)

    def test_get_context_can_add(self):
        with patch.object(self.widget, 'can_add_related', True):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertTrue(context.get('can_add_related', False))
            self.assertEqual(
                context.get('add_related_url'),
                "/admin/test_autocomplete/ausgabe/add/"
            )

        with patch.object(self.widget, 'can_add_related', False):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertNotIn('can_add_related', context)

    def test_get_context_can_delete(self):
        with patch.object(self.widget, 'can_delete_related', True):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertTrue(context.get('can_delete_related', False))
            self.assertEqual(
                context.get('delete_related_template_url'),
                "/admin/test_autocomplete/ausgabe/__fk__/delete/"
            )

        with patch.object(self.widget, 'can_delete_related', False):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertNotIn('can_delete_related', context)

    def test_wrapper_includes_related_object_js(self):
        """Assert that the wrapped widget includes the RelatedObjectLookups.js"""
        self.assertIn('admin/js/admin/RelatedObjectLookups.js', self.widget.media._js)

    def test_no_related_links_for_multiple(self):
        """
        Assert that no add/change/delete links/icons for related objects are
        added if the widget is a form of SelectMultiple.
        """
        widget = RemoteModelWidgetWrapper(
            widget=widgets.SelectMultiple(),
            remote_model=Ausgabe,
            can_add_related=True,
            can_change_related=True,
            can_delete_related=True
        )
        context = widget.get_context('Beep', ['1'], {'id': 1})
        for attr in ('can_add_related', 'can_change_related', 'can_delete_related'):
            with self.subTest(attr=attr):
                self.assertFalse(getattr(widget, attr))
                self.assertFalse(context.get(attr, False))

    def test_remote_field_defaults_to_pk(self):
        """Assert that init defaults remote_field_name to the PK field name."""
        widget = RemoteModelWidgetWrapper(widget=widgets.SelectMultiple(), remote_model=Ausgabe)
        self.assertEqual(widget.remote_field_name, 'id')
        widget = RemoteModelWidgetWrapper(widget=widgets.SelectMultiple(), remote_model=Inherited)
        self.assertEqual(widget.remote_field_name, 'base_ptr_id')


class DummyMixinSuper(object):

    def __init__(self, url, *_args, **_kwargs):
        self._url = url


class TestGenericURLWidgetMixin(MIZTestCase):
    class Widget(GenericURLWidgetMixin, DummyMixinSuper):
        generic_url_name = 'generic'

    def test_init_sets_model_name(self):
        """Assert that init sets model_name."""
        self.assertEqual(self.Widget(model_name='genre').model_name, 'genre')

    def test_init_uses_generic_url_name(self):
        """
        Assert that url argument defaults to class attribute 'generic_url_name'
        and is passed on to the super class constructor.
        """
        with patch.object(self.Widget, 'generic_url_name'):
            self.Widget.generic_url_name = ''
            self.assertEqual(self.Widget(model_name='genre')._url, '')
            self.Widget.generic_url_name = 'this-is-the-default'
            self.assertEqual(self.Widget(model_name='genre')._url, 'this-is-the-default')
            self.assertEqual(self.Widget(model_name='genre', url='nocapture')._url, 'nocapture')

    @patch('dbentry.ac.widgets.reverse')
    def test_get_url_none(self, reverse_mock):
        """_get_url should return None, if the url was set to None."""
        obj = self.Widget(model_name='genre', url=None)
        self.assertIsNone(obj._get_url())
        self.assertFalse(reverse_mock.called)

    @patch('dbentry.ac.widgets.reverse')
    def test_get_url_set_url(self, reverse_mock):
        """_get_url should return any URLs directly, if they contain a forward slash."""
        obj = self.Widget(model_name='genre', url='Test/Test')
        self.assertEqual(obj._get_url(), 'Test/Test')
        self.assertFalse(reverse_mock.called)

    @patch('dbentry.ac.widgets.reverse')
    def test_get_url_reverses_generic_url_name(self, reverse_mock):
        """
        _get_url should attempt reversing the generic URL name with the
        expected kwargs.
        """
        obj = self.Widget(model_name='genre', url='generic')
        obj._get_url()
        reverse_args, reverse_kwargs = reverse_mock.call_args
        self.assertEqual(reverse_args, ('generic',))
        self.assertIn('kwargs', reverse_kwargs)
        self.assertIn('model_name', reverse_kwargs['kwargs'])
        self.assertEqual(reverse_kwargs['kwargs']['model_name'], 'genre')

    @patch('dbentry.ac.widgets.reverse')
    def test_get_url_reverses(self, reverse_mock):
        """
        _get_url should just reverse the given URL name, if it doesn't contain
        a forward slash or is the generic URL name.
        """
        obj = self.Widget(model_name='genre', url='changelist')
        obj._get_url()
        reverse_args, reverse_kwargs = reverse_mock.call_args
        self.assertEqual(reverse_args, ('changelist',))
        self.assertFalse(reverse_kwargs)

    def test_get_reverse_kwargs(self):
        """Assert that get_reverse_kwargs only includes model_name, if it is set."""
        obj = self.Widget(model_name='')
        reverse_kwargs = obj._get_reverse_kwargs(default='default')
        self.assertNotIn('model_name', reverse_kwargs)
        self.assertIn('default', reverse_kwargs)
        self.assertEqual(reverse_kwargs['default'], 'default')

        obj.model_name = 'model-name'
        reverse_kwargs = obj._get_reverse_kwargs(default='default')
        self.assertIn('model_name', reverse_kwargs)
        self.assertEqual(reverse_kwargs['model_name'], 'model-name')
        self.assertIn('default', reverse_kwargs)
        self.assertEqual(reverse_kwargs['default'], 'default')


class TestMIZWidgetMixin(MIZTestCase):
    class Widget(MIZWidgetMixin, DummyMixinSuper):
        pass

    def test_init(self):
        """Assert that init sets create_field."""
        self.assertEqual(self.Widget(model_name='genre').create_field, '')

        self.assertEqual(
            self.Widget(model_name='genre', create_field='Test').create_field,
            'Test'
        )

    def test_get_reverse_kwargs_create_field(self):
        """Assert that get_reverse_kwargs adds 'create_field', if it is set."""
        obj = self.Widget(model_name='model_name')
        reverse_kwargs = obj._get_reverse_kwargs(default='default')
        self.assertNotIn('create_field', reverse_kwargs)
        self.assertIn('default', reverse_kwargs)
        self.assertEqual(reverse_kwargs['default'], 'default')

        obj.create_field = 'create-field'
        reverse_kwargs = obj._get_reverse_kwargs(default='default')
        self.assertIn('create_field', reverse_kwargs)
        self.assertEqual(reverse_kwargs['create_field'], 'create-field')
        self.assertIn('default', reverse_kwargs)
        self.assertEqual(reverse_kwargs['default'], 'default')


class TestMakeWidget(MIZTestCase):

    def test_takes_widget_class(self):
        """make_widget should return a widget of the passed in widget_class."""
        widget = make_widget(widget_class=widgets.TextInput)
        self.assertIsInstance(widget, widgets.TextInput)

    def test_select_multiple(self):
        self.assertIsInstance(make_widget(model=Ausgabe, multiple=False), MIZModelSelect2)
        self.assertIsInstance(make_widget(model=Ausgabe, multiple=True), MIZModelSelect2Multiple)

    def test_tabular(self):
        widget = make_widget(model=Ausgabe, multiple=False, tabular=True)
        self.assertIsInstance(widget, MIZModelSelect2Tabular)
        widget = make_widget(model=Ausgabe, multiple=True, tabular=True)
        self.assertIsInstance(widget, MIZModelSelect2MultipleTabular)

    def test_exception_on_no_model(self):
        with self.assertRaises(ImproperlyConfigured) as cm:
            make_widget(multiple=False)
        self.assertEqual(
            cm.exception.args[0],
            "MIZModelSelect2 widget missing argument 'model_name'."
        )

    def test_assigns_create_field(self):
        widget = make_widget(model=Ausgabe)
        self.assertEqual(widget.create_field, 'name')

    @translation_override(language=None)
    def test_forwarded(self):
        """make_widget should accept various forms of forwarding."""
        # Note that the values for forward are wrapped in a forward.Field
        # object.
        # Assert that make_widget can handle non-list 'forward' values:
        widget = make_widget(model=Ausgabe, forward='magazin')
        self.assertEqual(widget.forward[0].src, 'magazin')
        self.assertEqual(widget.attrs['data-placeholder'], "Bitte zuerst Magazin auswählen.")

        widget = make_widget(
            model=Ausgabe, forward='magazin', attrs={'data-placeholder': 'Test placeholder'}
        )
        self.assertEqual(widget.forward[0].src, 'magazin')
        self.assertEqual(widget.attrs['data-placeholder'], 'Test placeholder')

        # Assert that forward values can also be forward.Field objects:
        forwarded = forward.Field(src='magazin', dst='ausgabe')
        widget = make_widget(model=Ausgabe, forward=forwarded)
        self.assertEqual(widget.forward[0], forwarded)

        # Assert that the placeholder text defaults to forward's src if no model
        # field corresponds to src or dst.
        forwarded = forward.Field(src='beep_boop', dst=None)
        widget = make_widget(model=Ausgabe, forward=forwarded)
        self.assertEqual(widget.attrs['data-placeholder'], 'Bitte zuerst Beep Boop auswählen.')

    def test_forwarded_empty_values(self):
        """Assert that 'empty' values for forward are handled fine."""
        for val in [(), [], None, ""]:
            with self.subTest(value=val):
                widget = make_widget(model=Ausgabe, forward=val)
                self.assertFalse(widget.forward)

    def test_wraps(self):
        widget = make_widget(model=Ausgabe, multiple=False, wrap=False)
        self.assertIsInstance(widget, MIZModelSelect2)
        widget = make_widget(model=Ausgabe, multiple=False, wrap=True)
        self.assertIsInstance(widget, RemoteModelWidgetWrapper)


class TestTabularResultsMixin(MIZTestCase):
    class DummyWidget(object):

        def __init__(self, attrs=None):
            self.attrs = attrs or {}

        @property
        def media(self):
            return Media()

    class TabularWidget(TabularResultsMixin, DummyWidget):
        pass

    def test_init_adds_class(self):
        """Assert that init adds the necessary css class to the widget attrs."""
        widget = self.TabularWidget()
        self.assertIn('class', widget.attrs)
        self.assertEqual(widget.attrs['class'], 'select2-tabular')
        widget = self.TabularWidget(attrs={'class': 'test-class'})
        self.assertIn('class', widget.attrs)
        self.assertEqual(widget.attrs['class'], 'test-class select2-tabular')

    def test_init_adds_extra_data_key(self):
        # Assert that init adds the extra data key to the widget attrs.
        widget = self.TabularWidget()
        self.assertIn('data-extra-data-key', widget.attrs)
        self.assertEqual(widget.attrs['data-extra-data-key'], EXTRA_DATA_KEY)

    def test_adds_javascript(self):
        # Assert that the necessary javascript file is included in the media.
        widget = self.TabularWidget()
        self.assertIn('admin/js/select2_tabular.js', widget.media._js)
