import datetime
import random
from itertools import chain
from unittest.mock import patch, Mock

from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import models

from dbentry import models as _models
from dbentry.query import CNQuerySet, MIZQuerySet, build_date
from tests.case import DataTestCase, MIZTestCase
from tests.model_factory import make
from .models import Band


class TestMIZQuerySet(DataTestCase):
    model = Band

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, band_name='Testband1')
        cls.obj2 = make(
            cls.model, band_name='Testband2', bandalias__alias=['Coffee'],
            genre__genre=['Rock', 'Jazz']
        )
        cls.obj3 = make(
            cls.model, band_name='Testband3', bandalias__alias=['Juice', 'Water'],
            genre__genre=['Rock', 'Jazz']
        )
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.queryset = MIZQuerySet(self.model)
        self.fields = ['band_name', 'genre__genre', 'bandalias__alias']

    def test_values_dict(self):
        values = self.queryset.values_dict(*self.fields)
        expected = [
            (self.obj1.pk, {'band_name': ('Testband1',)}),
            (self.obj2.pk, {
                'band_name': ('Testband2',), 'genre__genre': ('Jazz', 'Rock'),
                'bandalias__alias': ('Coffee',)
            }),
            (self.obj3.pk, {
                'band_name': ('Testband3',), 'genre__genre': ('Jazz', 'Rock'),
                'bandalias__alias': ('Juice', 'Water')
            })
        ]
        self.assertEqual(len(values), 3)
        for obj_pk, expected_values in expected:
            with self.subTest(obj_pk=obj_pk):
                self.assertIn(obj_pk, values)
                value_dict = values[obj_pk]
                for field_name, _values in expected_values.items():
                    with self.subTest(field_name=field_name, values=_values):
                        self.assertIn(field_name, value_dict)
                        self.assertEqual(
                            sorted(value_dict[field_name]), sorted(_values)
                        )

    def test_values_dict_num_queries(self):
        with self.assertNumQueries(1):
            self.queryset.values_dict(*self.fields)

    def test_values_dict_include_empty(self):
        """Assert that values_dict removes empty values if include_empty is False."""
        queryset = self.queryset.filter(pk=self.obj1.pk)
        self.assertEqual(
            queryset.values_dict(*self.fields, include_empty=True)[self.obj1.pk],
            {'band_name': ('Testband1',), 'genre__genre': (None,), 'bandalias__alias': (None,)}
        )
        self.assertEqual(
            queryset.values_dict(*self.fields, include_empty=False)[self.obj1.pk],
            {'band_name': ('Testband1',)}
        )

    @patch.object(MIZQuerySet, 'values')
    def test_values_dict_no_fields_no_pk(self, values_mock):
        """
        Assert that values_dict does not add an argument for the primary key to
        the values() call if called without any explicit fields.
        """
        self.queryset.values_dict()
        values_mock.assert_called_once_with()  # no arguments

    @patch.object(MIZQuerySet, 'values')
    def test_values_dict_pk_not_in_fields(self, values_mock):
        """
        Assert that values_dict adds an argument for the primary key to the
        values() call.
        """
        self.queryset.values_dict('band_name')
        values_mock.assert_called_once_with('band_name', self.model._meta.pk.name)

    @patch.object(MIZQuerySet, 'values')
    def test_values_dict_pk_in_fields(self, values_mock):
        """
        Assert that values_dict does not add multiple arguments for the
        primary key to the values() call if called with an explicit primary key
        argument.
        """
        for pk_name in ('pk', 'id'):
            with self.subTest(pk_name=pk_name):
                self.queryset.values_dict('band_name', pk_name)
                values_mock.assert_called_once_with('band_name', pk_name)
                values_mock.reset_mock()

    def test_values_dict_flatten(self):
        """Assert that single values are flattened."""
        values = self.queryset.filter(pk=self.obj2.pk).values_dict(*self.fields, flatten=True)
        self.assertIn(self.obj2.pk, values)
        self.assertIn('band_name', values[self.obj2.pk])
        self.assertNotIsInstance(values[self.obj2.pk]['band_name'], tuple)

    def test_values_dict_flatten_reverse_relation(self):
        """Assert that single value lists from reverse relations are not flattened."""
        # obj2 has a single value for alias; which must not get flattened.
        values = self.queryset.filter(pk=self.obj2.pk).values_dict(*self.fields, flatten=True)
        self.assertIn(self.obj2.pk, values)
        self.assertIn('bandalias__alias', values[self.obj2.pk])
        self.assertIsInstance(values[self.obj2.pk]['bandalias__alias'], tuple)

    def test_values_dict_flatten_with_invalid_field_no_exception(self):
        """
        Assert that values_dict does not raise FieldDoesNotExist exceptions
        when determining which fields to exclude from flattening.
        """
        with patch.object(MIZQuerySet, 'values'):
            with self.assertNotRaises(FieldDoesNotExist):
                self.queryset.values_dict('thisaintnofield', flatten=True)

        # Assert that the much more informative django FieldError is raised by
        # values() instead.
        with self.assertRaises(FieldError) as cm:
            self.queryset.values_dict('thisaintnofield', flatten=True)
            self.assertIn('Choices are', cm.exception.args[0])

    def test_add_changelist_annotations(self):
        queryset = self.queryset.add_changelist_annotations()
        self.assertIn("annotated", queryset.query.annotations)

    def test_overview(self):
        """Assert that overview calls the model's overview class method."""
        with patch.object(self.model, "overview", new=Mock(return_value="model.overview called"), create=True):
            self.assertEqual(self.queryset.overview(), "model.overview called")


