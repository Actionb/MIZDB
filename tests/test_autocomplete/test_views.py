import json
from unittest import skip
from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.db.models import BooleanField, Count, ExpressionWrapper, Q, QuerySet
from django.urls import reverse, reverse_lazy
from django.utils.translation import override as translation_override

import dbentry.models as _models
from dbentry.ac.views import (
    ACAutor, ACBase, ACAusgabe, ACBuchband, ACMagazin, ACPerson, ACTabular,
    ContentTypeAutocompleteView,
    GND, GNDPaginator, Paginator, parse_autor_name
)
from dbentry.ac.widgets import EXTRA_DATA_KEY, GENERIC_URL_NAME

from tests.case import MIZTestCase, RequestTestCase, ViewTestCase
from tests.factory import make
from tests.mixins import LoggingTestMixin
from tests.test_autocomplete.models import Band, Musiker, Genre


def get_result_ids(response):
    """Return the ids of the results of an autocomplete request."""
    return [
        d['id']
        for d in json.loads(response.content)['results']
        if not d.get('create_id', False)
    ]


class ACViewTestCase(ViewTestCase):

    model = None

    def get_view(self, request=None, args=None, kwargs=None, model=None,
                 create_field=None, forwarded=None, q='', **initkwargs):
        initkwargs = {
            'model': model or getattr(self.view_class, 'model', None) or self.model,
            'create_field': create_field or getattr(model, 'create_field', None),
            **initkwargs
        }
        view = super().get_view(request, args, kwargs, **initkwargs)
        if not getattr(view, 'forwarded', None):
            view.forwarded = forwarded or {}
        if not getattr(view, 'q', None):
            view.q = q
        return view


# noinspection PyUnresolvedReferences
class ACViewTestMethodMixin(LoggingTestMixin):
    # TODO: remove this mixin and apply the tests directly in each test case
    view_class = ACBase
    has_alias = True
    alias_accessor_name = ''

    def test_get_ordering(self):
        """
        Assert that get_ordering returns either the value of the ordering
        attribute or the default ordering of the model.
        """
        view = self.get_view()
        if view.ordering:
            self.assertEqual(view.get_ordering(), view.ordering)
        else:
            self.assertEqual(view.get_ordering(), self.model._meta.ordering)

    def test_get_search_results(self):
        """
        Test that an object can be found by querying for the data that was used
        in its creation.
        """
        if not self.raw_data:
            return
        view = self.get_view()
        for data in self.raw_data:
            for field, value in data.items():
                with self.subTest(field=field, value=value):
                    q = str(value)
                    result = view.get_search_results(self.queryset, q)
                    if not result:
                        fail_msg = (
                            f"Could not find test object by querying for field {field!r} "
                            f"with search term {q!r}"
                        )
                        self.fail(fail_msg)
                    if isinstance(result, list):
                        if isinstance(result[-1], (list, tuple)):
                            result = (o[0] for o in result)
                        else:
                            result = (o.pk for o in result)
                    else:
                        result = result.values_list('pk', flat=True)
                    self.assertIn(self.obj1.pk, result)

    def test_get_search_results_alias(self):
        """Assert that an object can be found through its aliases."""
        if not self.has_alias:
            return
        if not self.alias_accessor_name:
            # No point in running this test
            self.warn('Test aborted: no alias accessor name set.')
            return

        # Find an object through its alias
        alias = getattr(self.obj1, self.alias_accessor_name).first()
        if alias is None:
            self.warn('Test aborted: queryset of aliases is empty.')
            return
        view = self.get_view()
        q = str(alias)
        result = [obj.pk for obj in view.get_search_results(self.queryset, q)]
        self.assertTrue(
            result,
            msg=f"View returned no results when querying for alias: {q}"
        )
        self.assertIn(self.obj1.pk, result)

    @translation_override(language=None)
    def test_get_create_option(self):
        request = self.get_request()
        view = self.get_view(request)
        create_option = view.get_create_option(context={'object_list': []}, q='Beep')
        if view.create_field:
            self.assertEqual(len(create_option), 1)
            self.assertEqual(create_option[0].get('id'), 'Beep')
            self.assertEqual(create_option[0].get('text'), 'Create "Beep"')
            self.assertTrue(create_option[0].get('create_id'))
        else:
            self.assertEqual(len(create_option), 0)

    def test_create_object_with_log_entry(self):
        # request set on view, log entry should be created
        request = self.get_request()
        view = self.get_view(request)
        if view.create_field:
            obj = view.create_object('Boop')
            self.assertLoggedAddition(obj)

    def test_create_object_strip(self):
        # Assert that the input is stripped for object creation:
        request = self.get_request()
        view = self.get_view(request)
        if view.create_field:
            obj = view.create_object('   Boop\n')
            self.assertEqual(getattr(obj, view.create_field), 'Boop')


class TestAutorNameParser(MIZTestCase):

    def test(self):
        names = [
            ('Alice Testman', ('Alice', 'Testman', '')),
            ('Testman, Alice', ('Alice', 'Testman', '')),
            ('Alice Bob Testman', ('Alice Bob', 'Testman', '')),
            ('Alice "AT" Testman', ('Alice', 'Testman', 'AT')),
            ('Alice Testman (AT)', ('Alice', 'Testman', 'AT')),
            ('Testman, Alice (AT)', ('Alice', 'Testman', 'AT')),
            ('Testman (AT)', ('', 'Testman', 'AT')),
            ('(AT)', ('', '', 'AT'))
        ]
        for name, expected in names:
            with self.subTest(name=name):
                self.assertEqual(parse_autor_name(name), expected)

    def test_kuerzel_max_length(self):
        """
        Assert that the kuerzel is shortened, so that its length doesn't exceed
        the model field max_length of 8.
        """
        _v, _n, kuerzel = parse_autor_name('Alice (Supercalifragilisticexpialidocious) Tester')
        # noinspection SpellCheckingInspection
        self.assertEqual(kuerzel, 'Supercal')


