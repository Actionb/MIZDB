import json
from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.db.models import BooleanField, ExpressionWrapper, Q, QuerySet
from django.urls import reverse, reverse_lazy
from django.utils.translation import override as translation_override

import dbentry.models as _models
from dbentry.ac import views
from dbentry.ac.widgets import EXTRA_DATA_KEY, GENERIC_URL_NAME
from tests.case import MIZTestCase, RequestTestCase, ViewTestCase
from tests.model_factory import make
from tests.test_ac.models import Band, Genre, Musiker


def get_result_ids(response):
    """Return the ids of the results of an autocomplete request."""
    return [d['id'] for d in response.json()['results'] if not d.get('create_id', False)]


class ACViewTestCase(ViewTestCase):
    model = None

    def get_view(
            self, request=None, args=None, kwargs=None, model=None,
            create_field=None, forwarded=None, q='', **initkwargs
    ):
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
                self.assertEqual(views.parse_autor_name(name), expected)

    def test_kuerzel_max_length(self):
        """
        Assert that the kuerzel is shortened, so that its length doesn't exceed
        the model field max_length of 8.
        """
        *y, kuerzel = views.parse_autor_name('Alice (Supercalifragilisticexpialidocious) Tester')
        self.assertEqual(kuerzel, 'Supercal')


class TestACBase(ACViewTestCase):
    """Unit tests for ACBase."""

    model = Band
    view_class = views.ACBase

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

    def test_apply_forwarded(self):
        """Assert that the queryset is filtered according to the forwarded values."""
        queryset = self.model.objects.all()
        view = self.get_view()
        view.forwarded = {'genre': self.genre.pk}
        self.assertQuerysetEqual(view.apply_forwarded(queryset), [self.obj1])

        musiker = make(Musiker)
        view.forwarded['musiker'] = musiker.pk
        self.assertFalse(view.apply_forwarded(queryset).exists())
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
    class DummyView(views.ACTabular):

        def get_group_headers(self):
            return ['foo']

        def get_extra_data(self, result):
            return ['bar']

    model = Band
    view_class = DummyView

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
        results = json.loads(response.content.decode(response.charset))['results']

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
        results = json.loads(response.content.decode(response.charset))['results']
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
        self.assertFalse(json.loads(response.content.decode(response.charset))['results'])