class CNQuerySetModel(models.Model):
    _name = models.CharField(max_length=10, editable=False, default='YYYY-MM')
    _changed_flag = models.BooleanField(editable=False, default=False)

    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()

    name_composing_fields = ['month', 'year']
    objects = CNQuerySet.as_manager()

    @classmethod
    def _get_name(cls, **name_data):
        return f"{name_data['year'][0]}-{name_data['month'][0]:02}"


class TestCNQuerySet(DataTestCase):
    model = CNQuerySetModel

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(CNQuerySetModel, month=10, year=2022)
        cls.obj2 = make(CNQuerySetModel, month=9, year=2021)
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.queryset = CNQuerySet(self.model)
        self.obj1_qs = self.queryset.filter(pk=self.obj1.pk)
        self.obj2_qs = self.queryset.filter(pk=self.obj2.pk)
        # Do pending updates (_changed_flag set by signals, etc.)
        self.queryset._update_names()

    def test_bulk_create_sets_changed_flag(self):
        """Assert that bulk_create sets the changed_flag."""
        # In order to update the created instances' names on their next
        # query/instantiation, bulk_create must include _changed_flag == True
        self.queryset.bulk_create([self.model(month=11, year=2023)])
        self.assertTrue(self.queryset.filter(month=11, year=2023, _changed_flag=True).exists())

    def test_defer_updates_name(self):
        """Assert that _update_names is called when using defer() without a '_name' argument."""
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.queryset.defer('id'))
            update_mock.assert_called()

    def test_defer_not_updates_name(self):
        """Assert that _update_names is not called when using defer() with a '_name' argument."""
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.queryset.defer('_name'))
            update_mock.assert_not_called()

    def test_filter_updates_names(self):
        """
        Assert that _update_names is called when using filter() with an
        argument that starts with '_name'.
        """
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            for arg in ('_name', '_name__icontains'):
                with self.subTest(arg=arg):
                    list(self.queryset.filter(**{arg: 'Test'}))
                    update_mock.assert_called()

    def test_filter_not_updates_names(self):
        """
        Assert that _update_names is not called when using filter() without a
        '_name' argument.
        """
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.obj1_qs.filter(year=2023))
            update_mock.assert_not_called()

    def test_only_updates_name(self):
        """Assert that _update_names is called when using only() with a '_name' argument."""
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.queryset.only('_name'))
            update_mock.assert_called()

    def test_only_not_updates_name(self):
        """Assert that _update_names is not called when using only() without a '_name' argument."""
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.queryset.only('id'))
            update_mock.assert_not_called()

    def test_update_sets_changed_flag(self):
        """
        Assert that update sets _changed_flag to True for updates without
        changed_flag arguments.
        """
        self.obj1_qs.update(year=1921)
        values = self.queryset.values('_changed_flag').get(pk=self.obj1.pk)
        self.assertTrue(values['_changed_flag'])

    def test_update_explicit_changed_flag_argument(self):
        """Assert that update doesn't override an explicit _changed_flag argument."""
        self.obj1_qs.update(year=1921, _changed_flag=False)
        values = self.queryset.values('_changed_flag').get(pk=self.obj1.pk)
        self.assertFalse(values['_changed_flag'])

    def test_values_updates_name(self):
        """Assert that _update_names is called when using values() with a '_name' argument."""
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.queryset.values('_name'))
            update_mock.assert_called()

    def test_values_not_updates_name(self):
        """
        Assert that _update_names is not called when using values() without a
        '_name' argument.
        """
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.queryset.values('id'))
            update_mock.assert_not_called()

    def test_values_list_updates_name(self):
        """Assert that _update_names is called when using values_list() with a '_name' argument."""
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.queryset.values_list('_name'))
            update_mock.assert_called()

    def test_values_list_not_updates_name(self):
        """
        Assert that _update_names is not called when using values_list()
        without a '_name' argument.
        """
        with patch.object(CNQuerySet, '_update_names') as update_mock:
            list(self.queryset.values_list('id'))
            update_mock.assert_not_called()

    def test_update_names(self):
        """Assert that the values for the name field are updated as expected."""
        # Disable the 'automatic' updating of names:
        with patch.object(CNQuerySet, '_update_names'):
            self.obj1_qs.update(_changed_flag=True, month=1, year=1922)
            self.obj2_qs.update(_changed_flag=True, month=2, year=1921)
        # Now do the name updates:
        self.queryset._update_names()
        self.assertEqual(self.queryset.values('_name').get(pk=self.obj1.pk)['_name'], '1922-01')
        self.assertEqual(self.queryset.values('_name').get(pk=self.obj2.pk)['_name'], '1921-02')

    def test_update_names_num_queries(self):
        """Asser that a name update performs the expected number of queries."""
        # Should be six queries:
        # - one from querying the existence of _changed_flag records,
        # - one from calling values_dict,
        # - one each for every object to be updated,
        # - two for the transaction.atomic block
        self.queryset.update(_changed_flag=True)
        with self.assertNumQueries(6):
            self.queryset._update_names()

    def test_update_names_num_queries_empty(self):
        """
        Assert that no updating queries are done if the queryset does not
        contain any rows with the changed flag set.
        """
        self.queryset.update(_changed_flag=False)
        # One query that checks if there are any rows with the changed flag set:
        with self.assertNumQueries(1):
            self.queryset._update_names()

    def test_num_queries(self):
        """
        Assert that a query including the _name field includes the expected
        number of queries.
        """
        # 3 queries for each call of _update_names from only, filter and
        # values_list, plus one query for the actual result list.
        with self.assertNumQueries(4):
            list(self.queryset.only('_name').filter(_name='2022-01').values_list('_name'))


