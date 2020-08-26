from functools import partial

from django.forms import widgets
from django.core.exceptions import ImproperlyConfigured
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import override as translation_override

import DBentry.models as _models
from DBentry.ac.widgets import (
    EasyWidgetWrapper, WidgetCaptureMixin, MIZModelSelect2,
    MIZModelSelect2Multiple, make_widget
)
from DBentry.forms import ArtikelForm
from DBentry.tests.base import MyTestCase

from dal import autocomplete, forward


class TestEasyWidgetWrapper(MyTestCase):

    def setUp(self):
        super().setUp()
        form = ArtikelForm()
        self.widget = EasyWidgetWrapper(
            form.fields['ausgabe'].widget, _models.Ausgabe, 'id')
        rel_opts = self.widget.related_model._meta
        self.info = (rel_opts.app_label, rel_opts.model_name)

    def test_get_related_url(self):
        url = self.widget.get_related_url(self.info, 'change', '__fk__')
        self.assertEqual(
            url, "/admin/DBentry/ausgabe/__fk__/change/",
            msg='info: {}'.format(self.info)
        )

        url = self.widget.get_related_url(self.info, 'add')
        self.assertEqual(url, "/admin/DBentry/ausgabe/add/")

        url = self.widget.get_related_url(self.info, 'delete', '__fk__')
        self.assertEqual(url, "/admin/DBentry/ausgabe/__fk__/delete/")

    def test_get_context_can_change(self):
        context = self.widget.get_context('Beep', ['1'], {'id': 1})
        self.assertTrue(context.get('can_change_related', False))
        self.assertEqual(
            context.get('change_related_template_url'),
            "/admin/DBentry/ausgabe/__fk__/change/"
        )

    def test_get_context_can_add(self):
        context = self.widget.get_context('Beep', ['1'], {'id': 1})
        self.assertTrue(context.get('can_add_related', False))
        self.assertEqual(context.get('add_related_url'), "/admin/DBentry/ausgabe/add/")

    def test_get_context_can_delete(self):
        self.widget.can_delete_related = True
        context = self.widget.get_context('Beep', ['1'], {'id': 1})
        self.assertTrue(context.get('can_delete_related', False))
        self.assertEqual(
            context.get('delete_related_template_url'),
            "/admin/DBentry/ausgabe/__fk__/delete/"
        )

    def test_wrapper_includes_relatedobject_js(self):
        # Assert that the wrapped widget includes the RelatedObjectLookups.js
        self.assertIn('admin/js/admin/RelatedObjectLookups.js', self.widget.media._js)

    def test_no_related_links_for_multiple(self):
        # Assert that no add/change/delete links/icons for related objects
        # are added if the widget is a form of SelectMultiple.
        widget = EasyWidgetWrapper(
            widget=widgets.SelectMultiple(),
            related_model=_models.Ausgabe,
            can_add_related=True,
            can_change_related=True,
            can_delete_related=True
        )
        context = widget.get_context('Beep', ['1'], {'id': 1})
        for attr in ('can_add_related', 'can_change_related', 'can_delete_related'):
            with self.subTest(attr=attr):
                self.assertFalse(getattr(widget, attr))
                self.assertFalse(context.get(attr, False))


class TestWidgetCaptureMixin(MyTestCase):

    class MixinSuper(object):

        def __init__(self, *args, **kwargs):
            self.args = args
            self._url = kwargs.pop('url', None)
            self.kwargs = kwargs

    dummy_class = type('Dummy', (WidgetCaptureMixin, MixinSuper), {})
    cls = partial(dummy_class, model_name='genre')

    def test_init(self):
        # Assert that init sets create_field
        self.assertEqual(self.cls(create_field='Test').create_field, 'Test')
        self.assertIsNone(self.cls().create_field)

        # Assert that 'url' kwarg defaults to 'accapture'
        self.assertEqual(self.cls()._url, 'accapture')
        self.assertEqual(self.cls(url='nocapture')._url, 'nocapture')

    def test_get_url(self):
        o = self.cls(url=None)
        self.assertIsNone(o._get_url())

        o._url = 'Test/Test'
        self.assertEqual(o._get_url(), 'Test/Test')

        # reversing of a named url starts here
        o._url = 'accapture'
        self.assertEqual(o._get_url(), '/admin/ac/genre/')
        o.create_field = 'genre'
        self.assertEqual(o._get_url(), '/admin/ac/genre/genre/')

        o._url = 'acbuchband'
        o.create_field = None
        self.assertEqual(o._get_url(), '/admin/ac/buch/')

        o._url = 'averyrandomurl'
        with self.assertRaises(NoReverseMatch):
            o._get_url()


class TestMakeWidget(MyTestCase):

    def test_takes_widget_class(self):
        widget = make_widget(widget_class=widgets.TextInput)
        self.assertIsInstance(widget, widgets.TextInput)

    def test_selectmultiple(self):
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
            def __init__(self, *args, **kwargs):
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
        self.assertIsInstance(widget, EasyWidgetWrapper)
