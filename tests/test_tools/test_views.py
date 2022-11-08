from collections import OrderedDict
from unittest.mock import DEFAULT, Mock, patch

from django.test import override_settings
from django.urls import reverse
from django.utils.http import unquote

from dbentry import models as _models
from dbentry.tools.views import (
    DuplicateModelSelectView, DuplicateObjectsView, MIZSiteSearch, ModelSelectView, SiteSearchView,
    UnusedObjectsView,
    find_duplicates
)
from tests.case import DataTestCase, ViewTestCase
from tests.factory import make
from .models import Band, Genre, Musiker, Person


@override_settings(ROOT_URLCONF='tests.test_tools.urls')
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
        """
        Assert that get() redirects to the success url if the view's
        submit_name is in the GET query dict.
        """
        request = self.get_request(data={'testing': 'yes'})
        view = self.get_view(request, submit_name='testing')
        with patch.object(view, 'get_success_url', return_value='test_tools:index'):
            response = view.get(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/test_tools/')

    def test_get_success_url(self):
        """Assert that get_success_url returns a resolvable url."""
        view = self.get_view(self.get_request(), next_view='test_tools:index')
        with patch.object(view, 'get_next_view_kwargs', return_value={}):
            self.assertEqual(view.get_success_url(), '/test_tools/')

    def test_get_next_view_kwargs(self):
        view = self.get_view(self.get_request(data={'model_select': 'some_model'}))
        self.assertEqual(view.get_next_view_kwargs(), {'model_name': 'some_model'})


@override_settings(ROOT_URLCONF='tests.test_tools.urls')
class TestDuplicateObjectsView(ViewTestCase):
    model = Musiker
    view_class = DuplicateObjectsView

    @classmethod
    def setUpTestData(cls):
        beschreibung = (
            "This description is rather long and should be truncated to 100 characters "
            "so that it doesn't occupy too much space in the overview."
        )
        cls.genre1 = make(Genre, genre='Rock')
        cls.genre2 = make(Genre, genre='Soul')
        cls.person1 = person1 = make(Person, name='Alice Tester')
        cls.person2 = person2 = make(Person, name='Bob Tester')

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
        cls.dupe_1.genres.set([cls.genre1, cls.genre2])
        # noinspection PyUnresolvedReferences
        cls.dupe_2.genres.set([cls.genre1, cls.genre2])
        super().setUpTestData()

    def test(self):
        # Go to the model select part:
        response = self.get_response(reverse('dupes_select'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.resolver_match.func.__name__,
            DuplicateModelSelectView.as_view().__name__
        )

        # Select model 'musiker'. It should redirect us to the DuplicateObjectsView
        # for that model to select the fields for the search and the overview.
        response = self.client.get(
            reverse('dupes_select'),
            data={'submit': '1', 'model_select': 'test_tools.musiker'},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tools/dupes.html')
        context = response.context
        self.assertEqual(context['title'], 'Duplikate: Musiker')
        self.assertEqual(context['breadcrumbs_title'], 'Musiker')
        # no overview should be displayed yet:
        self.assertNotIn('headers', context)
        self.assertNotIn('items', context)

        # Select the fields. The duplicates should then be displayed.
        response = self.client.get(
            reverse('dupes', kwargs={'model_name': 'test_tools.musiker'}),
            data={
                'get_duplicates': '1',
                'select': ['kuenstler_name'],
                'display': ['kuenstler_name', 'genres__genre']
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tools/dupes.html')
        context = response.context
        self.assertEqual(context['title'], 'Duplikate: Musiker')
        self.assertEqual(context['breadcrumbs_title'], 'Musiker')
        self.assertEqual(context['headers'], ['Künstlername', 'Genres'])
        self.assertTrue(context['items'])

    def test_build_duplicates_items(self):
        changelist_url = reverse('test_tools:test_tools_musiker_changelist')
        changeform_url = unquote(
            reverse('test_tools:test_tools_musiker_change', args=['{pk}'])
        )
        link_template = '<a href="{url}" target="_blank">{name}</a>'

        def get_link(obj):
            return link_template.format(url=changeform_url.format(pk=obj.pk), name=str(obj))

        request_data = {
            'select': ['kuenstler_name'],
            'display': ['kuenstler_name', 'beschreibung', 'person', 'genres__genre']
        }
        request = self.get_request(data=request_data)
        view = self.get_view(request, kwargs={'model_name': 'test_tools.musiker'})
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

    @patch('dbentry.base.views.MIZAdminMixin.get_context_data', new=Mock(return_value={}))
    def test_headers(self):
        """Assert that the headers for the overview table are added to the template context."""
        request_data = {
            'get_duplicates': '1',
            'select': ['kuenstler_name'],
            'display': ['kuenstler_name', 'genres__genre']
        }
        request = self.get_request(data=request_data)
        view = self.get_view(request, kwargs={'model_name': 'test_tools.musiker'})
        with patch.object(view, 'build_duplicates_items'):
            with patch.object(view, 'render_to_response') as render_mock:
                view.get(request)
                context = render_mock.call_args[0][0]
                self.assertEqual(context['headers'], ['Künstlername', 'Genres'])
                self.assertEqual(context['headers_width'], '40')

    @patch('dbentry.base.views.MIZAdminMixin.get_context_data', new=Mock(return_value={}))
    def test_get_context_data(self):
        view = self.get_view(self.get_request(), kwargs={'model_name': 'test_tools.musiker'})
        context = view.get_context_data()
        self.assertEqual(context['title'], 'Duplikate: Musiker')
        self.assertEqual(context['breadcrumbs_title'], 'Musiker')


@override_settings(ROOT_URLCONF='tests.test_tools.urls')
class TestUnusedObjectsView(ViewTestCase):
    view_class = UnusedObjectsView

    @classmethod
    def setUpTestData(cls):
        cls.musiker1 = make(Musiker)
        cls.musiker2 = make(Musiker)

        cls.unused = make(Genre)
        cls.used_once = make(Genre)
        cls.musiker1.genres.add(cls.used_once)
        cls.used_twice = make(Genre)
        cls.musiker1.genres.add(cls.used_twice)
        cls.musiker2.genres.add(cls.used_twice)
        cls.test_data = [cls.unused, cls.used_once, cls.used_twice]
        super().setUpTestData()

    def test_get_form_kwargs(self):
        """
        Assert that 'data' is only included in the form kwargs, when the request
        data contains the 'submit_name' (when the user has previously pressed
        the submit button).
        """
        view = self.get_view(request=self.get_request())
        self.assertNotIn('data', view.get_form_kwargs())
        view = self.get_view(request=self.get_request(data={'get_unused': '1'}))
        self.assertIn('data', view.get_form_kwargs())

    def test_get(self):
        """Assert that certain items are added to the template context."""
        request = self.get_request(data={'get_unused': True, 'model_select': 'artikel', 'limit': 0})
        view = self.get_view(request=request)
        self.assertTrue(view.get_form().is_valid())
        with patch.multiple(
                view, build_items=DEFAULT, render_to_response=DEFAULT,
                get_context_data=Mock(return_value={})
        ) as mocks:
            view.get(request=request)
        self.assertTrue(mocks['render_to_response'].called)
        context = mocks['render_to_response'].call_args[0][0]
        self.assertIn('items', context)
        self.assertIn('form', context)
        self.assertIn('changelist_link', context)

    def test_get_queryset(self):
        """
        Assert that the returned queryset return the expected amount of records
        that are 'unused'.
        """
        # Testing with Musiker model here, instead of Genre, due to the variety
        # of relations that model has.
        _unused = make(Musiker)
        view = self.get_view(request=self.get_request())
        for limit in [0, 1, 2]:
            relations, queryset = view.get_queryset(Musiker, limit)
            with self.subTest(limit=limit):
                self.assertEqual(queryset.count(), limit + 1)

    def test_get_queryset_ignores_self_relations(self):
        """
        Assert that get_queryset does not include self relations in its query
        for related objects.
        """
        obj = make(Musiker)
        _other = make(Musiker, andere=obj)
        view = self.get_view(request=self.get_request())
        _rels, unused_qs = view.get_queryset(Musiker, 0)
        # 'obj' has no other relations other than to 'other', which is a self
        # relation and should be ignored. That means 'obj' should appear in a
        # queryset of unused objects.
        self.assertIn(obj, unused_qs)

    def test_build_items(self):
        """Check the contents of the list that build_items returns."""
        relations = OrderedDict()
        relations['artikel_rel'] = {
            'related_model': Musiker,
            'counts': {self.unused.pk: '0', self.used_once.pk: '1'}
        }
        queryset = Genre.objects.filter(pk__in=[self.unused.pk, self.used_once.pk])

        items = self.get_view(self.get_request()).build_items(relations, queryset)
        self.assertEqual(len(items), 2)
        # Sorting by "model_name (count)" since we know count is either 0 or 1:
        # (sorting by url will sort an url with pk="10" before one with pk="9")
        unused, used_once = sorted(items, key=lambda tpl: tpl[1])
        url = reverse("test_tools:test_tools_genre_change", args=[self.unused.pk])
        self.assertIn(url, unused[0])
        self.assertIn("Musiker (0)", unused[1])
        url = reverse("test_tools:test_tools_genre_change", args=[self.used_once.pk])
        self.assertIn(url, used_once[0])
        self.assertIn("Musiker (1)", used_once[1])


class TestFindDuplicates(DataTestCase):
    model = Musiker

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
        self.dupe_1.genres.create(genre='Foo')
        duplicates = find_duplicates(
            self.model.objects.all(), fields=['kuenstler_name', 'genres__genre']
        )
        self.assertEqual(len(duplicates), 0)

        self.dupe_2.genres.create(genre='Foo')
        duplicates = find_duplicates(
            self.model.objects.all(), fields=['kuenstler_name', 'genres__genre']
        )
        self.assertEqual(len(duplicates), 2)

        # other shouldn't be a duplicate just because of the matching genre
        self.dupe_2.genres.update(genre='Bar')  # genres no longer match
        self.other.genres.create(genre='Foo')
        duplicates = find_duplicates(
            self.model.objects.all(), fields=['kuenstler_name', 'genres__genre']
        )
        self.assertEqual(len(duplicates), 0)


@override_settings(ROOT_URLCONF='tests.test_tools.urls')
class TestSiteSearchView(ViewTestCase):
    # noinspection PyPep8Naming
    class view_class(SiteSearchView):
        app_label = 'test_tools'  # use test models

        def _search(self, model, q):
            # noinspection PyUnresolvedReferences
            opts = model._meta
            field = ''
            if opts.model_name == 'band':
                field = 'name'
            elif opts.model_name == 'musiker':
                field = 'kuenstler_name'
            elif opts.model_name == 'genre':
                field = 'genre'
            if not field:
                return []
            # noinspection PyUnresolvedReferences
            qs = model.objects.filter(**{field + '__icontains': q})
            return qs

    @classmethod
    def setUpTestData(cls):
        make(Musiker, kuenstler_name='Sharon Silva')
        super().setUpTestData()

    def test_get_result_list(self):
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertEqual(len(results), 1)
        self.assertIn('Musiker (1)', results[0])

    def test_get_result_list_no_perms(self):
        """
        Assert that get_result_list doesn't return changelist links for users
        who have no permission to view those changelists.
        """
        view = self.get_view(request=self.get_request(user=self.noperms_user))
        results = view.get_result_list('Silva')
        self.assertFalse(results)

    def test_get_result_list_no_changelist(self):
        """
        Assert that get_result_list doesn't return changelist links for models
        that do not have a registered ModelAdmin.
        """
        make(Person, name='Sharon Silva')  # no ModelAdmin for this model
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertEqual(len(results), 1)
        self.assertIn('Musiker (1)', results[0])

    def test_get_result_list_sorted(self):
        """
        Assert that the result list is sorted alphabetically by the models'
        object names.
        """
        make(Band, name='Silva')
        make(Genre, genre='Silva Music')
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertTrue(results)
        self.assertEqual(len(results), 3)
        self.assertIn('Bands (1)', results[0])
        self.assertIn('Genres (1)', results[1])
        self.assertIn('Musiker (1)', results[2])

    @patch.object(SiteSearchView, 'render_to_response')
    def test_get(self, render_mock):
        """Assert that render_to_response is called with the expected context."""
        request = self.get_request(data={'q': 'Silva'})
        self.get_view(request).get(request)
        self.assertTrue(render_mock.called)
        context = render_mock.call_args[0][0]
        self.assertIn('q', context.keys())
        self.assertEqual(context['q'], 'Silva')
        self.assertIn('results', context.keys())
        results = context['results']
        self.assertTrue(results)
        self.assertEqual(len(results), 1)
        self.assertIn('?q=Silva', results[0])
        self.assertIn('Musiker (1)', results[0])

    @patch.object(SiteSearchView, 'get_result_list')
    @patch.object(SiteSearchView, 'render_to_response')
    def test_get_no_q(self, _render_mock, get_result_list_mock):
        """get_result_list should not be called when no search term was provided."""
        for data in ({}, {'q': ''}):
            with self.subTest(request_data=data):
                request = self.get_request(data=data)
                self.get_view(request).get(request)
                self.assertFalse(get_result_list_mock.called)


class TestMIZSiteSearch(ViewTestCase):
    view_class = MIZSiteSearch

    @classmethod
    def setUpTestData(cls):
        make(_models.Musiker, kuenstler_name='Sharon Silva')
        make(_models.Band, band_name='Silvas')
        make(_models.Veranstaltung, name='Silva Konzert')
        super().setUpTestData()

    def test_get_models_no_m2m_models(self):
        """Assert that _get_models filters out models subclassing BaseM2MModel."""
        view = self.get_view(self.get_request())
        models = view._get_models('dbentry')
        from dbentry.base.models import BaseModel, BaseM2MModel
        self.assertFalse(any(issubclass(m, BaseM2MModel) for m in models))
        self.assertTrue(all(issubclass(m, BaseModel) for m in models))

    def test_get_result_list(self):
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertTrue(results)
        self.assertEqual(len(results), 3)
        self.assertIn('Bands (1)', results[0])
        self.assertIn('Musiker (1)', results[1])
        self.assertIn('Veranstaltungen (1)', results[2])
