import json
from unittest import skip
from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.db.models import BooleanField, ExpressionWrapper, Q, QuerySet
from django.urls import reverse_lazy
from django.utils.translation import override as translation_override
from django.test import RequestFactory

import dbentry.models as _models
from dbentry.ac.views import (
    ACAutor, ACBase, ACAusgabe, ACBuchband, ACMagazin, ACPerson, ACTabular,
    ContentTypeAutocompleteView,
    GND, GNDPaginator, Paginator, parse_autor_name
)
from dbentry.ac.widgets import EXTRA_DATA_KEY
from dbentry.factory import make
from dbentry.tests.base import ViewTestCase, MyTestCase
from dbentry.tests.ac.base import ACViewTestMethodMixin, ACViewTestCase


class TestAutorNameParser(MyTestCase):

    def test(self):
        names = [
            ('Alice Testman', ('Alice', 'Testman', '')),
            ('Testman, Alice', ('Alice', 'Testman', '')),
            ('Alice "AT" Testman', ('Alice', 'Testman', 'AT')),
            ('Alice Testman (AT)', ('Alice', 'Testman', 'AT')),
            ('Testman, Alice (AT)', ('Alice', 'Testman', 'AT')),
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


class TestACBase(ACViewTestMethodMixin, ACViewTestCase):

    view_class = ACBase
    model = _models.Band
    create_field = 'band_name'
    alias_accessor_name = 'bandalias_set'
    path = reverse_lazy('acband')

    # noinspection SpellCheckingInspection
    @classmethod
    def setUpTestData(cls):
        cls.genre = make(_models.Genre, genre='Testgenre')
        cls.obj1 = cls.contains = make(
            cls.model, band_name='Bar Foo', genre=cls.genre, bandalias__alias='Fubars'
        )
        cls.obj2 = cls.startsw = make(cls.model, band_name='Foo Fighters')
        cls.exact = make(cls.model, band_name='Foo')
        cls.zero = make(cls.model, band_name='0')

        cls.test_data = [cls.contains, cls.startsw, cls.exact, cls.zero]

        super().setUpTestData()

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
        # TODO: replace with just self.get_request once merged into test-rework
        request = RequestFactory().get('/')
        request.user = self.super_user
        view = self.get_view(request)
        display_mock.return_value = False
        for q in (None, '    '):
            with self.subTest(q=q):
                view.get_create_option(context={}, q=q)
                display_mock.assert_called_with({}, '')

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
        has_more_mock.return_value = False
        q = 'foo'
        context = {'page_obj': object(), 'object_list': []}

        self.assertTrue(view.display_create_option(context, q))

    @patch('dbentry.ac.views.ACBase.has_more')
    def test_display_create_option_no_create_field(self, has_more_mock):
        """No create option should be shown, if there is no create field set."""
        view = self.get_view()
        has_more_mock.return_value = False
        context = {'page_obj': object(), 'object_list': []}

        for create_field in (None, ''):
            with self.subTest(create_field=create_field):
                view.create_field = create_field
                self.assertFalse(view.display_create_option(context, 'foo'))

    @patch('dbentry.ac.views.ACBase.has_more')
    def test_display_create_option_no_q(self, has_more_mock):
        """No create option should be shown, if q is None or empty."""
        view = self.get_view()
        view.create_field = 'any'
        has_more_mock.return_value = False
        context = {'page_obj': object(), 'object_list': []}

        for q in (None, ''):
            with self.subTest(q=q):
                self.assertFalse(view.display_create_option(context, q))

    @patch('dbentry.ac.views.ACBase.has_more')
    def test_display_create_option_no_pagination(self, has_more_mock):
        """A create option should be shown, if there is no pagination."""
        view = self.get_view()
        view.create_field = 'any'
        has_more_mock.return_value = False
        context = {'object_list': []}  # page_obj is missing

        self.assertTrue(view.display_create_option(context, 'foo'))

    @patch('dbentry.ac.views.ACBase.has_more')
    def test_display_create_option_more_results(self, has_more_mock):
        """No create option should be shown, if there are more pages of results."""
        view = self.get_view()
        view.create_field = 'any'
        context = {'page_obj': object(), 'object_list': []}

        has_more_mock.return_value = True
        self.assertFalse(view.display_create_option(context, 'foo'))

    @patch('dbentry.ac.views.ACBase.has_more')
    def test_display_create_option_exact_match(self, has_more_mock):
        """
        No create option should be displayed, if there is an exact match for
        the search term and prevent_duplicates is set to True.
        """
        has_more_mock.return_value = False
        context = {
            'page_obj': object(),
            'object_list': self.model.objects.filter(pk=self.obj1.pk)
        }
        view = self.get_view()
        view.prevent_duplicates = True
        self.assertFalse(view.display_create_option(context, 'Bar Foo'))

    def test_apply_forwarded(self):
        """Assert that the queryset is filtered according to the forwarded values."""
        view = self.get_view()
        view.forwarded = {'genre': self.genre.pk}
        self.assertQuerysetEqual(view.apply_forwarded(self.queryset), [self.obj1])

        other_musiker = make(_models.Musiker)
        view.forwarded['musiker'] = other_musiker.pk
        self.assertFalse(view.apply_forwarded(self.queryset).exists())
        # noinspection PyUnresolvedReferences
        other_musiker.band_set.add(self.obj1)
        self.assertTrue(view.apply_forwarded(self.queryset).exists())

    def test_apply_forwarded_no_values(self):
        """
        Assert that if none of the forwards provide (useful) values to filter
        with, an empty queryset is returned.
        """
        view = self.get_view()
        view.forwarded = {'ignore_me_too': ''}
        self.assertFalse(view.apply_forwarded(self.queryset).exists())
        view.forwarded = {'': 'ignore_me'}
        self.assertFalse(view.apply_forwarded(self.queryset).exists())

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
        name_field = self.model.name_field
        view = self.get_view()
        q = view.q = 'foo'
        ordering = view.get_queryset().query.order_by
        exact = ExpressionWrapper(
            Q(**{name_field + '__iexact': q}), output_field=BooleanField()
        )
        startswith = ExpressionWrapper(
            Q(**{name_field + '__istartswith': q}), output_field=BooleanField()
        )
        self.assertEqual(ordering[0], exact.desc())
        self.assertEqual(ordering[1], startswith.desc())
        self.assertEqual(ordering[2], '-rank')
        self.assertEqual(ordering[3], name_field)
        self.assertEqual(len(ordering), 4)

    def test_setup_sets_model(self):
        """
        Assert that setup sets the 'model' attribute from the kwargs.
        """
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

    ############################################################################
    # Integration (-ish) tests:
    ############################################################################

    @staticmethod
    def get_result_ids(response):
        return [d['id'] for d in json.loads(response.content)['results']]

    def test_results(self):
        """Assert that the expected result is found."""
        response = self.client.get(self.path, data={'q': 'Foo Fighters'})
        self.assertEqual([str(self.startsw.pk)], self.get_result_ids(response))

    def test_result_ordering(self):
        """Exact matches should come before startswith before all others."""
        response = self.client.get(self.path, data={'q': 'foo'})
        self.assertEqual(
            [str(self.exact.pk), str(self.startsw.pk), str(self.contains.pk)],
            self.get_result_ids(response)
        )

    def test_search_term_is_numeric(self):
        """For numeric search terms, a lookup for primary keys should be attempted."""
        response = self.client.get('/admin/ac/band/', data={'q': self.exact.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.exact.pk), self.get_result_ids(response))

        # The primary key doesn't exist: a normal search should be done.
        response = self.client.get('/admin/ac/band/', data={'q': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.zero.pk), self.get_result_ids(response))

    def test_create_option(self):
        """
        A create option should be appended to the results, if there is no
        exact match.
        """
        response = self.client.get('/admin/ac/band/band_name/', data={'q': 'Fighters'})
        results = json.loads(response.content)['results']
        self.assertEqual(
            results[-1],
            {'id': 'Fighters', 'text': 'Erstelle "Fighters"', 'create_id': True},
        )


class TestACAusgabe(ACViewTestCase):

    model = _models.Ausgabe
    path = 'acausgabe'
    view_class = ACAusgabe

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.obj_num = make(
            cls.model, magazin=cls.mag, ausgabejahr__jahr=2020, ausgabenum__num=10)
        cls.obj_lnum = make(
            cls.model, magazin=cls.mag, ausgabejahr__jahr=2020, ausgabelnum__lnum=10)
        cls.obj_monat = make(
            cls.model, magazin=cls.mag, ausgabejahr__jahr=2020,
            ausgabemonat__monat__monat='Januar'
        )
        cls.obj_sonder = make(
            cls.model, magazin=cls.mag, sonderausgabe=True,
            beschreibung='Special Edition'
        )
        # noinspection SpellCheckingInspection
        cls.obj_jahrg = make(cls.model, magazin=cls.mag, jahrgang=12, ausgabenum__num=13)
        cls.obj_datum = make(cls.model, magazin=cls.mag, e_datum='1986-08-18')

        cls.test_data = [
            cls.obj_num, cls.obj_lnum, cls.obj_monat, cls.obj_sonder, cls.obj_jahrg]

        super().setUpTestData()

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

        # search for 10/11:
        # noinspection PyUnresolvedReferences
        self.obj_lnum.ausgabelnum_set.create(lnum=11)
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


class TestGNDPaginator(MyTestCase):

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


class TestACTabular(ACViewTestCase):

    class DummyView(ACTabular):

        def get_group_headers(self):
            return ['foo']

        def get_extra_data(self, result):
            return ['bar']

    view_class = DummyView
    model = _models.Band

    def test_get_results_adds_extra_data(self):
        """Assert that get_results adds an item with extra data."""
        view = self.get_view()
        context = {'object_list': [Mock(pk=42)]}
        results = view.get_results(context)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIn(EXTRA_DATA_KEY, result)
        self.assertEqual(['bar'], result[EXTRA_DATA_KEY])

    def test_render_to_response_grouped_data(self):
        """Assert that render_to_response adds the items for the option groups."""
        view = self.get_view(request=self.get_request(data={'tabular': True}))
        view.model = _models.Band
        context = {
            'object_list': [Mock(pk=42)],
            'page_obj': Mock(has_previous=Mock(return_value=False)),
        }
        with patch('dbentry.ac.views.http.JsonResponse') as mocked_json_response:
            view.render_to_response(context)
            args, _kwargs = mocked_json_response.call_args
            response_data = args[0]
            self.assertIn('results', response_data)
            results = response_data['results']
            # 'results' should be a JSON object with the necessary items to
            # create the optgroup:
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[0], dict)
            self.assertIn('text', results[0])
            self.assertEqual(results[0]['text'], 'Band')
            self.assertIn('is_optgroup', results[0])
            self.assertEqual(results[0]['is_optgroup'], True)
            self.assertIn('optgroup_headers', results[0])
            self.assertEqual(results[0]['optgroup_headers'], ['foo'])
            self.assertIn('children', results[0])
            self.assertEqual(len(results[0]['children']), 1)
            result = results[0]['children'][0]
            self.assertIn(EXTRA_DATA_KEY, result)
            self.assertEqual(['bar'], result[EXTRA_DATA_KEY])

    def test_render_to_response_not_first_page(self):
        """Assert that optgroup headers are only included for the first page."""
        view = self.get_view(request=self.get_request(data={'tabular': True}))
        view.model = _models.Band
        context = {
            'object_list': [Mock(pk=42)],
            'page_obj': Mock(has_previous=Mock(return_value=True)),
        }
        with patch('dbentry.ac.views.http.JsonResponse') as mocked_json_response:
            view.render_to_response(context)
            args, _kwargs = mocked_json_response.call_args
            response_data = args[0]
            self.assertIn('results', response_data)
            results = response_data['results']
            self.assertIsInstance(results, list)
            self.assertEqual(len(results), 1)
            self.assertIsInstance(results[0], dict)
            self.assertEqual(results[0]['optgroup_headers'], [])

    def test_render_to_response_no_results(self):
        """
        Assert that render_to_response does not nest the result data, if there
        are no search results.
        """
        view = self.get_view(request=self.get_request())
        view.model = _models.Band
        context = {
            'object_list': [],
            'page_obj': None,  # disable paging
        }
        with patch('dbentry.ac.views.http.JsonResponse') as mocked_json_response:
            view.render_to_response(context)
            args, _kwargs = mocked_json_response.call_args
            response_data = args[0]
            self.assertIn('results', response_data)
            results = response_data['results']
            # 'results' should be a just an empty list:
            self.assertEqual(results, [])


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
        # FIXME: this test failed because multiple 'artikel' (lower case)
        #  content types were found in view.get_queryset
        class DummySite:
            _registry = {_models.Artikel: 'ModelAdmin_would_go_here'}

        view = self.get_view()
        view.admin_site = DummySite
        self.assertEqual(
            list(view.get_queryset()),
            [ContentType.objects.get_for_model(_models.Artikel)]
        )