class TestACBand(ACViewTestCase):
    """Integration tests for ACBand that also cover ACTabular and ACBase."""

    model = _models.Band
    path = reverse_lazy('acband')
    create_path = reverse_lazy('acband', kwargs={'create_field': 'band_name'})
    view_class = views.ACBand

    @classmethod
    def setUpTestData(cls):
        cls.genre = genre = make(_models.Genre, genre='Testgenre')
        cls.contains = make(cls.model, band_name='Bar Foo', genre=genre)
        cls.startsw = make(cls.model, band_name='Foo Fighters', bandalias__alias='The Holy Shits')
        cls.exact = make(cls.model, band_name='Foo')
        cls.alias = make(cls.model, band_name='Bars', bandalias__alias='Fee Fighters')

        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        for search_term in (self.startsw.pk, 'Foo Fighters', 'The Holy Shits'):
            with self.subTest(search_term=search_term):
                response = self.client.get(self.path, data={'q': search_term})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([str(self.startsw.pk)], get_result_ids(response))

    def test_create_object(self):
        """Assert that a new object can be created using a POST request."""
        response = self.post_response(self.create_path, data={'text': 'Foo Bars'})
        self.assertEqual(response.status_code, 200)
        created = response.json()
        self.assertTrue(created['id'])
        self.assertEqual(created['text'], 'Foo Bars')
        self.assertTrue(self.model.objects.filter(band_name='Foo Bars').exists())
        self.assertTrue(self.model.objects.get(pk=created['id']))

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

    def test_search_term_matches_pk(self):
        """Primary key matches should be the first results."""
        other = make(self.model, band_name=str(self.exact.pk))
        response = self.client.get(self.path, data={'q': self.exact.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(self.exact.pk), str(other.pk)], get_result_ids(response))

    @translation_override(language=None)
    def test_create_option(self):
        """A create option should be appended to the results."""
        path = reverse('acband', kwargs={'create_field': 'band_name'})
        response = self.client.get(path, data={'q': 'Fighters'})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(
            results[-1],
            {'id': 'Fighters', 'text': 'Create "Fighters"', 'create_id': True},
        )

    def test_tabular_results(self):
        """Assert that the results contain extra data for the tabular display."""
        path = reverse('acband', kwargs={'create_field': 'band_name'})
        response = self.client.get(path, data={'q': 'Fee Fighters', 'tabular': True})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results'][0]

        self.assertIn('text', results.keys())
        self.assertEqual(results['text'], 'Band')
        self.assertIn('is_optgroup', results.keys())
        self.assertEqual(results['is_optgroup'], True)
        self.assertIn('optgroup_headers', results.keys())
        self.assertEqual(results['optgroup_headers'], ['Alias', 'Orte'])
        self.assertIn('children', results.keys())
        self.assertEqual(len(results['children']), 2)
        result, _create_option = results['children']
        self.assertEqual(result['id'], str(self.alias.pk))
        self.assertEqual(result['text'], str(self.alias))
        self.assertEqual(result[EXTRA_DATA_KEY], ['Fee Fighters', '-'])
        self.assertEqual(result['selected_text'], str(self.alias))

    def test_filter_with_forwarded_values(self):
        """Assert that the results can be filtered with forwarded values."""
        response = self.get_response(
            # Provide valid JSON for the 'forward' item:
            self.path, data={'text': 'foo', 'forward': f'{{"genre": "{self.genre.pk}"}}'}
        )
        self.assertEqual(response.status_code, 200, msg=response.content)
        self.assertEqual([str(self.contains.pk)], get_result_ids(response))

    def test_get_queryset_adds_overview_annotations(self):
        """Assert that get_queryset adds the annotations declared in overview_annotations."""
        view = self.get_view(self.get_request())
        queryset = view.get_queryset()
        self.assertCountEqual(['alias_list', 'orte_list'], list(queryset.query.annotations))


class TestACAusgabe(ACViewTestCase):
    model = _models.Ausgabe
    path = reverse_lazy('acausgabe')
    view_class = views.ACAusgabe

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
        cls.obj_jahrg = make(cls.model, magazin=mag, jahrgang=12, ausgabenum__num=13)
        cls.obj_datum = make(cls.model, magazin=mag, e_datum='1986-08-18')

        cls.test_data = [
            cls.obj_num, cls.obj_lnum, cls.obj_monat, cls.obj_sonder, cls.obj_jahrg  # noqa
        ]

        super().setUpTestData()

    def test_search_num(self):
        """Assert that an object can be found via its num value(s)."""
        view = self.get_view(q=self.obj_num.__str__())
        self.assertIn(self.obj_num, view.get_queryset())

        # search for 10/11:
        self.obj_num.ausgabenum_set.create(num=11)
        self.obj_num.refresh_from_db()
        view = self.get_view(q=self.obj_num.__str__())
        self.assertIn(self.obj_num, view.get_queryset())

    def test_search_lnum(self):
        """Assert that an object can be found via its lnum value(s)."""
        view = self.get_view(q=self.obj_lnum.__str__())
        self.assertIn(self.obj_lnum, view.get_queryset())

        # search for 11/12:
        self.obj_lnum.ausgabelnum_set.create(lnum=12)
        self.obj_lnum.refresh_from_db()
        view = self.get_view(q=self.obj_lnum.__str__())
        self.assertIn(self.obj_lnum, view.get_queryset())

    def test_search_monat(self):
        """Assert that an object can be found via its monat value(s)."""
        view = self.get_view(q=self.obj_monat.__str__())
        self.assertIn(self.obj_monat, view.get_queryset())

        # search for Jan/Feb:
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
        results = response.json()['results'][0]

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

    def test_get_queryset_adds_overview_annotations(self):
        """Assert that get_queryset adds the annotations declared in overview_annotations."""
        view = self.get_view(self.get_request())
        queryset = view.get_queryset()
        for expected in ('num_list', 'lnum_list', 'jahr_list'):
            with self.subTest(annotation=expected):
                self.assertIn(expected, queryset.query.annotations)