class TestACBase(ACViewTestCase):
    """Unit tests for ACBase."""

    view_class = ACBase
    model = Band

    @classmethod
    def setUpTestData(cls):
        cls.genre = genre = make(Genre, genre='Testgenre')
        cls.obj1 = make(cls.model, band_name='Bar Foo', genre=genre)
        cls.obj2 = make(cls.model, band_name='Foo Fighters')

        super().setUpTestData()

    def test_setup_sets_model(self):
        """Assert that setup sets the 'model' attribute from the kwargs."""
        view = self.view_class()
        view.model = None
        view.setup(self.get_request(), model_name='ausgabe')
        self.assertEqual(view.model, _models.Ausgabe)

    def test_setup_sets_create_field(self):
        """Assert that setup sets the 'create_field' attribute from the kwargs."""
        request = self.get_request()
        view = self.view_class(model=self.model)
        view.create_field = None
        view.setup(request, create_field="this ain't no field")
        self.assertEqual(view.create_field, "this ain't no field")

    @patch('dbentry.ac.views.ACBase.has_more')
    def test_display_create_option(self, has_more_mock):
        """
        A create option should be displayed when:
            - a create_field is set and
            - q is not None and not an empty string and
            - we're on the last page of the results (if there is pagination)
        """
        view = self.get_view()
        view.create_field = 'any'
        view.prevent_duplicates = False
        q = 'foo'
        context = {'page_obj': object()}
        has_more_mock.return_value = False

        self.assertTrue(view.display_create_option(context, q))

    def test_display_create_option_no_create_field(self):
        """No create option should be shown, if there is no create field set."""
        view = self.get_view()
        view.prevent_duplicates = False

        for create_field in (None, ''):
            with self.subTest(create_field=create_field):
                view.create_field = create_field
                self.assertFalse(view.display_create_option({}, 'foo'))

    def test_display_create_option_no_q(self):
        """No create option should be shown, if q is None or empty."""
        view = self.get_view()
        view.create_field = 'any'
        view.prevent_duplicates = False

        for q in (None, ''):
            with self.subTest(q=q):
                self.assertFalse(view.display_create_option({}, q))

    @patch('dbentry.ac.views.ACBase.has_more')
    def test_display_create_option_no_pagination(self, has_more_mock):
        """A create option should be shown, if there is no pagination."""
        view = self.get_view()
        view.create_field = 'any'
        view.prevent_duplicates = False
        has_more_mock.return_value = False

        # Context is missing 'page_obj':
        self.assertTrue(view.display_create_option({}, 'foo'))

    @patch('dbentry.ac.views.ACBase.has_more')
    def test_display_create_option_more_results(self, has_more_mock):
        """No create option should be shown, if there are more pages of results."""
        view = self.get_view()
        view.create_field = 'any'
        view.prevent_duplicates = False
        context = {'page_obj': object()}
        has_more_mock.return_value = True

        self.assertFalse(view.display_create_option(context, 'foo'))

    def test_display_create_option_exact_match(self):
        """
        No create option should be displayed, if there is an exact match for
        the search term and prevent_duplicates is set to True.
        """
        view = self.get_view(self.get_request(), create_field='band_name')
        view.prevent_duplicates = True
        context = {'page_obj': object(), 'object_list': self.model.objects.all()}

        self.assertFalse(view.display_create_option(context, 'Bar Foo'))

    @translation_override(language=None)
    def test_build_create_option(self):
        """Check the default create option."""
        q = 'foo'
        view = self.get_view(self.get_request())
        option_kwargs = view.build_create_option(q)[0]

        self.assertEqual(option_kwargs['id'], q)
        self.assertEqual(option_kwargs['text'], 'Create "foo"')
        self.assertEqual(option_kwargs['create_id'], True)

    def test_get_create_option(self):
        """
        get_create_option should return the result of build_create_option, if
        all requirements for displaying a create option are satisfied.
        """
        q = 'foo'
        view = self.get_view(self.get_request())

        with patch.object(view, 'display_create_option') as display_option_mock:
            with patch.object(view, 'build_create_option') as build_option_mock:
                display_option_mock.return_value = True
                build_option_mock.return_value = 'This would be the create option!'
                self.assertEqual(
                    view.get_create_option(context={}, q=q),
                    'This would be the create option!'
                )

    def test_get_create_option_no_perms(self):
        """
        No create option should be displayed, if the user does not have 'add'
        permission.
        """
        request = self.get_request(user=self.noperms_user)
        view = self.get_view(request)
        self.assertFalse(view.get_create_option(context={'object_list': []}, q='Beep'))

    @patch('dbentry.ac.views.ACBase.display_create_option')
    def test_get_create_option_strips_q(self, display_mock):
        """
        Assert that get_create_option transforms the search term into a string
        and strips it before passing it on.
        """
        view = self.get_view(self.get_request())
        display_mock.return_value = False
        for q in (None, '    '):
            with self.subTest(q=q):
                view.get_create_option(context={}, q=q)
                display_mock.assert_called_with({}, '')

    def test_get_ordering(self):
        """
        get_ordering should return the view's ordering attribute or the default
        ordering of the view's model.
        """
        view = self.get_view()
        view.ordering = None
        self.assertEqual(view.get_ordering(), view.model._meta.ordering)

        view.ordering = ('hovercrafts', '-eels')
        self.assertEqual(view.get_ordering(), ('hovercrafts', '-eels'))

    def test_get_search_results_calls_search(self):
        """
        Assert that get_search_results calls queryset.search, if the search
        term is not empty and the queryset is a MIZQuerySet.
        """
        queryset = self.model.objects.all()
        view = self.get_view()
        with patch.object(queryset, 'search') as search_mock:
            # The primary key doesn't exist: a normal search should be done.
            view.get_search_results(queryset, 'foo')
            search_mock.assert_called_with('foo')

    def test_get_search_results_queryset_is_not_miz(self):
        """
        Assert that get_search_results calls the parent's get_search_results,
        if the queryset is not a MIZQuerySet.
        """
        queryset = QuerySet(self.model)
        view = self.get_view()
        with patch('dal_select2.views.Select2QuerySetView.get_search_results') as super_mock:
            view.get_search_results(queryset, 'foo')
            super_mock.assert_called()

    def test_get_search_results_no_q(self):
        """If q is an empty string, do not perform any queries."""
        queryset = self.model.objects.all()
        view = self.get_view(self.get_request())
        for q in ('', '   '):
            with self.subTest(q=q):
                with self.assertNumQueries(0):
                    view.get_search_results(queryset, q)

    def test_get_search_results_pk(self):
        """
        Assert that the queryset is filtered against primary keys, if q is a
        numeric string and a record with such a primary key exists.
        """
        queryset = self.model.objects.all()
        view = self.get_view()

        self.assertIn(self.obj1, view.get_search_results(queryset, str(self.obj1.pk)))

        # The primary key doesn't exist: a normal search should be done.
        with patch.object(queryset, 'search') as search_mock:
            view.get_search_results(queryset, '0')
            search_mock.assert_called_with('0')

    def test_apply_forwarded(self):
        """Assert that the queryset is filtered according to the forwarded values."""
        queryset = self.model.objects.all()
        view = self.get_view()
        view.forwarded = {'genre': self.genre.pk}
        self.assertQuerysetEqual(view.apply_forwarded(queryset), [self.obj1])

        musiker = make(Musiker)
        view.forwarded['musiker'] = musiker.pk
        self.assertFalse(view.apply_forwarded(queryset).exists())
        # noinspection PyUnresolvedReferences
        musiker.band_set.add(self.obj1)
        self.assertTrue(view.apply_forwarded(queryset).exists())

    def test_apply_forwarded_no_values(self):
        """
        Assert that if none of the forwards provide (useful) values to filter
        with, an empty queryset is returned.
        """
        queryset = self.model.objects.all()
        view = self.get_view()
        view.forwarded = {'ignore_me_too': ''}
        self.assertFalse(view.apply_forwarded(queryset).exists())
        view.forwarded = {'': 'ignore_me'}
        self.assertFalse(view.apply_forwarded(queryset).exists())

    def test_forwards_applied_before_pk_search(self):
        """
        Filters based on forwarded values must be applied before
        get_search_results attempts a primary key lookup for numeric search
        terms.

        If an instance with a primary key matching the search term exists,
        get_search_results will just return a queryset containing that instance,
        and no full text search with that search term will be performed.
        If that instance then doesn't match the forward filters, and if those
        filters are applied after get_search_results, the result list would be
        empty even though a full text search should have returned results.
        """
        view = self.get_view()
        self.obj1.band_name = str(self.obj2.pk)
        self.obj1.save()
        view.q = str(self.obj2.pk)
        # If forward filters are applied last, then get_search_results will
        # return a queryset containing just obj2 - but obj2 doesn't have the
        # required genre: the result queryset would be empty.
        view.forwarded = {'genre': self.genre.pk}
        self.assertQuerysetEqual(view.get_queryset(), [self.obj1])

    def test_create_object(self):
        """
        create_object should create and return a model instance. A log entry
        should also be created for that new object.
        """
        view = self.get_view(self.get_request(), create_field='band_name')

        with patch('dbentry.ac.views.log_addition') as log_addition_mock:
            new_obj = view.create_object('Fee Fighters')
            self.assertIsInstance(new_obj, self.model)
            self.assertEqual(new_obj.band_name, 'Fee Fighters')
            self.assertTrue(new_obj.pk)
            log_addition_mock.assert_called()

    def test_get_queryset_empty_search_term(self):
        """If the search term is an empty string, do not perform any queries."""
        view = self.get_view()
        for q in ('', '   '):
            with self.subTest(q=q):
                view.q = q
                with self.assertNumQueries(0):
                    view.get_queryset()

    def test_get_queryset_ordering(self):
        """Assert that the result queryset has the 'text search ordering'."""
        # The expected ordering would be:
        #   - name_field__iexact
        #   - name_field__istartswith
        #   - search rank
        #   - name_field
        q = 'foo'
        name_field = self.model.name_field
        exact = ExpressionWrapper(
            Q(**{name_field + '__iexact': q}), output_field=BooleanField()
        )
        startswith = ExpressionWrapper(
            Q(**{name_field + '__istartswith': q}), output_field=BooleanField()
        )

        self.assertEqual(
            self.get_view(q=q).get_queryset().query.order_by,
            (exact.desc(), startswith.desc(), '-rank', name_field)
        )


