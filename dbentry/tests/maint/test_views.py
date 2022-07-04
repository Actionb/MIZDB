from collections import OrderedDict
from unittest.mock import patch

from django.urls import reverse
from django.utils.http import unquote

from dbentry import models as _models
from dbentry.factory import make
from dbentry.maint.views import (
    DuplicateModelSelectView, DuplicateObjectsView, ModelSelectView, UnusedObjectsView,
    find_duplicates
)
from dbentry.tests.base import DataTestCase, ViewTestCase
from dbentry.tests.mixins import TestDataMixin


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
        # Assert that get_success_url returns a resolvable url.
        view = self.get_view(self.get_request(), next_view='admin:index')
        with patch.object(view, 'get_next_view_kwargs', return_value={}):
            self.assertEqual(view.get_success_url(), '/admin/')

    def test_get_next_view_kwargs(self):
        view = self.get_view(self.get_request(data={'model_select': 'some_model'}))
        self.assertEqual(view.get_next_view_kwargs(), {'model_name': 'some_model'})


class TestDuplicateObjectsView(TestDataMixin, ViewTestCase):
    model = _models.Musiker
    view_class = DuplicateObjectsView

    @classmethod
    def setUpTestData(cls):
        beschreibung = (
            "This description is rather long and should be truncated to 100 characters "
            "so that it doesn't occupy too much space in the overview."
        )
        cls.genre1 = make(_models.Genre, genre='Rock')
        cls.genre2 = make(_models.Genre, genre='Soul')
        cls.person1 = person1 = make(_models.Person, vorname='Alice', nachname='Tester')
        cls.person2 = person2 = make(_models.Person, vorname='Bob', nachname='Tester')
        # Do not use make(); it would do a get_or_create(kuenstler_name='Dupe')
        # when creating the second object, returning the first.
        cls.dupe_1 = cls.model.objects.create(
            kuenstler_name='Dupe', beschreibung=beschreibung, person=person1
        )
        cls.dupe_2 = cls.model.objects.create(
            kuenstler_name='Dupe', beschreibung=beschreibung, person=person2
        )
        # Add another group of simple duplicates:
        cls.dupe_3 = cls.model.objects.create(kuenstler_name='Zulu')
        cls.dupe_4 = cls.model.objects.create(kuenstler_name='Zulu')
        # And a control object that shouldn't show up as a duplicate:
        cls.other = cls.model.objects.create(kuenstler_name='Other')

        # noinspection PyUnresolvedReferences
        cls.dupe_1.genre.set([cls.genre1, cls.genre2])
        # noinspection PyUnresolvedReferences
        cls.dupe_2.genre.set([cls.genre1, cls.genre2])
        super().setUpTestData()

    def test(self):
        # Go to the model select part:
        response = self.client.get(reverse('dupes_select'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.resolver_match.func.__name__,
            DuplicateModelSelectView.as_view().__name__
        )

        # Select model 'musiker'. It should redirect us to the DuplicateObjectsView
        # for that model to select the fields for the search and the overview.
        response = self.client.get(
            reverse('dupes_select'),
            data={'submit': '1', 'model_select': 'musiker'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/dupes.html')
        context = response.context
        self.assertEqual(context['title'], 'Duplikate: Musiker')
        self.assertEqual(context['breadcrumbs_title'], 'Musiker')
        # no overview should be displayed yet:
        self.assertNotIn('headers', context)
        self.assertNotIn('items', context)

        # Select the fields. The duplicates should then be displayed.
        response = self.client.get(
            reverse('dupes', kwargs={'model_name': 'musiker'}),
            data={
                'get_duplicates': '1',
                'select': ['kuenstler_name'],
                'display': ['kuenstler_name', 'genre__genre']
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/dupes.html')
        context = response.context
        self.assertEqual(context['title'], 'Duplikate: Musiker')
        self.assertEqual(context['breadcrumbs_title'], 'Musiker')
        self.assertEqual(context['headers'], ['Künstlername', 'Genre'])
        self.assertTrue(context['items'])

    def test_build_duplicates_items(self):
        changelist_url = reverse('admin:dbentry_musiker_changelist')
        changeform_url = unquote(
            reverse('admin:dbentry_musiker_change', args=['{pk}'])
        )
        link_template = '<a href="{url}" target="_blank">{name}</a>'

        def get_link(obj):
            return link_template.format(url=changeform_url.format(pk=obj.pk), name=str(obj))

        request_data = {
            'select': ['kuenstler_name'],
            'display': ['kuenstler_name', 'beschreibung', 'person', 'genre__genre']
        }
        request = self.get_request(data=request_data)
        view = self.get_view(request, kwargs={'model_name': 'musiker'})
        form = view.get_form()
        # A validated and cleaned form is required.
        self.assertTrue(form.is_valid(), msg=form.errors)

        items = view.build_duplicates_items(form)
        self.assertEqual(
            len(items), 2,
            msg=f"There should be two sets of duplicate objects. {items}"
        )

        ############################################################################################
        # Check the first set of duplicates:
        ############################################################################################
        self.assertEqual(
            len(items[0]), 2,
            msg="Should contain one set of duplicate objects and the link to their changelist."
        )
        # Check the link to the changelist:
        cl_link = items[0][1]
        self.assertIsInstance(cl_link, str)
        self.assertIn(f"{changelist_url}?id__in={self.dupe_1.pk},{self.dupe_2.pk}", cl_link)
        self.assertIn('target="_blank"', cl_link)
        self.assertIn('class="button"', cl_link)
        self.assertIn('style="padding: 10px 15px;', cl_link)
        self.assertIn('>Änderungsliste</a>', cl_link)

        self.assertEqual(len(items[0][0]), 2, msg="Should contain the two duplicate objects.")

        # Check the duplicate items:
        expected_beschreibung = (
            "This description is rather long and should be truncated to 100 characters so that it "
            "doesn't occupy  [...]"
        )
        dupe1, dupe2 = items[0][0]
        expected = (
            self.dupe_1,
            get_link(self.dupe_1),
            ['Dupe', expected_beschreibung, 'Alice Tester', 'Rock, Soul']
        )
        self.assertEqual(dupe1, expected)
        expected = (
            self.dupe_2,
            get_link(self.dupe_2),
            ['Dupe', expected_beschreibung, 'Bob Tester', 'Rock, Soul']
        )
        self.assertEqual(dupe2, expected)

        ############################################################################################
        # Check the second set of duplicates:
        ############################################################################################
        self.assertEqual(
            len(items[1]), 2,
            msg="Should contain one set of duplicate objects and the link to their changelist."
        )
        # Check the link to the changelist:
        cl_link = items[1][1]
        self.assertIsInstance(cl_link, str)
        self.assertIn(f"{changelist_url}?id__in={self.dupe_3.pk},{self.dupe_4.pk}", cl_link)
        self.assertIn('target="_blank"', cl_link)
        self.assertIn('class="button"', cl_link)
        self.assertIn('style="padding: 10px 15px;', cl_link)
        self.assertIn('>Änderungsliste</a>', cl_link)

        self.assertEqual(len(items[1][0]), 2, msg="Should contain the two duplicate objects.")
        dupe1, dupe2 = items[1][0]
        self.assertEqual(dupe1, (self.dupe_3, get_link(self.dupe_3), ['Zulu', '', '', '']))
        self.assertEqual(dupe2, (self.dupe_4, get_link(self.dupe_4), ['Zulu', '', '', '']))

    def test_setup_exception(self):
        """Assert that setup() raises a TypeError when 'model_name' kwarg is missing."""
        with self.assertRaises(TypeError):
            self.view_class().setup(self.get_request())

    def test_headers(self):
        """Assert that the headers for the overview table are added to the template context."""
        request_data = {
            'get_duplicates': '1',
            'select': ['band_name'],
            'display': ['band_name', 'genre__genre']
        }
        request = self.get_request(data=request_data)
        view = self.get_view(request, kwargs={'model_name': 'band'})
        with patch.object(view, 'build_duplicates_items'):
            with patch.object(view, 'render_to_response') as render_mock:
                view.get(request)
                context = render_mock.call_args[0][0]
                self.assertEqual(context['headers'], ['Bandname', 'Genre'])
                self.assertEqual(context['headers_width'], '40')

    def test_get_context_data(self):
        view = self.get_view(self.get_request(), kwargs={'model_name': 'band'})
        context = view.get_context_data()
        self.assertEqual(context['title'], 'Duplikate: Band')
        self.assertEqual(context['breadcrumbs_title'], 'Band')


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
    def test_get_form_invalid(self, mocked_render, _mocked_build_items):
        # Assert that the get response with an invalid form does not contain
        # the context variable 'items'.
        data = {'get_unused': True, 'model_select': 'NotAModel', 'limit': 0}
        request = self.get_request(data=data)
        view = self.get_view(request=request)
        self.assertFalse(view.get_form().is_valid())
        view.get(request=request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertNotIn('items', context.keys())

    @patch.object(UnusedObjectsView, 'build_items')
    @patch.object(UnusedObjectsView, 'render_to_response')
    def test_get_form_valid(self, mocked_render, _mocked_build_items):
        # Assert that the get response with a valid form contains the
        # context variable 'items'.
        data = {'get_unused': True, 'model_select': 'artikel', 'limit': 0}
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
        # Sorting by "model_name (count)" since we know count is either 0 or 1:
        # (sorting by url will sort an url with pk="10" before one with pk="9")
        unused, used_once = sorted(items, key=lambda tpl: tpl[1])
        url = reverse("admin:dbentry_genre_change", args=[self.unused.pk])
        self.assertIn(url, unused[0])
        self.assertIn("Artikel (0)", unused[1])
        url = reverse("admin:dbentry_genre_change", args=[self.used_once.pk])
        self.assertIn(url, used_once[0])
        self.assertIn("Artikel (1)", used_once[1])

    @patch.object(UnusedObjectsView, 'build_items')
    @patch.object(UnusedObjectsView, 'render_to_response')
    def test_get_changelist_link(self, mocked_render, _mocked_build_items):
        # Assert that the response's context contains a link to the changelist
        # listing all the unused objects.
        data = {'get_unused': True, 'model_select': 'genre', 'limit': 0}
        request = self.get_request(data=data)
        view = self.get_view(request=request)
        self.assertTrue(view.get_form().is_valid())
        view.get(request=request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertIn('changelist_link', context.keys())
        link = context['changelist_link']
        cl_url = reverse('admin:dbentry_genre_changelist') + "?id__in=" + str(self.unused.pk)
        # Too lazy to unpack the html element with regex to check its other attributes.
        self.assertIn(cl_url, link)


class TestFindDuplicates(DataTestCase):
    model = _models.Musiker

    @classmethod
    def setUpTestData(cls):
        # Do not use make(); it would do a get_or_create(kuenstler_name='Dupe')
        # when creating the second object, returning the first.
        cls.dupe_1 = cls.model.objects.create(kuenstler_name='Dupe', beschreibung='foo')
        cls.dupe_2 = cls.model.objects.create(kuenstler_name='Dupe', beschreibung='bar')
        cls.other = cls.model.objects.create(kuenstler_name='Test')
        super().setUpTestData()

    def test(self):
        self.assertNotEqual(self.dupe_1.pk, self.dupe_2.pk)
        duplicates = find_duplicates(self.model.objects.all(), fields=['kuenstler_name'])
        self.assertEqual(len(duplicates), 2)
        self.assertIn(self.dupe_1, duplicates)
        self.assertIn(self.dupe_2, duplicates)

        # There should be no duplicates, if the 'beschreibung' field is included
        # as the field values differ.
        duplicates = find_duplicates(
            self.model.objects.all(), fields=['kuenstler_name', 'beschreibung']
        )
        self.assertEqual(len(duplicates), 0)

    def test_relations(self):
        """Assert that values from relations can be included when checking for duplicates."""
        self.dupe_1.musikeralias_set.create(alias='Foo')
        duplicates = find_duplicates(
            self.model.objects.all(), fields=['kuenstler_name', 'musikeralias__alias']
        )
        self.assertEqual(len(duplicates), 0)

        self.dupe_2.musikeralias_set.create(alias='Foo')
        duplicates = find_duplicates(
            self.model.objects.all(), fields=['kuenstler_name', 'musikeralias__alias']
        )
        self.assertEqual(len(duplicates), 2)

        # other shouldn't be a duplicate just because of the matching alias
        self.dupe_2.musikeralias_set.update(alias='Bar')  # aliases no longer match
        self.other.musikeralias_set.create(alias='Foo')
        duplicates = find_duplicates(
            self.model.objects.all(), fields=['kuenstler_name', 'musikeralias__alias']
        )
        self.assertEqual(len(duplicates), 0)