class TestACAutor(ACViewTestCase):
    model = _models.Autor
    path = reverse_lazy('acautor')
    view_class = views.ACAutor

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        obj = make(
            self.model, kuerzel='AT',
            person__vorname='Alice', person__nachname='Testman'
        )
        for search_term in (obj.pk, 'AT', 'Alice', 'Testman', 'Alice Testman (AT)'):
            with self.subTest(search_term=search_term):
                response = self.client.get(self.path, data={'q': search_term})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([str(obj.pk)], get_result_ids(response))

    def test_create_object(self):
        """Assert that a new object can be created using a POST request."""
        response = self.post_response(self.path, data={'text': 'Bob Tester (BT)'})
        self.assertEqual(response.status_code, 200)
        created = response.json()
        self.assertTrue(created['id'])
        self.assertEqual(created['text'], 'Bob Tester (BT)')
        self.assertTrue(
            self.model.objects.filter(
                person__vorname='Bob', person__nachname='Tester', kuerzel='BT'
            ).exists()
        )
        self.assertTrue(self.model.objects.get(pk=created['id']))

    @patch('dbentry.ac.views.log_addition')
    def test_create_object_adds_log_entry(self, log_addition_mock):
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

    def test_create_object_only_kuerzel(self):
        """
        Assert that no Person instance is created if only the kuerzel is given.
        """
        response = self.post_response(self.path, data={'text': '(BT)'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(_models.Person.objects.exists())


class TestACBuchband(ACViewTestCase):
    model = _models.Buch
    path = reverse_lazy('acbuchband')
    view_class = views.ACBuchband

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, titel='Buchband', is_buchband=True)
        cls.obj2 = make(cls.model, titel='Buch mit Buchband', buchband=cls.obj1)  # noqa
        cls.obj3 = make(cls.model, titel='Buch ohne Buchband')

        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]  # noqa

        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        for search_term in (self.obj1.pk, 'Buch'):
            with self.subTest(search_term=search_term):
                response = self.client.get(self.path, data={'q': search_term})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([str(self.obj1.pk)], get_result_ids(response))

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


class TestACMagazin(ACViewTestCase):
    model = _models.Magazin
    path = reverse_lazy('acmagazin')
    create_path = reverse_lazy('acmagazin', kwargs={'create_field': 'magazin_name'})
    view_class = views.ACMagazin

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, magazin_name='Testmagazin', issn='12345679')

        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        for search_term in (self.obj.pk, 'Testmag', '12345679', '1234-5679'):
            with self.subTest(search_term=search_term):
                response = self.get_response(self.path, data={'q': search_term})
                self.assertIn(str(self.obj.pk), get_result_ids(response))

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

    def test_create_object(self):
        """Assert that a new object can be created using a POST request."""
        response = self.post_response(self.create_path, data={'text': 'Good Times'})
        self.assertEqual(response.status_code, 200)
        created = response.json()
        self.assertTrue(created['id'])
        self.assertEqual(created['text'], 'Good Times')
        self.assertTrue(self.model.objects.filter(magazin_name='Good Times').exists())
        self.assertTrue(self.model.objects.get(pk=created['id']))