class TestACTabular(ACViewTestCase):

    class DummyView(ACTabular):

        def get_group_headers(self):
            return ['foo']

        def get_extra_data(self, result):
            return ['bar']

    view_class = DummyView
    model = Band

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model)

        super().setUpTestData()

    def test_get_results_adds_extra_data(self):
        """
        Assert that get_results adds an item with extra data to the results 
        context.
        """
        view = self.get_view()
        result = view.get_results({'object_list': [self.obj]})[0]
        
        self.assertIn(EXTRA_DATA_KEY, result)
        self.assertEqual(['bar'], result[EXTRA_DATA_KEY])

    def test_render_to_response_grouped_data(self):
        """Assert that render_to_response adds the items for the option groups."""
        view = self.get_view(self.get_request(data={'tabular': True}))
        context = {
            'object_list': [self.obj],
            'page_obj': view.paginate_queryset(self.model.objects.all(), 10)[1]
        }
        
        response = view.render_to_response(context)
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)['results']

        # 'results' should be a JSON object with the necessary items to
        # create the optgroup. The first item should be the headers of the
        # optgroup.
        self.assertEqual(len(results), 1)
        self.assertIn('text', results[0])
        self.assertEqual(results[0]['text'], 'Band')
        self.assertIn('is_optgroup', results[0])
        self.assertEqual(results[0]['is_optgroup'], True)
        self.assertIn('optgroup_headers', results[0])
        self.assertEqual(results[0]['optgroup_headers'], ['foo'])
        self.assertIn('children', results[0])
        self.assertEqual(len(results[0]['children']), 1)

        # 'children' contains the actual results.
        result = results[0]['children'][0]
        self.assertIn(EXTRA_DATA_KEY, result)
        self.assertEqual(['bar'], result[EXTRA_DATA_KEY])

    def test_render_to_response_not_first_page(self):
        """Assert that optgroup headers are only included for the first page."""
        make(self.model)  # add another object for the second page
        view = self.get_view(self.get_request(data={'tabular': True, 'page': 2}))
        context = {
            'object_list': [self.obj],
            'page_obj': view.paginate_queryset(self.model.objects.all(), 1)[1]
        }

        response = view.render_to_response(context)
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['optgroup_headers'], [])

    def test_render_to_response_no_results(self):
        """
        Assert that render_to_response does not nest the result data, if there
        are no search results.
        """
        view = self.get_view(self.get_request(data={'tabular': True}))
        context = {
            'object_list': [],  # no results
            'page_obj': None,  # disable paging
        }

        response = view.render_to_response(context)
        self.assertEqual(response.status_code, 200)
        # 'results' should be a just an empty list:
        self.assertFalse(json.loads(response.content)['results'])


