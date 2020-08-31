import re
from unittest.mock import patch, Mock
from collections import OrderedDict

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.urls import reverse, resolve
from django.utils.http import unquote

from DBentry import models as _models
from DBentry import utils
from DBentry.actions.views import MergeViewWizarded
from DBentry.factory import make
from DBentry.maint.views import (
    DuplicateObjectsView, ModelSelectView, UnusedObjectsView
)
from DBentry.tests.base import ViewTestCase
from DBentry.tests.mixins import TestDataMixin


class TestModelSelectView(ViewTestCase):

    view_class = ModelSelectView

    def test_get_context_data(self):
        initkwargs = {
            'submit_value': 'testing_value',
            'submit_name': 'testing_name',
            'form_method': 'testing_form_method'
        }
        view = self.get_view(self.get_request(), **initkwargs)
        context = view.get_context_data()
        for context_variable, expected in initkwargs.items():
            with self.subTest(var=context_variable):
                self.assertIn(context_variable, context)
                self.assertEqual(context[context_variable], expected)

    def test_get(self):
        # Assert that get() redirects to the success url if
        # the view's submit_name is in the GET querydict.
        request = self.get_request(data={'testing': 'yes'})
        view = self.get_view(request, submit_name='testing')
        with patch.object(view, 'get_success_url', return_value='admin:index'):
            response = view.get(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/')

    def test_get_success_url(self):
        # Assert that get_success_url returns a resolveable url.
        view = self.get_view(self.get_request(), next_view='admin:index')
        with patch.object(view, 'get_next_view_kwargs', return_value={}):
            self.assertEqual(view.get_success_url(), '/admin/')

    def test_get_next_view_kwargs(self):
        view = self.get_view(self.get_request(data={'model_select': 'some_model'}))
        self.assertEqual(view.get_next_view_kwargs(), {'model_name': 'some_model'})


class TestDuplicateObjectsView(TestDataMixin, ViewTestCase):

    model = _models.Band
    view_class = DuplicateObjectsView

    @classmethod
    def setUpTestData(cls):
        # Not using make() as the factory for band has 'band_name' in
        # get_or_create; calling make(band_name = 'X') repeatedly will always
        # return the same band object.
        cls.test_data = [
            _models.Band.objects.create(id=i, band_name='Beep')
            for i in range(1, 4)
        ]
        super().setUpTestData()

    def test_availabilty(self):
        url = reverse('dupes', kwargs={'model_name': 'band'})
        self.assertTrue(resolve(url))

        # Assert that no queries are being done accessing the page; an oversight
        # led to the page querying for duplicates without any fields when request.
        # one query each for: session, user (must be a client thing)
        with self.assertNumQueries(2):
            self.client.get(url)

    def test_setup_exceptions(self):
        # Assert that setup() raises exceptions when:
        # - the kwarg 'model_name' is not provided OR
        # - when no model matching that name exists.
        view = self.view_class()
        request = self.get_request()
        with self.assertRaises(TypeError):
            view.setup(request)
        with self.assertRaises(ValueError):
            view.setup(request, model_name='WOOP')

    def test_post_redirects_to_self_after_merging(self):
        # Assert that post redirects back to itself after a merge.
        path = reverse('dupes', kwargs={'model_name': 'band'})
        request = self.post_request(path, data={ACTION_CHECKBOX_NAME: ['1', '2']})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        # Patch the as_view method of MergeViewWizarded to return None,
        # thereby emulating a successful merge without conflicts.
        mocked_as_view = Mock(return_value=Mock(return_value=None))
        with patch.object(MergeViewWizarded, 'as_view', new=mocked_as_view):
            response = view.post(request)
            self.assertEqual(response.url, path)

    def test_post_calls_merge_view(self):
        # Assert that a post request will call the merge view.
        model_admin = utils.get_model_admin_for_model(self.model)
        request = self.post_request(data={ACTION_CHECKBOX_NAME: ['1', '2']})
        view = self.get_view(request, kwargs={'model_name': 'band'})

        with patch.object(MergeViewWizarded, 'as_view') as mocked_as_view:
            view.post(request)
        self.assertEqual(mocked_as_view.call_count, 1)
        kwargs = mocked_as_view.call_args[1]
        self.assertIn('model_admin', kwargs)
        self.assertEqual(kwargs['model_admin'].__class__, model_admin.__class__)
        self.assertIn('queryset', kwargs)
        self.assertEqual(
            list(kwargs['queryset'].values_list('pk', flat=True)),
            [self.obj1.pk, self.obj2.pk]
        )

    def test_post_does_not_call_merge_view_with_no_selects(self):
        # Assert that a post request will NOT call the merge view when no items
        # in a sub list are selected for a merge.
        request = self.post_request(data={ACTION_CHECKBOX_NAME: []})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        with patch.object(MergeViewWizarded, 'as_view') as mocked_as_view:
            view.post(request)
        self.assertEqual(mocked_as_view.call_count, 0)

    def test_build_duplicates_items(self):
        # Assert that build_duplicates_items returns the correct items.
        changeform_url = unquote(
            reverse('admin:DBentry_band_change', args=['{pk}'])
        )
        link_template = '<a href="{url}" target="_blank">{name}</a>'

        request = self.get_request(data={'base': ['band_name', 'beschreibung']})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        form = view.get_form()
        # A validated and cleaned form is required.
        self.assertTrue(form.is_valid())

        items = view.build_duplicates_items(form)
        self.assertEqual(
            len(items), 1,
            msg="There should be only one set of duplicate objects."
        )
        self.assertEqual(
            len(items[0]), 2,
            msg="Should contain one set of duplicate objects and the link to "
            "their changelist."
        )
        self.assertEqual(
            len(items[0][0]), 3,
            msg="Should contain the three duplicate objects."
        )
        for dupe_item in items[0][0]:
            with self.subTest():
                self.assertEqual(
                    len(dupe_item), 3,
                    msg="Each dupe item is expected to have 3 attributes."
                )
                self.assertIsInstance(
                    dupe_item[0], self.model,
                    msg="Duplicate object should be an instance of "
                    "{!s}.".format(self.model)
                )
                expected_link = link_template.format(
                    url=changeform_url.format(pk=dupe_item[0].pk),
                    name=str(dupe_item[0])
                )
                self.assertEqual(
                    dupe_item[1], expected_link,
                    msg="Should be link to change form of object."
                )
                self.assertEqual(
                    dupe_item[2], ['Beep', ''],
                    msg="Should be the duplicate object's values of the "
                    "fields the duplicates were found with."
                )
        # Investigate the link to the changelist:
        cl_link = items[0][1]
        self.assertIsInstance(cl_link, str)
        match = re.match(r'<a (.*)>(\w+)</a>', cl_link)
        self.assertTrue(
            match, msg="Should be the link to the changelist of the duplicate objects.")
        attrs, content = match.groups()
        self.assertEqual(content, 'Änderungsliste')
        attrs = dict(attr.replace('"', '').split("=", 1) for attr in attrs.split(" "))
        self.assertIn("href", attrs)
        self.assertEqual(
            attrs['href'].count('?'), 1,
            msg="Changelist url should be of format <changelist>?id__in=[ids]")
        cl_url, query_params = attrs['href'].split('?')
        self.assertEqual(reverse('admin:DBentry_band_changelist'), cl_url)
        self.assertEqual("id__in=" + ",".join(str(o.pk) for o in self.test_data), query_params)
        self.assertIn("target", attrs)
        self.assertEqual(attrs['target'], '_blank')
        self.assertIn("class", attrs)
        self.assertEqual(attrs["class"], "button")

    def test_build_duplicates_headers(self):
        # Assert that the correct (field.verbose_name capitalized) headers are
        # returned. Headers are built from the labels of the established choices.
        test_data = [
            ({'base': ['band_name']}, 'Bandname'),
            ({'m2m': ['genre']}, 'Genre'),
            ({'reverse': ['bandalias__alias']}, 'Alias')
        ]
        for request_data, expected in test_data:
            with self.subTest(data=request_data):
                request = self.get_request(data=request_data)
                view = self.get_view(request, kwargs={'model_name': 'band'})
                form = view.get_form()
                self.assertTrue(form.is_valid())
                headers = view.build_duplicates_headers(form)
                self.assertIn(expected, headers)

    def test_build_duplicates_headers_grouped_choices(self):
        request = self.get_request(data={'reverse': ['bandalias__alias']})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        form = view.get_form()
        form.fields['reverse'].choices = [
            ('Alias', [('bandalias__alias', 'Alias')])
        ]
        self.assertTrue(form.is_valid())
        headers = view.build_duplicates_headers(form)
        self.assertIn('Alias', headers)


class TestUnusedObjectsView(ViewTestCase):

    view_class = UnusedObjectsView

    @classmethod
    def setUpTestData(cls):
        cls.artikel1 = make(_models.Artikel)
        cls.artikel2 = make(_models.Artikel)

        cls.unused = make(_models.Genre)
        cls.used_once = make(_models.Genre)
        cls.artikel1.genre.add(cls.used_once)
        cls.used_twice = make(_models.Genre)
        cls.artikel1.genre.add(cls.used_twice)
        cls.artikel2.genre.add(cls.used_twice)
        cls.test_data = [cls.unused, cls.used_once, cls.used_twice]
        super().setUpTestData()

    def test_get_queryset(self):
        # Assert that the returned querysets return the correct amount of
        # 'unused' records.
        view = self.get_view(request=self.get_request())
        for limit in [0, 1, 2]:
            relations, queryset = view.get_queryset(_models.Genre, limit)
            with self.subTest(limit=limit):
                self.assertEqual(queryset.count(), limit + 1)

    @patch.object(UnusedObjectsView, 'build_items')
    @patch.object(UnusedObjectsView, 'render_to_response')
    def test_get_form_invalid(self, mocked_render, mocked_build_items):
        # Assert that the get response with an invalid form does not contain
        # the context variable 'items'.
        data={'get_unused': True, 'model_select': 'NotAModel', 'limit': 0}
        request = self.get_request(data=data)
        view = self.get_view(request=request)
        self.assertFalse(view.get_form().is_valid())
        view.get(request=request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertNotIn('items', context.keys())

    @patch.object(UnusedObjectsView, 'build_items')
    @patch.object(UnusedObjectsView, 'render_to_response')
    def test_get_form_valid(self, mocked_render, mocked_build_items):
        # Assert that the get response with a valid form contains the
        # context variable 'items'.
        data={'get_unused': True, 'model_select': 'artikel', 'limit': 0}
        request = self.get_request(data=data)
        view = self.get_view(request=request)
        self.assertTrue(view.get_form().is_valid())
        view.get(request=request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertIn('items', context.keys())

    def test_build_items(self):
        # Check the contents of the list that build_items returns.
        relations = OrderedDict()
        relations['artikel_rel'] = {
            'related_model': _models.Artikel,
            'counts': {self.unused.pk: '0', self.used_once.pk: '1'}
        }
        queryset = _models.Genre.objects.filter(pk__in=[self.unused.pk, self.used_once.pk])

        items = self.get_view(self.get_request()).build_items(relations, queryset)
        self.assertEqual(len(items), 2)
        # Sort via the links to the change pages (lower ID should come first):
        unused, used_once = sorted(items, key=lambda tpl: tpl[0])
        url = reverse("admin:DBentry_genre_change", args=[self.unused.pk])
        self.assertIn(url, unused[0])
        self.assertIn("Artikel (0)", unused[1])
        url = reverse("admin:DBentry_genre_change", args=[self.used_once.pk])
        self.assertIn(url, used_once[0])
        self.assertIn("Artikel (1)", used_once[1])

    @patch.object(UnusedObjectsView, 'build_items')
    @patch.object(UnusedObjectsView, 'render_to_response')
    def test_get_changelist_link(self, mocked_render, mocked_build_items):
        # Assert that the response's context contains a link to the changelist
        # listing all the unused objects.
        data={'get_unused': True, 'model_select': 'genre', 'limit': 0}
        request = self.get_request(data=data)
        view = self.get_view(request=request)
        self.assertTrue(view.get_form().is_valid())
        view.get(request=request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertIn('changelist_link', context.keys())
        link = context['changelist_link']
        cl_url = reverse('admin:DBentry_genre_changelist') + "?id__in=" + str(self.unused.pk)
        # Too lazy to unpack the html element with regex to check its other attributes.
        self.assertIn(cl_url, link)