class TestACMusiker(ACViewTestCase):
    model = _models.Musiker
    path = reverse_lazy('acmusiker')
    create_path = reverse_lazy('acmusiker', kwargs={'create_field': 'kuenstler_name'})
    test_data = {
        'kuenstler_name': 'Prince',
        'musikeralias__alias': 'TAFKAP',
        'person__vorname': 'Rogers',
        'person__nachname': 'Nelson',
        'beschreibung': 'American singer-songwriter',
        'bemerkungen': 'Alan: revisit this'
    }
    view_class = views.ACMusiker

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, **cls.test_data)
        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        for search_term in (self.obj.pk, *self.test_data.values()):
            with self.subTest(search_term=search_term):
                response = self.get_response(self.path, data={'q': search_term})
                self.assertIn(str(self.obj.pk), get_result_ids(response))

    def test_tabular_results(self):
        """Assert that the results contain extra data for the tabular display."""
        response = self.get_response(self.path, data={'q': 'Prince', 'tabular': True})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results'][0]

        self.assertIn('text', results.keys())
        self.assertEqual(results['text'], 'Musiker')
        self.assertIn('is_optgroup', results.keys())
        self.assertEqual(results['is_optgroup'], True)
        self.assertIn('optgroup_headers', results.keys())
        self.assertEqual(results['optgroup_headers'], ['Alias', 'Orte'])
        self.assertIn('children', results.keys())
        self.assertEqual(len(results['children']), 1, results['children'])
        result = results['children'][0]
        self.assertEqual(result['id'], str(self.obj.pk))
        self.assertEqual(result['text'], str(self.obj))
        self.assertEqual(result[EXTRA_DATA_KEY], ['TAFKAP', '-'])
        self.assertEqual(result['selected_text'], str(self.obj))

    def test_create_object(self):
        """Assert that a new object can be created using a POST request."""
        response = self.post_response(self.create_path, data={'text': 'Princess'})
        self.assertEqual(response.status_code, 200)
        created = response.json()
        self.assertTrue(created['id'])
        self.assertEqual(created['text'], 'Princess')
        self.assertTrue(self.model.objects.filter(kuenstler_name='Princess').exists())
        self.assertTrue(self.model.objects.get(pk=created['id']))

    def test_get_queryset_adds_overview_annotations(self):
        """Assert that get_queryset adds the annotations declared in overview_annotations."""
        view = self.get_view(self.get_request())
        queryset = view.get_queryset()
        self.assertCountEqual(['alias_list', 'orte_list'], list(queryset.query.annotations))


class TestACPerson(ACViewTestCase):
    model = _models.Person
    path = reverse_lazy('acperson')
    view_class = views.ACPerson

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        obj = make(self.model, vorname='Alice', nachname='Testman')
        response = self.client.get(self.path, data={'q': 'Alice Testman'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(obj.pk)], get_result_ids(response))

    @patch('dbentry.ac.views.log_addition')
    def test_create_object_adds_log_entry(self, log_addition_mock):
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


class TestACSpielort(ACViewTestCase):
    model = _models.Spielort
    path = reverse_lazy('acspielort')
    view_class = views.ACSpielort

    @classmethod
    def setUpTestData(cls):
        ort = make(_models.Ort, stadt='Dortmund', land__code='DE')
        cls.obj = make(
            cls.model, name='Freizeitzentrum West', spielortalias__alias='FZW', ort=ort,
            beschreibung='Ort für Konzerte', bemerkungen='Braucht mehr Info!',
        )
        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        search_terms = [self.obj.pk, 'Freizeitzentrum West', 'FZW', 'Dortmund', 'Konzerte', 'Info']
        for search_term in search_terms:
            with self.subTest(search_term=search_term):
                response = self.get_response(self.path, data={'q': search_term})
                self.assertIn(str(self.obj.pk), get_result_ids(response))

    def test_tabular_results(self):
        """Assert that the results contain extra data for the tabular display."""
        response = self.get_response(self.path, data={'q': 'FZW', 'tabular': True})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results'][0]

        self.assertIn('text', results.keys())
        self.assertEqual(results['text'], 'Spielort')
        self.assertIn('is_optgroup', results.keys())
        self.assertEqual(results['is_optgroup'], True)
        self.assertIn('optgroup_headers', results.keys())
        self.assertEqual(results['optgroup_headers'], ['Ort'])
        self.assertIn('children', results.keys())
        self.assertEqual(len(results['children']), 1, results['children'])
        result = results['children'][0]
        self.assertEqual(result['id'], str(self.obj.pk))
        self.assertEqual(result['text'], str(self.obj))
        self.assertEqual(result[EXTRA_DATA_KEY], ['Dortmund, DE'])
        self.assertEqual(result['selected_text'], str(self.obj))


