from unittest.mock import patch

# noinspection PyPackageRequirements
from dal import autocomplete, forward
from django.core.exceptions import ImproperlyConfigured
from django.forms import Media, widgets
from django.utils.translation import override as translation_override

import dbentry.models as _models
from dbentry.ac.widgets import (
    EXTRA_DATA_KEY, GenericURLWidgetMixin, MIZModelSelect2, MIZModelSelect2Multiple, MIZWidgetMixin,
    RemoteModelWidgetWrapper, TabularResultsMixin, make_widget
)
from dbentry.forms import ArtikelForm
from dbentry.tests.base import MyTestCase


class TestRemoteModelWidgetWrapper(MyTestCase):

    def setUp(self):
        super().setUp()
        form = ArtikelForm()
        self.widget = RemoteModelWidgetWrapper(
            form.fields['ausgabe'].widget, _models.Ausgabe, 'id'
        )
        rel_opts = self.widget.remote_model._meta
        self.info = (rel_opts.app_label, rel_opts.model_name)

    def test_get_related_url(self):
        url = self.widget.get_related_url(self.info, 'change', '__fk__')
        self.assertEqual(
            url, "/admin/dbentry/ausgabe/__fk__/change/",
            msg='info: {}'.format(self.info)
        )

        url = self.widget.get_related_url(self.info, 'add')
        self.assertEqual(url, "/admin/dbentry/ausgabe/add/")

        url = self.widget.get_related_url(self.info, 'delete', '__fk__')
        self.assertEqual(url, "/admin/dbentry/ausgabe/__fk__/delete/")

    def test_get_context_can_change(self):
        with patch.object(self.widget, 'can_change_related', True):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertTrue(context.get('can_change_related', False))
            self.assertEqual(
                context.get('change_related_template_url'),
                "/admin/dbentry/ausgabe/__fk__/change/"
            )
        with patch.object(self.widget, 'can_change_related', False):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertNotIn('can_change_related', context)

    def test_get_context_can_add(self):
        with patch.object(self.widget, 'can_add_related', True):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertTrue(context.get('can_add_related', False))
            self.assertEqual(context.get('add_related_url'), "/admin/dbentry/ausgabe/add/")
        with patch.object(self.widget, 'can_add_related', False):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertNotIn('can_add_related', context)

    def test_get_context_can_delete(self):
        with patch.object(self.widget, 'can_delete_related', True):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertTrue(context.get('can_delete_related', False))
            self.assertEqual(
                context.get('delete_related_template_url'),
                "/admin/dbentry/ausgabe/__fk__/delete/"
            )
        with patch.object(self.widget, 'can_delete_related', False):
            context = self.widget.get_context('Beep', ['1'], {'id': 1})
            self.assertNotIn('can_delete_related', context)

    def test_wrapper_includes_related_object_js(self):
        # Assert that the wrapped widget includes the RelatedObjectLookups.js
        self.assertIn('admin/js/admin/RelatedObjectLookups.js', self.widget.media._js)

    def test_no_related_links_for_multiple(self):
        # Assert that no add/change/delete links/icons for related objects
        # are added if the widget is a form of SelectMultiple.
        widget = RemoteModelWidgetWrapper(
            widget=widgets.SelectMultiple(),
            remote_model=_models.Ausgabe,
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
        # Assert that init defaults remote_field_name to the PK field name.
        widget = RemoteModelWidgetWrapper(
            widget=widgets.SelectMultiple(),
            remote_model=_models.Ausgabe
        )
        self.assertEqual(widget.remote_field_name, 'id')
        widget = RemoteModelWidgetWrapper(
            widget=widgets.SelectMultiple(),
            remote_model=_models.Katalog
        )
        self.assertEqual(widget.remote_field_name, 'basebrochure_ptr_id')


class DummyMixinSuper(object):

    def __init__(self, url, *args, **kwargs):
        self._url = url


class TestWidgetCaptureMixin(MyTestCase):

    dummy_class = type('Dummy', (GenericURLWidgetMixin, DummyMixinSuper), {})

    def test_init(self):
        # Assert that init sets model_name.
        self.assertEqual(self.dummy_class(model_name='genre').model_name, 'genre')

        # Assert that 'url' argument defaults to class attribute
        # 'generic_url_name' and is passed on to the super class constructor.
        self.dummy_class.generic_url_name = ''
        self.assertEqual(self.dummy_class(model_name='genre')._url, '')
        self.dummy_class.generic_url_name = 'this-is-the-default'
        self.assertEqual(self.dummy_class(model_name='genre')._url, 'this-is-the-default')
        # noinspection SpellCheckingInspection
        self.assertEqual(
            self.dummy_class(model_name='genre', url='nocapture')._url, 'nocapture'
        )

    @patch('dbentry.ac.widgets.reverse')
    def test_get_url(self, mocked_reverse):
        obj = self.dummy_class(model_name='genre', url=None)
        self.assertIsNone(obj._get_url())
        self.assertFalse(mocked_reverse.called)

        obj._url = 'Test/Test'
        self.assertEqual(obj._get_url(), 'Test/Test')
        self.assertFalse(mocked_reverse.called)

        # reversing of the generic url starts here
        obj._url = obj.generic_url_name = 'accapture'
        obj._get_url()
        reverse_args, reverse_kwargs = mocked_reverse.call_args
        self.assertEqual(reverse_args, ('accapture', ))
        self.assertIn('kwargs', reverse_kwargs)
        self.assertIn('model_name', reverse_kwargs['kwargs'])
        self.assertEqual(reverse_kwargs['kwargs']['model_name'], 'genre')

    def test_get_reverse_kwargs(self):
        # Assert tat get_reverse_kwargs only includes model_name, if it is set.
        obj = self.dummy_class(model_name='')
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


class TestMIZWidgetMixin(MyTestCase):

    dummy_class = type('Dummy', (MIZWidgetMixin, DummyMixinSuper), {})

    def test_init(self):
        # Assert that init sets create_field
        self.assertEqual(self.dummy_class(model_name='genre').create_field, '')

        self.assertEqual(
            self.dummy_class(model_name='genre', create_field='Test').create_field,
            'Test'
        )

    def test_get_reverse_kwargs(self):
        # Assert that get_reverse_kwargs adds 'create_field', if it is set.
        obj = self.dummy_class(model_name='model_name')
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


class TestMakeWidget(MyTestCase):

    def test_takes_widget_class(self):
        widget = make_widget(widget_class=widgets.TextInput)
        self.assertIsInstance(widget, widgets.TextInput)

    def test_select_multiple(self):
        self.assertIsInstance(
            make_widget(model=_models.Genre, multiple=False), MIZModelSelect2)
        self.assertIsInstance(
            make_widget(model=_models.Genre, multiple=True), MIZModelSelect2Multiple)

    def test_exception_on_no_model(self):
        with self.assertRaises(ImproperlyConfigured) as cm:
            make_widget(multiple=False)
        expected_error_msg = "MIZModelSelect2 widget missing argument 'model_name'."
        self.assertEqual(cm.exception.args[0], expected_error_msg)

    def test_assigns_create_field(self):
        widget = make_widget(model=_models.Genre)
        self.assertEqual(widget.create_field, 'genre')

    def test_does_not_assign_url_to_not_dal_widgets(self):
        # Do note that the attribute url of a dal widget is actually a property,
        # so we're looking for the private attribute '_url' instead to not invoke the property
        widget = make_widget(widget_class=widgets.TextInput)
        self.assertFalse(hasattr(widget, '_url'))

        widget = make_widget(model=_models.Genre, widget_class=autocomplete.ModelSelect2)
        self.assertTrue(hasattr(widget, '_url'))

    @translation_override(language=None)
    def test_forwarded(self):
        # The values for forward are wrapped in a forward.Field object.

        # Assert that make_widget can handle non-list 'forward' values
        widget = make_widget(model=_models.Ausgabe, forward='magazin')
        self.assertEqual(widget.forward[0].src, 'magazin')
        self.assertEqual(
            widget.attrs['data-placeholder'], "Bitte zuerst Magazin auswählen.")

        widget = make_widget(
            model=_models.Genre, forward='magazin', attrs={'data-placeholder': 'Go home!'})
        self.assertEqual(widget.forward[0].src, 'magazin')
        self.assertEqual(widget.attrs['data-placeholder'], 'Go home!')

        # Assert that forward values can also be forward.Field objects
        forwarded = forward.Field(src='magazin', dst='ausgabe')
        widget = make_widget(model=_models.Ausgabe, forward=forwarded)
        self.assertEqual(widget.forward[0], forwarded)

        # Assert that the placeholder text defaults to forward's src if no model
        # field corresponds to src or dst.
        forwarded = forward.Field(src='beep_boop', dst=None)
        widget = make_widget(model=_models.Ausgabe, forward=forwarded)
        self.assertEqual(
            widget.attrs['data-placeholder'], 'Bitte zuerst Beep Boop auswählen.')

    def test_forwarded_empty_values(self):
        # Assert that 'empty' values can be handled.
        for val in [(), [], None, ""]:
            with self.subTest(value=val):
                widget = make_widget(model=_models.Genre, forward=val)
                self.assertFalse(widget.forward)

    def test_preserves_attrs(self):
        # Assert that make_widget preserves 'attrs' passed in via kwargs even
        # though the forwarded bit messes with that.
        class DummyWidget(MIZModelSelect2):
            # noinspection PyMissingConstructor
            def __init__(self, *_args, **kwargs):
                self.untouched = kwargs.get('attrs', {}).pop('untouched', None)
        widget = make_widget(
            model=_models.Ausgabe, widget_class=DummyWidget,
            forward='magazin', attrs={'data-placeholder': 'Go home!', 'untouched': 1}
        )
        self.assertEqual(widget.untouched, 1)

    def test_wraps(self):
        widget = make_widget(model=_models.Genre, multiple=False, wrap=False)
        self.assertIsInstance(widget, MIZModelSelect2)
        widget = make_widget(model=_models.Genre, multiple=False, wrap=True)
        self.assertIsInstance(widget, RemoteModelWidgetWrapper)


class TestTabularResultsMixin(MyTestCase):

    class DummyWidget(object):

        def __init__(self, attrs=None):
            self.attrs = attrs or {}

        @property
        def media(self):
            return Media()

    class TabularWidget(TabularResultsMixin, DummyWidget):
        pass

    def test_init_adds_class(self):
        # Assert that init adds the necessary css class to the widget attrs.
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