class TestACBand(RequestTestCase):
    """Integration tests for ACBand that also cover ACTabular and ACBase."""

    model = _models.Band
    path = reverse_lazy('acband')

    @classmethod
    def setUpTestData(cls):
        cls.genre = genre = make(_models.Genre, genre='Testgenre')
        cls.contains = make(cls.model, band_name='Bar Foo', genre=genre)
        cls.startsw = make(cls.model, band_name='Foo Fighters')
        cls.exact = make(cls.model, band_name='Foo')
        cls.alias = make(cls.model, band_name='Bars', bandalias__alias='Fee Fighters')
        cls.zero = make(cls.model, band_name='0')

        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        response = self.client.get(self.path, data={'q': 'Foo Fighters'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(self.startsw.pk)], get_result_ids(response))

    def test_result_ordering(self):
        """Exact matches should come before startswith before all others."""
        response = self.client.get(self.path, data={'q': 'foo'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [str(self.exact.pk), str(self.startsw.pk), str(self.contains.pk)],
            get_result_ids(response)
        )

    def test_search_term_is_alias(self):
        """An object should be findable via its alias."""
        response = self.client.get(self.path, data={'q': 'Fee Fighters'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.alias.pk), get_result_ids(response))

    def test_search_term_is_numeric(self):
        """For numeric search terms, a lookup for primary keys should be attempted."""
        response = self.client.get(self.path, data={'q': self.exact.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.exact.pk), get_result_ids(response))

        # The primary key doesn't exist: a normal search should be done.
        response = self.client.get(self.path, data={'q': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.zero.pk), get_result_ids(response))

    @translation_override(language=None)
    def test_create_option(self):
        """A create option should be appended to the results."""
        path = reverse('acband', kwargs={'create_field': 'band_name'})
        response = self.client.get(path, data={'q': 'Fighters'})
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)['results']
        self.assertEqual(
            results[-1],
            {'id': 'Fighters', 'text': 'Create "Fighters"', 'create_id': True},
        )

    def test_tabular_results(self):
        """Assert that the results contain extra data for the tabular display."""
        path = reverse('acband', kwargs={'create_field': 'band_name'})
        response = self.client.get(path, data={'q': 'Fee Fighters', 'tabular': True})
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)['results'][0]

        self.assertIn('text', results.keys())
        self.assertEqual(results['text'], 'Band')
        self.assertIn('is_optgroup', results.keys())
        self.assertEqual(results['is_optgroup'], True)
        self.assertIn('optgroup_headers', results.keys())
        self.assertEqual(results['optgroup_headers'], ['Alias'])
        self.assertIn('children', results.keys())
        self.assertEqual(len(results['children']), 2)
        result, _create_option = results['children']
        self.assertEqual(result['id'], str(self.alias.pk))
        self.assertEqual(result['text'], str(self.alias))
        self.assertEqual(result[EXTRA_DATA_KEY], ['Fee Fighters'])
        self.assertEqual(result['selected_text'], str(self.alias))

    def test_filter_with_forwarded_values(self):
        """Assert that the results can be filtered with forwarded values."""
        response = self.get_response(
            # Provide valid JSON for the 'forward' item:
            self.path, data={'text': 'foo', 'forward': f'{{"genre": "{self.genre.pk}"}}'}
        )
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual([str(self.contains.pk)], get_result_ids(response))

    def test_create_object(self):
        """Check the object created with a POST request."""
        path = reverse('acband', kwargs={'create_field': 'band_name'})
        response = self.post_response(path, data={'text': 'Foo Bars'})
        self.assertEqual(response.status_code, 200)
        created = json.loads(response.content)
        self.assertTrue(created['id'])
        self.assertEqual(created['text'], 'Foo Bars')
        self.assertTrue(self.model.objects.filter(band_name='Foo Bars').exists())
        self.assertEqual(self.model.objects.get(band_name='Foo Bars').pk, created['id'])