class TestACVeranstaltung(RequestTestCase):
    model = _models.Veranstaltung
    path = reverse_lazy('acveranstaltung')

    @classmethod
    def setUpTestData(cls):
        ort = make(_models.Ort, stadt='Bethel', land__code='US')
        spielort = make(_models.Spielort, name="Max Yasgur's Dairy Farm", ort=ort)
        cls.obj = make(
            cls.model, name='Woodstock', datum='1969', spielort=spielort,
            veranstaltungalias__alias='Woodstock Rock Festival',
            beschreibung='Summer of Love!', bemerkungen='Braucht mehr Info!',
        )
        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        search_terms = [
            self.obj.pk, 'Woodstock', '1969', 'Rock Festival', 'Yasgur', 'Bethel', 'Love', 'Info'
        ]
        for search_term in search_terms:
            with self.subTest(search_term=search_term):
                response = self.get_response(self.path, data={'q': search_term})
                self.assertIn(str(self.obj.pk), get_result_ids(response))

    def test_tabular_results(self):
        """Assert that the results contain extra data for the tabular display."""
        response = self.get_response(self.path, data={'q': 'Woodstock', 'tabular': True})
        self.assertEqual(response.status_code, 200)
        results = response.json()['results'][0]

        self.assertIn('text', results.keys())
        self.assertEqual(results['text'], 'Veranstaltung')
        self.assertIn('is_optgroup', results.keys())
        self.assertEqual(results['is_optgroup'], True)
        self.assertIn('optgroup_headers', results.keys())
        self.assertEqual(results['optgroup_headers'], ['Datum', 'Spielort'])
        self.assertIn('children', results.keys())
        self.assertEqual(len(results['children']), 1, results['children'])
        result = results['children'][0]
        self.assertEqual(result['id'], str(self.obj.pk))
        self.assertEqual(result['text'], str(self.obj))
        self.assertEqual(result[EXTRA_DATA_KEY], ['1969', "Max Yasgur's Dairy Farm"])
        self.assertEqual(result['selected_text'], str(self.obj))


class TestGND(ViewTestCase):
    path = reverse_lazy('gnd')
    view_class = views.GND

    @patch('dbentry.ac.views.searchgnd')
    def test(self, query_mock):
        """Assert that the response contains the expected results."""
        query_mock.return_value = ([('134485904', 'Plant, Robert')], 1)
        response = self.client.get(self.path, data={'q': 'Robert Plant'})
        results = response.json()['results']
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
        paginator = views.GNDPaginator(object_list=[], per_page=1, total_count=69)
        self.assertEqual(paginator.count, 69)

    def test_page_does_not_slice_object_list(self):
        """
        Assert that GNDPaginator.page does not slice the object_list in its
        call to Paginator._get_page.
        """
        # Mock object isn't subscriptable; trying to slice it would raise a TypeError.
        paginator = views.GNDPaginator(
            object_list=Mock(), per_page=1, total_count=1, allow_empty_first_page=True
        )
        msg = "GNDPaginator.page tried to slice the object list."
        with patch.object(views.Paginator, '_get_page'):
            with self.assertNotRaises(TypeError, msg=msg):
                paginator.page(number=1)