class TestAusgabeChronologicalOrder(DataTestCase):
    jg = None
    monat = None
    lnum = None
    num = None
    mag = None
    e_datum = None
    model = _models.Ausgabe

    @classmethod
    def setUpTestData(cls):

        def get_date(month, year):  # noqa
            return "{year}-{month}-{day}".format(
                year=str(year),
                month=str(month),
                day=random.randrange(1, 28)
            )

        cls.e_datum, cls.num, cls.lnum, cls.monat, cls.jg = (
            [], [], [], [], []
        )
        cls.mag = make(_models.Magazin)

        for jg, year in enumerate(range(1999, 2002), start=1):
            for i in range(1, 4):
                cls.e_datum.append(
                    make(
                        cls.model, magazin=cls.mag,
                        e_datum=get_date(i, year), ausgabejahr__jahr=year
                    )
                )
                cls.num.append(
                    make(
                        cls.model, magazin=cls.mag,
                        ausgabenum__num=i, ausgabejahr__jahr=year
                    )
                )
                cls.lnum.append(
                    make(
                        cls.model, magazin=cls.mag,
                        ausgabelnum__lnum=i, ausgabejahr__jahr=year
                    )
                )
                cls.monat.append(
                    make(
                        cls.model, magazin=cls.mag,
                        ausgabemonat__monat__ordinal=i, ausgabejahr__jahr=year
                    )
                )
                cls.jg.append(
                    make(
                        cls.model, magazin=cls.mag,
                        ausgabenum__num=i, jahrgang=jg
                    )
                )
        cls.all = cls.e_datum + cls.num + cls.lnum + cls.monat + cls.jg
        super().setUpTestData()

    def test_already_ordered(self):
        """
        Assert that chronological_order is not attempted for a queryset that is
        already chronologically ordered.
        """
        queryset = self.model.objects.all()
        queryset.chronologically_ordered = True
        with self.assertNumQueries(0):
            queryset = queryset.chronological_order()
        self.assertFalse(queryset.query.order_by)

    def test_empty_queryset(self):
        """Assert that chronological_order is not attempted for an empty queryset."""
        queryset = self.model.objects.filter(id=0).order_by()
        with self.assertNumQueries(1):
            queryset = queryset.chronological_order()
        self.assertEqual(queryset.query.order_by, tuple(self.model._meta.ordering))

    def test_multiple_magazines(self):
        """
        Assert that chronological_order is not attempted for a queryset with
        multiple magazines.
        """
        make(_models.Ausgabe, magazin__magazin_name='Bad')
        queryset = self.model.objects.all()
        with self.assertNumQueries(1):
            queryset = queryset.chronological_order()
        self.assertEqual(queryset.query.order_by, tuple(self.model._meta.ordering))

    def test_keeps_specified_ordering(self):
        """
        Assert that chronological_order applies ordering specified by either
        the given arguments or the ordering of the initial queryset if no
        chronological ordering will be attempted.
        """
        make(_models.Ausgabe, magazin__magazin_name='Bad')
        queryset = self.model.objects.order_by('sonderausgabe', '-id')
        queryset = queryset.chronological_order()
        self.assertEqual(queryset.query.order_by, ('sonderausgabe', '-id'))
        queryset = self.model.objects.all()
        queryset = queryset.chronological_order('sonderausgabe', '-id')
        self.assertEqual(queryset.query.order_by, ('sonderausgabe', '-id'))

    def test_checks_for_pk_ordering(self):
        """
        Assert that chronological_order removes passed in order fields for the
        primary key, and instead appends one primary key field to the final
        ordering.
        """
        for ordering in [[], ['pk'], ['-pk'], ['id'], ['-id'], ['pk', '-pk']]:
            with self.subTest(ordering=ordering):
                queryset = self.model.objects.chronological_order(*ordering)
                if not ordering:
                    self.assertEqual(
                        queryset.query.order_by[-1], f"-{self.model._meta.pk.name}",
                        msg="If no ordering is specified, the last ordering "
                            "entry should default to '-{pk_name}'."
                    )
                else:
                    self.assertEqual(
                        queryset.query.order_by[-1], ordering[0],
                        msg="Last ordering entry should be a primary key."
                    )

    def test_argument_ordering_has_priority(self):
        """
        Assert that ordering fields passed in to chronological_order have the
        highest priority in the final ordering.
        """
        queryset = self.model.objects.chronological_order('-magazin', 'sonderausgabe', 'jahr')
        self.assertEqual(queryset.query.order_by[:3], ('-magazin', 'sonderausgabe', 'jahr'))

    def test_jahr_over_jahrgang(self):
        """
        Assert that ordering field 'jahr' comes before 'jahrgang' if 'jahr'
        values are more prominent than 'jahrgang' values in the queryset.
        """
        order_by = self.model.objects.chronological_order().query.order_by
        self.assertGreater(
            order_by.index('jahrgang'), order_by.index('jahr'),
            msg="'jahr' ordering expected before 'jahrgang'."
        )

    def test_jahrgang_over_jahr(self):
        """
        Assert that ordering field 'jahrgang' comes before 'jahr' if 'jahrgang'
        values are more prominent than 'jahr' values in the queryset.
        """
        ids = [obj.pk for obj in self.jg]
        order_by = self.model.objects.filter(id__in=ids).chronological_order().query.order_by
        self.assertGreater(
            order_by.index('jahr'), order_by.index('jahrgang'),
            msg="'jahrgang' ordering expected before 'jahr'."
        )

    def test_criteria_equal(self):
        """
        Assert that a default ordering is used when all criteria are equally
        represented.
        """
        # If none of the four criteria dominate, the default order should be:
        # 'e_datum', 'lnum', 'monat', 'num'
        ids = [obj.pk for obj in chain(self.e_datum, self.lnum, self.monat, self.num)]
        queryset = self.model.objects.filter(id__in=ids)
        expected = (
            'magazin__magazin_name', 'jahr', 'jahrgang', 'sonderausgabe',
            'e_datum', 'lnum', 'monat', 'num', '-id'
        )
        self.assertEqual(queryset.chronological_order().query.order_by, expected)

    def test_table_join_duplicates(self):
        """
        Assert that duplicates created through table joins are not counted
        multiple times when determining which criteria to use.
        """
        # Four Ausgabe instances use 'lnum', thus it should be the leading
        # criteria.
        a = make(self.model, magazin=self.mag, ausgabelnum__lnum=1)
        b = make(self.model, magazin=self.mag, ausgabelnum__lnum=2)
        c = make(self.model, magazin=self.mag, ausgabelnum__lnum=3)
        d = make(self.model, magazin=self.mag, ausgabelnum__lnum=4)
        e = make(
            self.model, magazin=self.mag,
            # The joins would lead to both monat and num criteria being present
            # nine times. lnum should still win out, though.
            ausgabemonat__monat__ordinal=[1, 2, 3], ausgabenum__num=[1, 2, 3]
        )
        ordering = (
            self.model.objects
            .filter(pk__in=[a.pk, b.pk, c.pk, d.pk, e.pk])
            .chronological_order()
            .query
            .order_by
        )
        self.assertLess(ordering.index('lnum'), ordering.index('monat'))
        self.assertLess(ordering.index('lnum'), ordering.index('num'))

    def test_search_keeps_order(self):
        """
        Assert that filtering the queryset via search() maintains the ordering
        established by chronological_order.
        """
        queryset = self.model.objects.filter(ausgabejahr__jahr=2000).chronological_order()
        found_ids = [obj.pk for obj in queryset.search('2000')]
        self.assertSequenceEqual(queryset.values_list('pk', flat=True), found_ids)

    def test_update_names_after_chronological_order(self):
        """Assert that updating the names does not remove the chronological ordering."""
        # _updates_names removes all ordering for the update query
        self.model.objects.update(_changed_flag=True)
        queryset = self.model.objects.chronological_order()
        queryset._update_names()
        # Since jahrgang objects have 'num' values the 'num' criterion should
        # come before 'e_datum', 'lnum', etc.:
        expected = (
            'magazin__magazin_name', 'jahr', 'jahrgang', 'sonderausgabe',
            'num', 'e_datum', 'lnum', 'monat', '-id'
        )
        self.assertEqual(queryset.query.order_by, expected)

    def test_keeps_chronologically_ordered_value_after_cloning(self):
        """
        Assert that cloning/chaining the queryset transfers the value of the
        chronologically_ordered attribute.
        """
        queryset = self.model.objects.all()
        self.assertFalse(queryset.chronologically_ordered)
        self.assertFalse(queryset._chain().chronologically_ordered)
        queryset = queryset.chronological_order()
        self.assertTrue(queryset.chronologically_ordered)
        self.assertTrue(queryset._chain().chronologically_ordered)

    def test_order_by_resets_chronological_order(self):
        """
        Assert that using order_by() resets the chronologically_ordered
        attribute to False.
        """
        queryset = self.model.objects.all().chronological_order()
        self.assertTrue(queryset.chronologically_ordered)
        queryset = queryset.order_by('magazin')
        self.assertFalse(queryset.chronologically_ordered)

    def test_update(self):
        """
        Assert that an update query can be performed on a chronologically
        ordered queryset.
        """
        queryset = self.queryset.chronological_order()
        self.assertTrue(queryset.chronological_order)
        with self.assertNotRaises(Exception):
            queryset.update(beschreibung='abc')

    def test_count_ordering_field_only_once_per_row(self):
        """
        Assert that rows with multiple values in any of the order fields are
        only counted once.
        """
        a = make(self.model, magazin=self.mag, e_datum='2023-04-17')
        b = make(
            self.model, magazin=self.mag, e_datum='2023-04-16',
            ausgabelnum__lnum=[1, 2, 3]
        )
        # Top ordering field should be e_datum, because both instances have it.
        # It should not be lnum, although it has the highest 'count' in total
        # (3 lnums vs 2 e_datums).
        queryset = self.model.objects.filter(id__in=[a.pk, b.pk]).chronological_order()
        ordering = queryset.query.order_by
        self.assertGreater(ordering.index('lnum'), ordering.index('e_datum'), msg=ordering)