class TestACAusgabe(ACViewTestCase):

    view_class = ACAusgabe
    model = _models.Ausgabe
    path = reverse_lazy('acausgabe')

    @classmethod
    def setUpTestData(cls):
        cls.mag = mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.obj_num = make(
            cls.model, magazin=mag, ausgabejahr__jahr=2020, ausgabenum__num=10
        )
        cls.obj_lnum = make(
            cls.model, magazin=mag, ausgabejahr__jahr=2020, ausgabelnum__lnum=11
        )
        cls.obj_monat = make(
            cls.model, magazin=mag, ausgabejahr__jahr=2020,
            ausgabemonat__monat__monat='Januar'
        )
        cls.obj_sonder = make(
            cls.model, magazin=mag, sonderausgabe=True,
            beschreibung='Special Edition'
        )
        # noinspection SpellCheckingInspection
        cls.obj_jahrg = make(cls.model, magazin=mag, jahrgang=12, ausgabenum__num=13)
        cls.obj_datum = make(cls.model, magazin=mag, e_datum='1986-08-18')

        # noinspection PyUnresolvedReferences
        cls.test_data = [
            cls.obj_num, cls.obj_lnum, cls.obj_monat, cls.obj_sonder, cls.obj_jahrg
        ]

        super().setUpTestData()

    def test_get_queryset_add_annotations(self):
        """Assert that the ModelAdmin annotations are added to the queryset."""
        class DummyAdmin:

            def __init__(self, *args, **kwargs):
                pass

            # noinspection PyMethodMayBeStatic
            def get_changelist_annotations(self):
                return {'foo': Count('*')}

        with patch('dbentry.admin.AusgabenAdmin', new=DummyAdmin):
            view = self.get_view(self.get_request())
            queryset = view.get_queryset()
            self.assertIn('foo', queryset.query.annotations)

    def test_search_num(self):
        """Assert that an object can be found via its num value(s)."""
        view = self.get_view(q=self.obj_num.__str__())
        self.assertIn(self.obj_num, view.get_queryset())

        # search for 10/11:
        # noinspection PyUnresolvedReferences
        self.obj_num.ausgabenum_set.create(num=11)
        self.obj_num.refresh_from_db()
        view = self.get_view(q=self.obj_num.__str__())
        self.assertIn(self.obj_num, view.get_queryset())

    def test_search_lnum(self):
        """Assert that an object can be found via its lnum value(s)."""
        view = self.get_view(q=self.obj_lnum.__str__())
        self.assertIn(self.obj_lnum, view.get_queryset())

        # search for 11/12:
        # noinspection PyUnresolvedReferences
        self.obj_lnum.ausgabelnum_set.create(lnum=12)
        self.obj_lnum.refresh_from_db()
        view = self.get_view(q=self.obj_lnum.__str__())
        self.assertIn(self.obj_lnum, view.get_queryset())

    def test_search_monat(self):
        """Assert that an object can be found via its monat value(s)."""
        view = self.get_view(q=self.obj_monat.__str__())
        self.assertIn(self.obj_monat, view.get_queryset())

        # search for Jan/Feb:
        # noinspection PyUnresolvedReferences
        self.obj_monat.ausgabemonat_set.create(monat=make(_models.Monat, monat='Februar'))
        self.obj_monat.refresh_from_db()
        view = self.get_view(q=self.obj_monat.__str__())
        self.assertIn(self.obj_monat, view.get_queryset())

    def test_search_sonderausgabe(self):
        """
        Assert that an object can be found via its beschreibung, if it is
        flagged as a 'sonderausgabe'.
        """
        view = self.get_view(q=self.obj_sonder.__str__())
        self.assertIn(self.obj_sonder, view.get_queryset())

    def test_search_jahrgang(self):
        """Assert that an object can be found via its jahrgang value."""
        view = self.get_view(q=self.obj_jahrg.__str__())
        self.assertIn(self.obj_jahrg, view.get_queryset())

    def test_search_datum(self):
        """Assert that an object can be found via its datum value."""
        view = self.get_view(q=self.obj_datum.__str__())
        self.assertIn(self.obj_datum, view.get_queryset())

    def test_get_queryset_chronological_order(self):
        """Assert that the queryset is chronologically ordered."""
        view = self.get_view()
        self.assertTrue(view.get_queryset().chronologically_ordered)

    def test_tabular_results(self):
        """Assert that the results contain extra data for the tabular display."""
        response = self.client.get(self.path, data={'q': str(self.obj_num), 'tabular': True})
        self.assertEqual(response.status_code, 200)
        results = json.loads(response.content)['results'][0]

        self.assertIn('text', results.keys())
        self.assertEqual(results['text'], 'Ausgabe')
        self.assertIn('is_optgroup', results.keys())
        self.assertEqual(results['is_optgroup'], True)
        self.assertIn('optgroup_headers', results.keys())
        self.assertEqual(results['optgroup_headers'], ['Nummer', 'lfd.Nummer', 'Jahr'])
        self.assertIn('children', results.keys())
        self.assertEqual(len(results['children']), 1, results['children'])
        result = results['children'][0]
        self.assertEqual(result['id'], str(self.obj_num.pk))
        self.assertEqual(result['text'], str(self.obj_num))
        self.assertEqual(result[EXTRA_DATA_KEY], ['10', '-', '2020'])
        self.assertEqual(result['selected_text'], str(self.obj_num))


class TestACProv(ACViewTestMethodMixin, ACViewTestCase):
    model = _models.Provenienz
    has_alias = False
    test_data_count = 1