class TestContentTypeAutocompleteView(ACViewTestCase):
    model = ContentType
    view_class = views.ContentTypeAutocompleteView

    def test_get_queryset(self):
        """
        Assert that the queryset only returns ContentTypes for models that have
        been registered with the given admin site.
        """

        class DummySite:
            _registry = {Band: 'ModelAdmin_would_go_here'}

        view = self.get_view()
        view.admin_site = DummySite
        opts = Band._meta
        self.assertQuerysetEqual(
            view.get_queryset(),
            ContentType.objects.filter(app_label=opts.app_label, model=opts.model_name)
        )


####################################################################################################
# Tests for various autocompletes that use the generic URL.
####################################################################################################

class TestACGenre(RequestTestCase):
    model = _models.Genre
    path = reverse_lazy(GENERIC_URL_NAME, kwargs={'model_name': 'genre'})
    create_path = reverse_lazy(
        GENERIC_URL_NAME,
        kwargs={'model_name': 'genre', 'create_field': 'genre'}
    )

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, genre='Electronic Dance Music', genrealias__alias='EDM')
        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        for search_term in (self.obj.pk, 'Electronic Dance Music', 'EDM'):
            with self.subTest(search_term=search_term):
                response = self.get_response(self.path, data={'q': search_term})
                self.assertIn(str(self.obj.pk), get_result_ids(response))

    def test_create_object(self):
        """Assert that a new object can be created using a POST request."""
        response = self.post_response(self.create_path, data={'text': 'Rock'})
        self.assertEqual(response.status_code, 200)
        created = response.json()
        self.assertTrue(created['id'])
        self.assertEqual(created['text'], 'Rock')
        self.assertTrue(self.model.objects.filter(genre='Rock').exists())
        self.assertTrue(self.model.objects.get(pk=created['id']))


class TestACSchlagwort(RequestTestCase):
    model = _models.Schlagwort
    path = reverse_lazy(GENERIC_URL_NAME, kwargs={'model_name': 'schlagwort'})
    create_path = reverse_lazy(
        GENERIC_URL_NAME, kwargs={'model_name': 'schlagwort', 'create_field': 'schlagwort'}
    )

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, schlagwort='Hippies', schlagwortalias__alias='Summer of Love')
        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        for search_term in (self.obj.pk, 'Hippies', 'Summer of Love'):
            with self.subTest(search_term=search_term):
                response = self.get_response(self.path, data={'q': search_term})
                self.assertIn(str(self.obj.pk), get_result_ids(response))

    def test_create_object(self):
        """Assert that a new object can be created using a POST request."""
        response = self.post_response(self.create_path, data={'text': 'History'})
        self.assertEqual(response.status_code, 200)
        created = response.json()
        self.assertTrue(created['id'])
        self.assertEqual(created['text'], 'History')
        self.assertTrue(self.model.objects.filter(schlagwort='History').exists())
        self.assertTrue(self.model.objects.get(pk=created['id']))


class TestACInstrument(RequestTestCase):
    model = _models.Instrument
    path = reverse_lazy(GENERIC_URL_NAME, kwargs={'model_name': 'instrument'})

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, instrument='Piano', kuerzel='xy')
        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        for search_term in (self.obj.pk, 'Piano', 'xy'):
            with self.subTest(search_term=search_term):
                response = self.get_response(self.path, data={'q': search_term})
                self.assertIn(str(self.obj.pk), get_result_ids(response))


class TestACLand(RequestTestCase):
    model = _models.Land
    path = reverse_lazy(GENERIC_URL_NAME, kwargs={'model_name': 'land'})

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, land_name='Deutschland', code='XY')
        super().setUpTestData()

    def test(self):
        """Assert that an autocomplete request returns the expected results."""
        for search_term in (self.obj.pk, 'Deutschland', 'XY'):
            with self.subTest(search_term=search_term):
                response = self.get_response(self.path, data={'q': search_term})
                self.assertIn(str(self.obj.pk), get_result_ids(response))