class TestAusgabeIncrementJahrgang(DataTestCase):
    model = _models.Ausgabe

    @classmethod
    def setUpTestData(cls):
        # obj1: start_jg
        cls.obj1 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[2000],
            e_datum='2000-06-01', ausgabemonat__monat__ordinal=[6],
            ausgabenum__num=[6]
        )
        cls.obj1.refresh_from_db()  # noqa
        # obj2: start_jg - 1
        # Should belong to the previous jahrgang.
        cls.obj2 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[2000],
            e_datum='2000-05-01', ausgabemonat__monat__ordinal=[5],
            ausgabenum__num=[5]
        )
        # obj3: start_jg - 1
        # This object *starts* the jahrgang that obj2 also belongs to.
        cls.obj3 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[1999],
            e_datum='1999-06-01', ausgabemonat__monat__ordinal=[6],
            ausgabenum__num=[6]
        )
        # obj4: start_jg
        # Test the differentiation of jahr/num/monat values when the object
        # spans more than one year.
        cls.obj4 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[2000, 2001],
            e_datum='2000-12-31', ausgabemonat__monat__ordinal=[12, 1],
            ausgabenum__num=[12, 1]
        )
        # obj5: start_jg
        cls.obj5 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[2001],
            e_datum='2001-05-01', ausgabemonat__monat__ordinal=[5],
            ausgabenum__num=[5]
        )
        # obj6: start_jg + 1
        # This object begins the jahrgang following the starting jahrgang.
        cls.obj6 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[2001],
            e_datum='2001-06-01', ausgabemonat__monat__ordinal=[6],
            ausgabenum__num=[6]
        )
        # obj7: start_jg + 2
        cls.obj7 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[2002],
            e_datum='2002-06-01', ausgabemonat__monat__ordinal=[6],
            ausgabenum__num=[6]
        )
        # obj8: ignored
        cls.obj8 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabemonat__monat__ordinal=[6],
            ausgabenum__num=[6]
        )
        # obj9: start_jg - 2
        cls.obj9 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[1998],
            e_datum='1998-06-01', ausgabemonat__monat__ordinal=[6],
            ausgabenum__num=[6]
        )
        # obj10: start_jg - 3
        cls.obj10 = make(
            cls.model, magazin__magazin_name='Testmagazin', ausgabejahr__jahr=[1997],
            e_datum='1997-06-01', ausgabemonat__monat__ordinal=[6],
            ausgabenum__num=[6]
        )

    def assertJahrgangIncremented(self, queryset):
        """Assert that the jahrgang values were adjusted as expected."""
        self.assertEqual(queryset.get(pk=self.obj1.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj2.pk).jahrgang, 9)
        self.assertEqual(queryset.get(pk=self.obj3.pk).jahrgang, 9)
        self.assertEqual(queryset.get(pk=self.obj4.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj5.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj6.pk).jahrgang, 11)
        self.assertEqual(queryset.get(pk=self.obj7.pk).jahrgang, 12)
        self.assertEqual(queryset.get(pk=self.obj8.pk).jahrgang, None)
        self.assertEqual(queryset.get(pk=self.obj9.pk).jahrgang, 8)
        self.assertEqual(queryset.get(pk=self.obj10.pk).jahrgang, 7)

    def test_increment_by_date(self):
        self.obj1.refresh_from_db()  # refresh value for field 'e_datum'
        self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertJahrgangIncremented(self.queryset)

    def test_increment_by_month(self):
        self.queryset.update(e_datum=None)
        self.obj1.refresh_from_db()
        self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertJahrgangIncremented(self.queryset)

    def test_increment_by_num(self):
        self.queryset.update(e_datum=None)
        _models.AusgabeMonat.objects.all().delete()
        self.obj1.refresh_from_db()
        self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertJahrgangIncremented(self.queryset)

    def test_increment_by_year(self):
        self.queryset.update(e_datum=None)
        _models.AusgabeMonat.objects.all().delete()
        _models.AusgabeNum.objects.all().delete()
        self.obj1.refresh_from_db()

        self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertEqual(self.queryset.get(pk=self.obj1.pk).jahrgang, 10)
        self.assertEqual(self.queryset.get(pk=self.obj2.pk).jahrgang, 10)
        self.assertEqual(self.queryset.get(pk=self.obj3.pk).jahrgang, 9)
        self.assertEqual(self.queryset.get(pk=self.obj4.pk).jahrgang, 10)
        self.assertEqual(self.queryset.get(pk=self.obj5.pk).jahrgang, 11)
        self.assertEqual(self.queryset.get(pk=self.obj6.pk).jahrgang, 11)
        self.assertEqual(self.queryset.get(pk=self.obj7.pk).jahrgang, 12)
        self.assertEqual(self.queryset.get(pk=self.obj8.pk).jahrgang, None)
        self.assertEqual(self.queryset.get(pk=self.obj9.pk).jahrgang, 8)
        self.assertEqual(self.queryset.get(pk=self.obj10.pk).jahrgang, 7)

    def test_increment_mixed(self):
        """Test increment_jahrgang with a mixed bag of values."""
        # Remove the e_datum and month values from obj4 to obj7.
        self.obj1.refresh_from_db()  # refresh value for field 'e_datum'
        ids = [self.obj4.pk, self.obj5.pk, self.obj6.pk, self.obj7.pk]
        _models.AusgabeMonat.objects.filter(ausgabe_id__in=ids).delete()
        _models.Ausgabe.objects.filter(pk__in=ids).update(e_datum=None)
        # Also remove num values from obj6 and obj7.
        _models.AusgabeNum.objects.filter(ausgabe_id__in=[self.obj6.pk, self.obj7.pk]).delete()

        self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertJahrgangIncremented(self.queryset)

    def test_increment_no_start_values(self):
        """
        Assert that increment_jahrgang only increments the jahrgang value of
        the start object if no temporal order can be established due to missing
        values (no start date/start year).
        """
        _models.AusgabeJahr.objects.all().delete()
        self.obj1.e_datum = None

        self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertFalse(
            self.queryset.exclude(pk=self.obj1.pk).filter(jahrgang__isnull=False).exists()
        )
        self.assertSequenceEqual(
            self.queryset.filter(pk=self.obj1.pk).values_list('jahrgang', flat=True),
            [10]
        )


class TestBuildDate(MIZTestCase):

    def test_build_date(self):
        self.assertEqual(build_date([2000], [1], 31), datetime.date(2000, 1, 31))
        self.assertEqual(build_date([2000], [1]), datetime.date(2000, 1, 1))

        self.assertEqual(build_date([2001, 2000], [12]), datetime.date(2000, 12, 1))
        # If there's more than one month, build_date should set the day to the
        # last day of the min month.
        self.assertEqual(build_date([None, 2000], [12, 2]), datetime.date(2000, 2, 29))
        # If there's more than one month and more than one year,
        # build_date should set the day to the last day of the max month
        self.assertEqual(build_date([2001, 2000], [12, 1]), datetime.date(2000, 12, 31))

        self.assertIsNone(build_date([None], [None]))