class TestACPerson(ACViewTestCase):
    model = _models.Person
    view_class = ACPerson

    @patch('dbentry.ac.views.log_addition')
    def test_create_object_new_adds_log_entry(self, log_addition_mock):
        """Assert that a log entry is added for the created object."""
        view = self.get_view(self.get_request())
        view.create_object('Alice Testman')
        log_addition_mock.assert_called()

    @translation_override(language=None)
    def test_build_create_option(self):
        """Assert that the create option contains the expected items."""
        request = self.get_request()
        view = self.get_view(request)

        for name in ('Alice Testman', 'Testman, Alice'):
            with self.subTest(name=name):
                create_option = view.build_create_option(q=name)
                self.assertEqual(
                    create_option[0],
                    {'id': name, 'text': f'Create "{name}"', 'create_id': True},
                    msg="The first item should be the 'create' button."
                )
                self.assertEqual(
                    create_option[1],
                    {'id': None, 'text': '...mit folgenden Daten:', 'create_id': True},
                    msg="The second item should be some descriptive text."
                )
                self.assertEqual(
                    create_option[2],
                    {'id': None, 'text': 'Vorname: Alice', 'create_id': True},
                    msg="The third item should be the data for 'vorname'."
                )
                self.assertEqual(
                    create_option[3],
                    {'id': None, 'text': 'Nachname: Testman', 'create_id': True},
                    msg="The fourth item should be the data for 'nachname'."
                )
                self.assertEqual(len(create_option), 4)


class TestACAutor(ACViewTestCase):
    model = _models.Autor
    view_class = ACAutor

    @patch('dbentry.ac.views.log_addition')
    def test_create_object_new_adds_log_entry(self, log_addition_mock):
        """Assert that log entries are added for the created objects."""
        request = self.get_request()
        view = self.get_view(request)
        obj = view.create_object('Alice Testman (AT)')
        self.assertEqual(len(log_addition_mock.call_args_list), 2)
        person_call, autor_call = log_addition_mock.call_args_list
        self.assertEqual(person_call.args, (request.user.pk, obj.person))
        self.assertEqual(autor_call.args, (request.user.pk, obj))

    @translation_override(language=None)
    def test_build_create_option(self):
        """Assert that the create option contains the expected items."""
        request = self.get_request()
        view = self.get_view(request)

        create_option = view.build_create_option(q='Alice Testman (AT)')
        self.assertEqual(
            create_option[0],
            {'id': 'Alice Testman (AT)', 'text': 'Create "Alice Testman (AT)"', 'create_id': True},
            msg="The first item should be the 'create' button."
        )
        self.assertEqual(
            create_option[1],
            {'id': None, 'text': '...mit folgenden Daten:', 'create_id': True},
            msg="The second item should be some descriptive text."
        )
        self.assertEqual(
            create_option[2],
            {'id': None, 'text': 'Vorname: Alice', 'create_id': True},
            msg="The third item should be the data for 'vorname'."
        )
        self.assertEqual(
            create_option[3],
            {'id': None, 'text': 'Nachname: Testman', 'create_id': True},
            msg="The fourth item should be the data for 'nachname'."
        )
        self.assertEqual(
            create_option[4],
            {'id': None, 'text': 'Kürzel: AT', 'create_id': True},
            msg="The fifth item should be the data for 'kuerzel'."
        )
        self.assertEqual(len(create_option), 5)


class TestACMusiker(ACViewTestMethodMixin, ACViewTestCase):
    model = _models.Musiker
    alias_accessor_name = 'musikeralias_set'
    raw_data = [
        {
            'musikeralias__alias': 'John',
            'person__vorname': 'Peter',
            'person__nachname': 'Lustig',
            'beschreibung': 'Description',
            'bemerkungen': 'Stuff'
        }
    ]


class TestACLand(ACViewTestMethodMixin, ACViewTestCase):
    model = _models.Land
    raw_data = [{'land_name': 'Deutschland', 'code': 'DE'}]
    has_alias = False


class TestACInstrument(ACViewTestMethodMixin, ACViewTestCase):
    model = _models.Instrument
    raw_data = [{'instrument': 'Piano', 'kuerzel': 'pi'}]
    has_alias = False


class TestACSpielort(ACViewTestMethodMixin, ACViewTestCase):
    model = _models.Spielort
    alias_accessor_name = 'spielortalias_set'
    raw_data = [{
        'spielortalias__alias': 'AliasSpielort',
        'beschreibung': "If it beeps like a boop, it's probably a test.",
        'bemerkungen': 'Stuff and Things.'
    }]


class TestACVeranstaltung(ACViewTestMethodMixin, ACViewTestCase):
    model = _models.Veranstaltung
    alias_accessor_name = 'veranstaltungalias_set'
    raw_data = [{
        'veranstaltungalias__alias': 'AliasVeranstaltung',
        'beschreibung': "If it beeps like a boop, it's probably a test.",
        'bemerkungen': 'Stuff and Things.'
    }]


class TestACBuchband(ACViewTestCase):
    model = _models.Buch
    view_class = ACBuchband

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, titel='Buchband', is_buchband=True)
        cls.obj2 = make(cls.model, titel='Buch mit Buchband', buchband=cls.obj1)
        cls.obj3 = make(cls.model, titel='Buch ohne Buchband')

        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]

        super().setUpTestData()

    def test_gets_queryset_filters_out_non_buchband(self):
        """
        Assert that get_queryset does not return Buch instances that are not
        flagged as 'buchband'.
        """
        view = self.get_view(q='Buch')
        result = view.get_queryset()
        self.assertEqual(len(result), 1)
        self.assertIn(self.obj1, result)

        self.model.objects.filter(pk=self.obj1.pk).update(is_buchband=False)
        self.assertFalse(view.get_queryset())


class TestACGenre(ACViewTestMethodMixin, ACViewTestCase):

    model = _models.Genre
    alias_accessor_name = 'genrealias_set'
    raw_data = [{'genrealias__alias': 'Beep'}]


class TestACSchlagwort(ACViewTestMethodMixin, ACViewTestCase):

    model = _models.Schlagwort
    alias_accessor_name = 'schlagwortalias_set'
    raw_data = [{'schlagwortalias__alias': 'AliasSchlagwort'}]


class TestGND(ViewTestCase):

    view_class = GND
    path = reverse_lazy('gnd')

    @patch('dbentry.ac.views.searchgnd')
    def test(self, query_mock):
        """Assert that the response contains the expected results."""
        query_mock.return_value = ([('134485904', 'Plant, Robert')], 1)
        response = self.client.get(self.path, data={'q': 'Robert Plant'})
        results = json.loads(response.content)['results']
        self.assertEqual(len(results), 1)
        expected = [{
            'id': '134485904',
            'text': 'Plant, Robert (134485904)',
            'selected_text': 'Plant, Robert (134485904)'
        }]
        self.assertEqual(expected, results)

    def test_get_query_string(self):
        """Assert that get_query_string returns the expected SRU query string."""
        view = self.get_view()
        query = view.get_query_string(q="Robert")
        self.assertEqual(query, "PER=Robert and BBG=Tp*")
        query = view.get_query_string(q="Robert Plant")
        self.assertEqual(query, "PER=Robert and PER=Plant and BBG=Tp*")

    def test_get_query_string_empty(self):
        """
        Assert that get_query_string returns an empty string, if the input
        parameter is an empty string.
        """
        view = self.get_view()
        self.assertFalse(view.get_query_string(q=""))

    @patch('dbentry.ac.views.searchgnd')
    def test_get_queryset(self, mocked_query_func):
        """Assert that get_queryset returns the query results."""
        results = [('id', 'label')]
        mocked_query_func.return_value = (results, 1)
        view = self.get_view(request=self.get_request(), q='q')
        self.assertEqual(view.get_queryset(), results)

    @patch('dbentry.ac.views.searchgnd')
    def test_get_queryset_page_number(self, mocked_query_func):
        """
        Assert that for a given page number, get_queryset calls the query func
        with the correct startRecord index.
        """
        mocked_query_func.return_value = ([('id', 'label')], 1)
        # noinspection PyPep8Naming
        startRecord_msg = "Expected query func to be called with a 'startRecord' kwarg."
        view_initkwargs = {
            'q': 'Beep',
            'page_kwarg': 'page',
            'paginate_by': 10,
        }

        # Should call with 1, if view kwargs or request data do not provide a
        # 'page' (page_kwarg) parameter:
        request = self.get_request()
        view = self.get_view(request=request, **view_initkwargs)
        view.get_queryset()
        _args, kwargs = mocked_query_func.call_args
        self.assertIn('startRecord', kwargs, msg=startRecord_msg)
        self.assertEqual(kwargs['startRecord'], ['1'])

        # Should call with request.GET.page_kwarg:
        request = self.get_request(data={'page': '2'})
        view = self.get_view(request=request, **view_initkwargs)
        view.get_queryset()
        _args, kwargs = mocked_query_func.call_args
        self.assertIn('startRecord', kwargs, msg=startRecord_msg)
        self.assertEqual(kwargs['startRecord'], ['11'])

        # Should call with view.kwargs.page_kwarg:
        request = self.get_request()
        view = self.get_view(request=request, kwargs={'page': 3}, **view_initkwargs)
        view.get_queryset()
        _args, kwargs = mocked_query_func.call_args
        self.assertIn('startRecord', kwargs, msg=startRecord_msg)
        self.assertEqual(kwargs['startRecord'], ['21'])

    @patch('dbentry.ac.views.searchgnd')
    def test_get_queryset_paginate_by(self, mocked_query_func):
        """
        Assert that get_queryset factors in the paginate_by attribute when
        calculating the startRecord value.
        """
        # Set paginate_by to 5; the startRecord index for the third page
        # would then be 11 (first page: 1-5, second page: 6-10).
        mocked_query_func.return_value = ([('id', 'label')], 1)
        request = self.get_request(data={'page': '3'})
        view = self.get_view(request=request, page_kwarg='page', paginate_by=5, q='Beep')
        view.get_queryset()
        args, kwargs = mocked_query_func.call_args
        self.assertIn(
            'startRecord', kwargs,
            msg="Expected query func to be called with a 'startRecord' kwarg."
        )
        self.assertEqual(kwargs['startRecord'], ['11'])

    @patch('dbentry.ac.views.searchgnd')
    def test_get_queryset_maximum_records(self, mocked_query_func):
        """
        Assert that get_queryset passes 'paginate_by' to the query func as
        'maximumRecords' kwarg.
        """
        # (This sets the number of records retrieved per request)
        mocked_query_func.return_value = ([('id', 'label')], 1)
        view = self.get_view(request=self.get_request(), q='Beep', paginate_by=9)
        view.get_queryset()
        _args, kwargs = mocked_query_func.call_args
        self.assertIn(
            'maximumRecords', kwargs,
            msg="Expected query func to be called with a 'maximumRecords' kwarg."
        )
        self.assertEqual(kwargs['maximumRecords'], ['9'])

    def test_get_paginator_adds_total_count(self):
        """
        Assert that get_paginator adds 'total_count' to the
        super().get_paginator kwargs.
        """
        view = self.get_view(total_count=420)
        with patch('dal_select2.views.Select2QuerySetView.get_paginator') as super_mock:
            view.get_paginator()
            super_mock.assert_called_with(total_count=420)

    def test_get_result_label(self):
        """
        Assert that for a given result, the label displayed is of the format:
        'gnd_name (gnd_id)'
        """
        view = self.get_view()
        self.assertEqual(
            'Plant, Robert (134485904)',
            view.get_result_label(('134485904', 'Plant, Robert'))
        )

    @patch('dbentry.ac.views.searchgnd')
    def test_get_query_func_kwargs(self, mocked_query_func):
        """
        Assert that the view's query func is called with the kwargs added by
        get_query_func_kwargs.
        """
        mocked_query_func.return_value = ([], 0)
        view = self.get_view(request=self.get_request(), q='Beep')
        mocked_get_kwargs = Mock(return_value={'version': '-1', 'new_kwarg': 'never seen before'})

        with patch.object(view, 'get_query_func_kwargs', new=mocked_get_kwargs):
            view.get_queryset()
            mocked_query_func.assert_called()
            _args, kwargs = mocked_query_func.call_args
            self.assertIn('version', kwargs)
            self.assertEqual(kwargs['version'], '-1')
            self.assertIn('new_kwarg', kwargs)
            self.assertEqual(kwargs['new_kwarg'], 'never seen before')


class TestGNDPaginator(MIZTestCase):

    def test_count_equals_total_count_kwarg(self):
        """
        Assert that paginator.count returns the 'total_count' that was passed
        to the constructor.
        """
        paginator = GNDPaginator(object_list=[], per_page=1, total_count=69)
        self.assertEqual(paginator.count, 69)

    def test_page_does_not_slice_object_list(self):
        """
        Assert that GNDPaginator.page does not slice the object_list in its
        call to Paginator._get_page.
        """
        # Mock object isn't subscriptable; trying to slice it would raise a TypeError.
        paginator = GNDPaginator(
            object_list=Mock(), per_page=1, total_count=1, allow_empty_first_page=True
        )
        msg = "GNDPaginator.page tried to slice the object list."
        with patch.object(Paginator, '_get_page'):
            with self.assertNotRaises(TypeError, msg=msg):
                paginator.page(number=1)


class TestACMagazin(ACViewTestCase):
    model = _models.Magazin
    view_class = ACMagazin

    def test_get_search_results_validates_and_compacts_search_term(self):
        """
        Assert that the search term has dashes removed (compact standard number),
        if it is a valid ISSN.
        """
        view = self.get_view(self.get_request())
        queryset = self.model.objects.all()
        # Valid ISSN:
        with patch('dbentry.ac.views.ACBase.get_search_results') as super_mock:
            view.get_search_results(queryset, '1234-5679')
            super_mock.assert_called_with(queryset, '12345679')
        # Invalid ISSN, search term should be left as-is:
        with patch('dbentry.ac.views.ACBase.get_search_results') as super_mock:
            view.get_search_results(queryset, '1234-5670')
            super_mock.assert_called_with(queryset, '1234-5670')

    def test_search_term_issn(self):
        """Assert that a Magazin instance can be found using its ISSN."""
        obj = make(_models.Magazin, magazin_name='Testmagazin', issn='12345679')
        for issn in ('12345679', '1234-5679'):
            with self.subTest(ISSN=issn):
                view = self.get_view(request=self.get_request(), q=issn)
                self.assertIn(obj, view.get_queryset())


@skip("There are no autocompletes for Buch instances (yet?).")
class TestACBuch(ACViewTestCase):
    model = _models.Buch
    view_class = ACBase

    def test_get_search_results_validates_and_compacts_search_term(self):
        """
        Assert that the search term is transformed into compact ISBN-13, if it
        is found to be a valid ISBN. ISBN-13 is equivalent to EAN.
        """
        view = self.get_view(self.get_request())
        for isbn in ('1-234-56789-X', '978-1-234-56789-7'):
            with self.subTest(ISBN=isbn):
                with patch('dbentry.ac.views.ACBase.get_search_results') as super_mock:
                    view.get_search_results(self.queryset, isbn)
                    super_mock.assert_called_with(self.queryset, isbn.replace('-', ''))

        # Invalid ISBN - leave search term as-is:
        for isbn in ('1-234-56789-1', '978-1-234-56789-1'):
            with self.subTest(ISBN=isbn):
                with patch('dbentry.ac.views.ACBase.get_search_results') as super_mock:
                    view.get_search_results(self.queryset, isbn)
                    super_mock.assert_called_with(self.queryset, isbn)

    def test_q_isbn(self):
        """Assert that a Buch instance can be found using its ISBN."""
        obj = make(_models.Buch, titel='Testbuch', issn='9781234567897')
        for isbn in ('123456789X', '1-234-56789-X', '9781234567897', '978-1-234-56789-7'):
            with self.subTest(ISBN=isbn):
                view = self.get_view(request=self.get_request(), q=isbn)
                self.assertIn(obj, view.get_queryset())

    def test_q_ean(self):
        """Assert that a Buch instance can be found using its EAN."""
        obj = make(_models.Buch, titel='Testbuch', ean='9781234567897')
        for ean in ('9781234567897', '978-1-234-56789-7'):
            with self.subTest(EAN=ean):
                view = self.get_view(request=self.get_request(), q=ean)
                self.assertIn(obj, view.get_queryset())


class TestContentTypeAutocompleteView(ACViewTestCase):
    model = ContentType
    view_class = ContentTypeAutocompleteView

    def test_get_queryset(self):
        # Test that the queryset only returns models that have in the admin
        # site register.
        # FIXME: flaky test: this test failed because multiple 'artikel' (lower case)
        #  content types were found in view.get_queryset
        class DummySite:
            _registry = {_models.Artikel: 'ModelAdmin_would_go_here'}

        view = self.get_view()
        view.admin_site = DummySite
        self.assertEqual(
            list(view.get_queryset()),
            [ContentType.objects.get_for_model(_models.Artikel)]
        )
