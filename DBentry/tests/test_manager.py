import datetime
import random
from itertools import chain
from unittest.mock import patch, Mock

from django.core.exceptions import FieldDoesNotExist, FieldError
from django.test import tag

import DBentry.models as _models
from DBentry.factory import make
from DBentry.managers import CNQuerySet, MIZQuerySet, build_date
from DBentry.tests.base import DataTestCase, MyTestCase
from DBentry.query import (
    BaseSearchQuery, PrimaryFieldsSearchQuery, ValuesDictSearchQuery)


class TestMIZQuerySet(DataTestCase):

    model = _models.Band
    raw_data = [
        {'band_name': 'Testband1'},
        {
            'band_name': 'Testband2', 'bandalias__alias': 'Coffee',
            'genre__genre': ['Rock', 'Jazz']
        },
        {
            'band_name': 'Testband3', 'bandalias__alias': ['Juice', 'Water'],
            'genre__genre': ['Rock', 'Jazz']
        },
    ]
    fields = ['band_name', 'genre__genre', 'bandalias__alias']

    @patch.object(
        ValuesDictSearchQuery, 'search',
        return_value=('ValuesDictSearchQuery', False)
    )
    @patch.object(
        PrimaryFieldsSearchQuery, 'search',
        return_value=('PrimaryFieldsSearchQuery', False)
    )
    @patch.object(
        BaseSearchQuery, 'search',
        return_value=('BaseSearchQuery', False)
    )
    def test_find_strategy_chosen(self, MockBSQ, MockPFSQ, MockVDSQ):
        # Assert that 'find' chooses the correct search strategy dependent on the
        # model's properties.
        model = Mock(name_field='', primary_search_fields=[], search_field_suffixes={})
        model.get_search_fields.return_value = []
        qs = Mock(model=model, find=MIZQuerySet.find)

        self.assertEqual(qs.find(qs, 'x'), 'BaseSearchQuery')

        model.primary_search_fields = ['Something']
        self.assertEqual(qs.find(qs, 'x'), 'PrimaryFieldsSearchQuery')

        model.name_field = 'Something again'
        self.assertEqual(qs.find(qs, 'x'), 'ValuesDictSearchQuery')

    def test_find(self):
        self.assertIn((self.obj1.pk, str(self.obj1)), self.queryset.find('Testband'))
        self.assertIn(
            (self.obj2.pk, str(self.obj2) + ' (Alias)'),
            self.queryset.find('Coffee')
        )
        self.assertFalse(self.queryset.find('Jazz'))


class TestAusgabeChronologicOrder(DataTestCase):

    model = _models.Ausgabe

    @classmethod
    def setUpTestData(cls):
        possible_pks = list(range(1, 1001))

        def get_random_pk():
            # 'randomize' the pk values so we cannot rely on them for ordering
            return possible_pks.pop(random.randrange(0, len(possible_pks) - 1))

        def get_date(month, year):
            return "{year}-{month}-{day}".format(
                year=str(year),
                month=str(month),
                day=random.randrange(1, 28)
            )
        cls.e_datum, cls.num, cls.lnum, cls.monat, cls.jg = (
            [], [], [], [], []
        )
        cls.mag = make(_models.Magazin)

        for jg, year in enumerate(range(1999, 2005), start=1):
            for i in range(1, 13):
                cls.e_datum.append(make(
                    cls.model, pk=get_random_pk(), magazin=cls.mag,
                    e_datum=get_date(i, year), ausgabejahr__jahr=year
                ))
                cls.num.append(make(
                    cls.model, pk=get_random_pk(), magazin=cls.mag,
                    ausgabenum__num=i, ausgabejahr__jahr=year
                ))
                cls.lnum.append(make(
                    cls.model, pk=get_random_pk(), magazin=cls.mag,
                    ausgabelnum__lnum=i, ausgabejahr__jahr=year
                ))
                cls.monat.append(make(
                    cls.model, pk=get_random_pk(), magazin=cls.mag,
                    ausgabemonat__monat__ordinal=i, ausgabejahr__jahr=year
                ))
                cls.jg.append(make(
                    cls.model, pk=get_random_pk(), magazin=cls.mag,
                    ausgabenum__num=i, jahrgang=jg
                ))
        cls.all = cls.e_datum + cls.num + cls.lnum + cls.monat + cls.jg
        super().setUpTestData()

    def setUp(self):
        # By having an empty self.test_data list, TestDataMixin won't add the
        # 'qs_obj' attributes - speeding up the tests. However, the objects
        # still need to be refreshed.
        for o in self.all:
            o.refresh_from_db()
        super().setUp
        self.queryset = self.model.objects.all()

    def test_a_num_queries(self):
        # Assert that a standard chronologic_order call does the expected
        # number of queries.
        # 3 queries:
        #   - for number of magazines
        #   - for number of jahr & jahrgang
        #   - for getting the numbers for the criteria (e_datum, etc.)
        with self.assertNumQueries(3):
            self.model.objects.chronologic_order()

    def test_chronologic_order_already_ordered(self):
        # Assert that chronologic_order is not attempted for a queryset that is
        # already chronologically ordered.
        queryset = self.model.objects.all()
        queryset.chronologically_ordered = True
        with self.assertNumQueries(0):
            queryset = queryset.chronologic_order()
        self.assertFalse(queryset.query.order_by)

    def test_chronologic_order_empty_queryset(self):
        # Assert that chronologic_order is not attempted for an empty queryset.
        queryset = self.model.objects.filter(id=1002).order_by()  # 1002 is not a valid ID
        with self.assertNumQueries(1):
            queryset = queryset.chronologic_order()
        self.assertEqual(
            queryset.query.order_by, tuple(self.model._meta.ordering))

    def test_chronologic_order_multiple_magazine(self):
        # Assert that chronologic_order is not attempt for a queryset with
        # multiple magazines.
        make(_models.Ausgabe, magazin__magazin_name='Bad', id=1002)
        queryset = self.model.objects.all()
        with self.assertNumQueries(1):
            queryset = queryset.chronologic_order()
        self.assertEqual(
            queryset.query.order_by, tuple(self.model._meta.ordering))

    def test_chronologic_order_empty_queryset_takes_ordering(self):
        # Assert that chronologic_order applies the passed in ordering to
        # an 'empty' queryset (or one with multiple magazines; functionally the
        # same thing).
        queryset = self.model.objects.all()
        self.assertEqual(
            queryset.none().chronologic_order('sonderausgabe').query.order_by,
            ('sonderausgabe', )
        )

    def test_chronologic_order_checks_for_pk_ordering(self):
        # Assert that chronologic_order checks the passed in ordering for the
        # primary key field an then puts that field at the very end of the final
        # ordering.
        for ordering in [[], ['pk'], ['-pk'], ['id'], ['-id'], ['pk', '-pk']]:
            with self.subTest(ordering=ordering):
                queryset = self.model.objects.chronologic_order(*ordering)
                if not ordering:
                    self.assertEqual(
                        queryset.query.order_by[-1], '-%s' % self.model._meta.pk.name,
                        msg=(
                            "If no ordering is specified, the last ordering "
                            "entry should default to '-{pk_name}'."
                        )
                    )
                else:
                    self.assertEqual(
                        queryset.query.order_by[-1], ordering[0],
                        msg="Last ordering entry should be a primary key."
                    )

    def test_chronologic_order_overrides_default_ordering(self):
        # Assert that chronologic_order accepts an ordering override via the
        # arguments.
        queryset = self.model.objects.chronologic_order(
            '-magazin', 'sonderausgabe', 'jahr')
        self.assertEqual(
            queryset.query.order_by[:3],
            ('-magazin', 'sonderausgabe', 'jahr')
        )

    def test_chronologic_order_jahr_over_jahrgang(self):
        # Assert that in a queryset with:
        # number of objects with jahr values > number of objects with a jahrgang value
        # the jahr ordering precedes jahrgang ordering.
        order_by = self.model.objects.chronologic_order().query.order_by
        self.assertGreater(
            order_by.index('jahrgang'), order_by.index('jahr'),
            msg="'jahr' ordering expected before 'jahrgang'."
        )

    def test_chronologic_order_jahrgang_over_jahr(self):
        # Assert that in a queryset with:
        # number of objects with jahrgang value > number of objects with jahr values
        # the jahrgang ordering precedes jahr ordering.
        ids = [obj.pk for obj in self.jg]
        order_by = self.model.objects.filter(
            id__in=ids).chronologic_order().query.order_by
        self.assertGreater(
            order_by.index('jahr'), order_by.index('jahrgang'),
            msg="'jahrgang' ordering expected before 'jahr'."
        )

    def test_chronologic_order_criteria_equal(self):
        # If none of the four criteria dominate, the default order should be:
        # 'e_datum', 'lnum', 'monat', 'num'
        queryset = self.model.objects.filter(
            id__in=[
                obj.pk for obj in chain(self.e_datum, self.lnum, self.monat, self.num)
            ]
        )
        expected = (
            'magazin', 'jahr', 'jahrgang', 'sonderausgabe',
            'e_datum', 'lnum', 'monat', 'num', '-id'
        )
        self.assertEqual(queryset.chronologic_order().query.order_by, expected)

    def test_find_keeps_order(self):
        # Assert that filtering the queryset via MIZQuerySet.find(ordered=True)
        # maintains the ordering established by chronologic_order.
        queryset = self.model.objects.filter(ausgabejahr__jahr=2000).chronologic_order()
        found_ids = [
            pk for pk, str_repr in queryset.find('2000', ordered=True)
        ]
        self.assertEqual(
            list(queryset.values_list('pk', flat=True)), found_ids
        )

    def test_update_names_after_chronologic_order(self):
        # Assert that resetting ordering for _update_names does not break the
        # ordering of the underlying queryset.
        expected = (
            'magazin', 'jahr', 'jahrgang', 'sonderausgabe',
            # Note that jahrgang objects have 'num' values, this means that
            # the 'num' criterion coming first.
            'num', 'e_datum', 'lnum', 'monat', '-id'
        )
        self.model.objects.update(_changed_flag=True)
        queryset = self.model.objects.chronologic_order()
        queryset._update_names()
        self.assertEqual(queryset.query.order_by, expected)

    def test_keeps_chronologically_ordered_value_after_cloning(self):
        queryset = self.model.objects.all()
        self.assertFalse(queryset.chronologically_ordered)
        self.assertFalse(queryset._chain().chronologically_ordered)
        queryset = queryset.chronologic_order()
        self.assertTrue(queryset.chronologically_ordered)
        self.assertTrue(queryset._chain().chronologically_ordered)

    def test_order_by_call_disables_chronologic_order(self):
        # A call of order_by should set chronologically_ordered to False.
        queryset = self.model.objects.all().chronologic_order()
        self.assertTrue(queryset.chronologically_ordered)
        queryset = queryset.order_by('magazin')
        self.assertFalse(queryset.chronologically_ordered)

    def test_update(self):
        # Assert that update calls are possible after chronologic_order().
        with self.assertNotRaises(FieldError):
            self.queryset.chronologic_order().update(beschreibung='abc')


class TestAusgabeIncrementJahrgang(DataTestCase):

    model = _models.Ausgabe

    raw_data = [
        {  # obj1: start_jg
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2000],
            'e_datum': '2000-06-01', 'ausgabemonat__monat__ordinal': [6],
            'ausgabenum__num': [6],
        },
        {  # obj2: start_jg - 1
            # Should belong to the previous jahrgang.
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2000],
            'e_datum': '2000-05-01', 'ausgabemonat__monat__ordinal': [5],
            'ausgabenum__num': [5],
        },
        {  # obj3: start_jg - 1
            # This object *starts* the jahrgang that obj2 also belongs to.
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [1999],
            'e_datum': '1999-06-01', 'ausgabemonat__monat__ordinal': [6],
            'ausgabenum__num': [6],
        },
        {  # obj4: start_jg
            # Test the differentation of jahr/num/monat values when the object
            # spans more than one year.
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2000, 2001],
            'e_datum': '2000-12-31', 'ausgabemonat__monat__ordinal': [12, 1],
            'ausgabenum__num': [12, 1],
        },
        {  # obj5: start_jg
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2001],
            'e_datum': '2001-05-01', 'ausgabemonat__monat__ordinal': [5],
            'ausgabenum__num': [5],
        },
        {  # obj6: start_jg + 1
            # This object begins the jahrgang following the starting jahrgang.
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2001],
            'e_datum': '2001-06-01', 'ausgabemonat__monat__ordinal': [6],
            'ausgabenum__num': [6],
        },
        {  # obj7: start_jg + 2
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [2002],
            'e_datum': '2002-06-01', 'ausgabemonat__monat__ordinal': [6],
            'ausgabenum__num': [6],
        },
        {  # obj8: ignored
            'magazin__magazin_name': 'Testmagazin', 'ausgabemonat__monat__ordinal': [6],
            'ausgabenum__num': [6]
        },
        {  # obj9: start_jg - 2
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [1998],
            'e_datum': '1998-06-01', 'ausgabemonat__monat__ordinal': [6],
            'ausgabenum__num': [6],
        },
        {  # obj10: start_jg - 3
            'magazin__magazin_name': 'Testmagazin', 'ausgabejahr__jahr': [1997],
            'e_datum': '1997-06-01', 'ausgabemonat__monat__ordinal': [6],
            'ausgabenum__num': [6],
        },
    ]

    def assertIncrementedUpdateDict(self, update_dict):
        # Check the dict 'update_dict' returned by increment_jahrgang for the
        # expected values.
        self.assertEqual(len(update_dict), 6, msg=str(update_dict))

        self.assertIn(7, update_dict)
        self.assertEqual(update_dict[7], [self.obj10.pk])
        self.assertIn(8, update_dict)
        self.assertEqual(update_dict[8], [self.obj9.pk])
        self.assertIn(9, update_dict)
        self.assertEqual(update_dict[9], [self.obj2.pk, self.obj3.pk])
        self.assertIn(10, update_dict)
        self.assertEqual(sorted(update_dict[10]), [self.obj1.pk, self.obj4.pk, self.obj5.pk])
        self.assertIn(11, update_dict)
        self.assertEqual(update_dict[11], [self.obj6.pk])
        self.assertIn(12, update_dict)
        self.assertEqual(update_dict[12], [self.obj7.pk])

    def assertIncrementedQuerySet(self, queryset):
        # Check the instance values.
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
        update_dict = self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertIncrementedUpdateDict(update_dict)
        self.assertIncrementedQuerySet(self.queryset)

    def test_increment_by_month(self):
        self.queryset.update(e_datum=None)
        self.obj1.refresh_from_db()
        update_dict = self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertIncrementedUpdateDict(update_dict)
        self.assertIncrementedQuerySet(self.queryset)

    def test_increment_by_num(self):
        self.queryset.update(e_datum=None)
        _models.AusgabeMonat.objects.all().delete()
        self.obj1.refresh_from_db()
        update_dict = self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertIncrementedUpdateDict(update_dict)
        self.assertIncrementedQuerySet(self.queryset)

    def test_increment_by_year(self):
        self.queryset.update(e_datum=None)
        _models.AusgabeMonat.objects.all().delete()
        _models.AusgabeNum.objects.all().delete()
        self.obj1.refresh_from_db()
        update_dict = self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)

        self.assertEqual(len(update_dict), 6, msg=str(update_dict))
        self.assertIn(7, update_dict)
        self.assertEqual(update_dict[7], [self.obj10.pk])
        self.assertIn(8, update_dict)
        self.assertEqual(update_dict[8], [self.obj9.pk])
        self.assertIn(9, update_dict)
        self.assertEqual(update_dict[9], [self.obj3.pk])
        self.assertIn(10, update_dict)
        self.assertEqual(update_dict[10], [self.obj1.pk, self.obj2.pk, self.obj4.pk])
        self.assertIn(11, update_dict)
        self.assertEqual(update_dict[11], [self.obj5.pk, self.obj6.pk])
        self.assertIn(12, update_dict)
        self.assertEqual(update_dict[12], [self.obj7.pk])

        queryset = self.queryset
        self.assertEqual(queryset.get(pk=self.obj1.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj2.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj3.pk).jahrgang, 9)
        self.assertEqual(queryset.get(pk=self.obj4.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj5.pk).jahrgang, 11)
        self.assertEqual(queryset.get(pk=self.obj6.pk).jahrgang, 11)
        self.assertEqual(queryset.get(pk=self.obj7.pk).jahrgang, 12)
        self.assertEqual(queryset.get(pk=self.obj8.pk).jahrgang, None)
        self.assertEqual(queryset.get(pk=self.obj9.pk).jahrgang, 8)
        self.assertEqual(queryset.get(pk=self.obj10.pk).jahrgang, 7)

    def test_increment_mixed(self):
        # Test increment_jahrgang with a mixed bag of values.
        # Remove the e_datum and month values from obj4 to obj7.
        ids = [self.obj4.pk, self.obj5.pk, self.obj6.pk, self.obj7.pk]
        _models.AusgabeMonat.objects.filter(ausgabe_id__in=ids).delete()
        _models.Ausgabe.objects.filter(pk__in=ids).update(e_datum=None)
        # Also remove num values from obj6 and obj7.
        _models.AusgabeNum.objects.filter(
            ausgabe_id__in=[self.obj6.pk, self.obj7.pk]).delete()

        update_dict = self.queryset.increment_jahrgang(start_obj=self.obj1, start_jg=10)
        self.assertIncrementedUpdateDict(update_dict)
        self.assertIncrementedQuerySet(self.queryset)

    def test_build_date(self):
        self.assertEqual(build_date([2000], [1], 31), datetime.date(2000, 1, 31))
        self.assertEqual(build_date([2000], [1], None), datetime.date(2000, 1, 1))

        self.assertEqual(build_date([2001, 2000], [12], None), datetime.date(2000, 12, 1))
        # If there's more than one month, build_date should set the day to the
        # last day of the min month.
        self.assertEqual(build_date([None, 2000], [12, 2], None), datetime.date(2000, 2, 29))
        # If there's more than one month and more than one year,
        # build_date should set the day to the last day of the max month
        self.assertEqual(build_date([2001, 2000], [12, 1], None), datetime.date(2000, 12, 31))

        self.assertIsNone(build_date([None], [None]))
        self.assertIsNotNone(build_date(2000, 1))


@tag("cn")
class TestCNQuerySet(DataTestCase):

    model = _models.Ausgabe

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.Magazin, magazin_name='Testmagazin')
        cls.obj1 = make(cls.model, magazin=cls.mag)
        cls.obj2 = make(
            cls.model, magazin=cls.mag, ausgabemonat__monat__monat='Dezember',
            ausgabelnum__lnum=12, ausgabenum__num=12, ausgabejahr__jahr=2000
        )
        cls.test_data = [cls.obj1, cls.obj2]
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        # Assign CNQuerySet as the manager for this TestCase
        self.queryset = CNQuerySet(self.model, query=self.queryset.query)
        self.qs_obj1 = self.queryset.filter(pk=self.obj1.pk)
        self.qs_obj2 = self.queryset.filter(pk=self.obj2.pk)
        # Do pending updates (_changed_flag set by signals, etc.)
        self.queryset._update_names()

    def test_update_sets_changed_flag(self):
        # _changed_flag should be set to True if an update is done without
        # _changed_flag as one of its arguments.
        self.obj1.qs().update(beschreibung='Test')
        values = self.queryset.values('_changed_flag').get(pk=self.obj1.pk)
        self.assertTrue(values['_changed_flag'])

    def test_update_not_sets_changed_flag(self):
        # If _changed_flag is a part of an update, that value should be maintained.
        self.obj1.qs().update(beschreibung='Test', _changed_flag=False)
        values = self.queryset.values('_changed_flag').get(pk=self.obj1.pk)
        self.assertFalse(values['_changed_flag'])

    def test_bulk_create_sets_changed_flag(self):
        # In order to update the created instances' names on their next
        # query/instantiation, bulk_create must include _changed_flag == True
        new_obj = self.model(
            magazin=self.mag, beschreibung='My Unique Name', sonderausgabe=True)
        self.queryset.bulk_create([new_obj])
        qs = self.queryset.filter(beschreibung='My Unique Name', sonderausgabe=True)
        self.assertTrue(qs.filter(_changed_flag=True).exists())

    def test_values_updates_name(self):
        # Calling values('_name') should cause a call to _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.values('_name'))
            self.assertTrue(mocked_func.called)

    def test_values_not_updates_name(self):
        # Calling values() without '_name' should not cause a call of _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.values('id'))
            self.assertFalse(mocked_func.called)

    def test_values_list_updates_name(self):
        # Calling values_list('_name') should cause a call to _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.values_list('_name'))
            self.assertTrue(mocked_func.called)

    def test_values_list_not_updates_name(self):
        # Calling values_list() without '_name' should not cause a call of _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.values_list('id'))
            self.assertFalse(mocked_func.called)

    def test_only_updates_name(self):
        # Calling only('_name') should cause a call of _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.only('_name'))
            self.assertTrue(mocked_func.called)

    def test_only_not_updates_name(self):
        # Calling only() without '_name' should not cause a call of _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.only('id'))
            self.assertFalse(mocked_func.called)

    def test_defer_updates_name(self):
        # Calling defer() without '_name' should cause a call of _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.defer('id'))
            self.assertTrue(mocked_func.called)

    def test_defer_not_updates_name(self):
        # Calling defer('_name') should not cause a call of _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.defer('_name'))
            self.assertFalse(mocked_func.called)

    def test_filter_updates_names(self):
        # Calling filter('_name') should cause a call of _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.filter(_name='Test'))
            self.assertTrue(mocked_func.called)

    def test_update_names(self):
        # Check the effects from calling _update_names.
        # Disable the 'automatic' updating of names:
        with patch.object(CNQuerySet, '_update_names'):
            self.obj1.qs().update(
                _changed_flag=True,
                beschreibung='Testinfo',
                sonderausgabe=True
            )
            self.obj2.qs().update(
                _changed_flag=True,
                beschreibung='Testinfo2',
                sonderausgabe=True
            )
            # Check that the _name was not updated:
            qs = self.queryset.values('_name')
            self.assertNotEqual(qs.get(pk=self.obj1.pk)['_name'], 'Testinfo')
            self.assertNotEqual(qs.get(pk=self.obj2.pk)['_name'], 'Testinfo2')
        # values('_name') will call _update_names.
        qs = self.queryset.values('_name')
        self.assertEqual(qs.get(pk=self.obj1.pk)['_name'], 'Testinfo')
        self.assertEqual(qs.get(pk=self.obj2.pk)['_name'], 'Testinfo2')

    def test_filter_not_updates_names(self):
        # Calling filter() without any arguments starting with '_name'
        # should not cause a call of _update_names.
        with patch.object(CNQuerySet, '_update_names') as mocked_func:
            list(self.queryset.filter(beschreibung='Test'))
            self.assertFalse(mocked_func.called)

    def test_update_names_num_queries_empty(self):
        # Assert that only a single query (filtering for _changed_flag) is run
        # when the no row in queryset has _changed_flag=True.
        self.queryset.update(_changed_flag=False)
        with self.assertNumQueries(1):
            self.queryset._update_names()

    def test_update_names_num_queries(self):
        # Should be six queries:
        # - one from querying the existence of _changed_flag records,
        # - one from calling values_dict,
        # - one each for every object to be updated,
        # - two for the transaction.atomic block
        self.queryset.update(_changed_flag=True)
        with self.assertNumQueries(6):
            self.queryset._update_names()

    def test_num_queries(self):
        # 3 queries for each call of _update_names from only, filter and
        # values_list + one query for the actual list.
        with self.assertNumQueries(4):
            list(self.queryset.only('_name').filter(_name='Testinfo').values_list('_name'))


class TestBuchQuerySet(DataTestCase):

    model = _models.Buch
    raw_data = [
        {'ISBN': '978-1-234-56789-7', 'EAN': '73513537'},
        {'ISBN': '978-4-56-789012-0', 'EAN': "1234567890128"}
    ]

    def test_filter_finds_isbn(self):
        isbn_10 = "123456789X"
        self.assertIn(self.obj1, self.queryset.filter(ISBN=isbn_10))
        isbn_10 = "1-234-56789-X"
        self.assertIn(self.obj1, self.queryset.filter(ISBN=isbn_10))

        isbn_13 = '9784567890120'
        self.assertIn(self.obj2, self.queryset.filter(ISBN=isbn_13))
        isbn_13 = '978-4-56-789012-0'
        self.assertIn(self.obj2, self.queryset.filter(ISBN=isbn_13))

    def test_filter_finds_ean(self):
        ean_8 = '7351-3537'
        self.assertIn(self.obj1, self.queryset.filter(EAN=ean_8))
        ean_13 = '1-234567-890128'
        self.assertIn(self.obj2, self.queryset.filter(EAN=ean_13))


class TestValuesDict(DataTestCase):

    model = _models.Band
    raw_data = [
        {'band_name': 'Testband1', },
        {
            'band_name': 'Testband2', 'bandalias__alias': 'Coffee',
            'genre__genre': ['Rock', 'Jazz']
        },
        {
            'band_name': 'Testband3', 'bandalias__alias': ['Juice', 'Water'],
            'genre__genre': ['Rock', 'Jazz']
        },
    ]
    fields = ['band_name', 'genre__genre', 'bandalias__alias']

    def test_values_dict(self):
        values = self.queryset.values_dict(*self.fields)
        expected = [
            (self.obj1.pk, {'band_name': ('Testband1', )}),
            (self.obj2.pk, {
                'band_name': ('Testband2', ), 'genre__genre': ('Jazz', 'Rock'),
                'bandalias__alias': ('Coffee', )
            }),
            (self.obj3.pk, {
                'band_name': ('Testband3', ), 'genre__genre': ('Jazz', 'Rock'),
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
        values = self.qs_obj1.values_dict(*self.fields, include_empty=True)
        expected = {
            'band_name': ('Testband1', ), 'genre__genre': (None, ),
            'bandalias__alias': (None, )
        }
        self.assertEqual(values.get(self.obj1.pk), expected)

    def test_values_dict_tuplfy(self):
        values = self.qs_obj2.values_dict(*self.fields, tuplfy=True)
        expected = (
            ('band_name', ('Testband2',)), ('genre__genre', ('Rock', 'Jazz')),
            ('bandalias__alias', ('Coffee',))
        )
        # Iterate through the expected_values and compare them individuallly;
        # full tuple comparison includes order equality - and we can't predict
        # the order of the tuples.
        for expected_values in expected:
            with self.subTest():
                self.assertIn(expected_values, values.get(self.obj2.pk))

    # Patching MIZQuerySet.values to find out how the primary key values are queried.
    @patch.object(MIZQuerySet, 'values')
    def test_values_dict_no_fields(self, mocked_values):
        # Assert that values_dict does not add a pk item if called without any
        # fields (implicitly querying all fields).
        self.qs_obj1.values_dict()
        self.assertTrue(mocked_values.called)
        self.assertEqual(mocked_values.call_args[0], ())

    @patch.object(MIZQuerySet, 'values')
    def test_values_dict_pk_in_fields(self, mocked_values):
        # Assert that values_dict queries for primary key values with the
        # alias 'pk' if called with it.
        self.qs_obj1.values_dict('band_name', 'pk')
        self.assertTrue(mocked_values.called)
        self.assertIn('pk', mocked_values.call_args[0])

    @patch.object(MIZQuerySet, 'values')
    def test_values_dict_meta_pk_in_fields(self, mocked_values):
        # Assert that values_dict keeps the model's pk name if called with it.
        self.qs_obj1.values_dict('band_name', 'id')
        self.assertTrue(mocked_values.called)
        self.assertIn('id', mocked_values.call_args[0])

    def test_values_dict_flatten(self):
        # Assert that single values are flattened.
        values = self.qs_obj2.values_dict(*self.fields, flatten=True)
        self.assertIn(self.obj2.pk, values)
        obj2_values = values.get(self.obj2.pk)
        self.assertIn('band_name', obj2_values)
        self.assertNotIsInstance(obj2_values['band_name'], tuple)

    def test_values_dict_flatten_reverse_relation(self):
        # Assert that multiple values (reverse relations) are never flattened.
        # obj2 has a single value for alias; which must not get flattened.
        values = self.qs_obj2.values_dict(*self.fields, flatten=True)
        self.assertIn(self.obj2.pk, values)
        obj2_values = values.get(self.obj2.pk)
        self.assertIn('bandalias__alias', obj2_values)
        self.assertIsInstance(obj2_values['bandalias__alias'], tuple)

        # also test if the multiple genres do not get flattened (however that would work..)
        self.assertIn('genre__genre', obj2_values)
        self.assertIsInstance(obj2_values['genre__genre'], tuple)

    def test_values_dict_flatten_no_fields(self):
        # This test just makes sure that values_dict doesn't error when no
        # fields are passed in. The process of finding the fields/field paths
        # to exclude from flattening is dependent on having passed in 'fields'.
        # Calling values() without params will fetch all the values of the base fields;
        # i.e. no reverse stuff so everything WILL be flattened.
        with self.assertNotRaises(Exception):
            self.qs_obj2.values_dict(flatten=True)

    def test_values_dict_flatten_with_invalid_field(self):
        # django's exception when calling values() with an invalid should
        # be the exception that propagates. No exception should be raised from
        # the process that determines the fields to be excluded even if a given
        # field does not exist. The process catches a FieldDoesNotExist but does
        # not act on it.
        with patch.object(MIZQuerySet, 'values'):
            with self.assertNotRaises(FieldDoesNotExist):
                self.queryset.values_dict('thisaintnofield', flatten=True)

        # Assert that the much more informative django FieldError is raised.
        with self.assertRaises(FieldError) as cm:
            self.queryset.values_dict('thisaintnofield', flatten=True)
        self.assertIn('Choices are', cm.exception.args[0])


class TestDuplicates(DataTestCase):

    model = _models.Musiker

    @classmethod
    def setUpTestData(cls):
        cls.test_data = [
            cls.model.objects.create(kuenstler_name='Bob'),
            cls.model.objects.create(kuenstler_name='Bob'),
            cls.model.objects.create(kuenstler_name='Bob'),
        ]

        super().setUpTestData()

    def get_duplicate_instances(self, *fields, queryset=None):
        if queryset is None:
            queryset = self.queryset
        duplicates = queryset.duplicates(*fields)
        return list(chain(*(dupe.instances for dupe in duplicates)))

    def test_a_baseline(self):
        duplicates = self.get_duplicate_instances('kuenstler_name')
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        self.assertIn(self.obj3, duplicates)

    def test_empty(self):
        # Assert that duplicates are not found by comparing empty values.
        duplicates = self.get_duplicate_instances('beschreibung')
        for obj in self.test_data:
            with self.subTest(obj=obj):
                self.assertNotIn(obj, duplicates)

    def test_duplicates_m2m(self):
        g1 = make(_models.Genre)
        g2 = make(_models.Genre)

        self.obj1.genre.add(g1)
        self.obj2.genre.add(g1)
        duplicates = self.get_duplicate_instances('kuenstler_name', 'genre')
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

        self.obj3.genre.add(g2)
        duplicates = self.get_duplicate_instances('kuenstler_name', 'genre')
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

        # obj1 and obj2 share a genre, but their total genres are not the same
        self.obj1.genre.add(g2)
        duplicates = self.get_duplicate_instances('kuenstler_name', 'genre')
        self.assertNotIn(self.obj1, duplicates)
        self.assertNotIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

    def test_duplicates_reverse_fk(self):
        self.obj1.musikeralias_set.create(alias='Beep')
        self.obj2.musikeralias_set.create(alias='Beep')
        duplicates = self.get_duplicate_instances('kuenstler_name', 'musikeralias__alias')
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

        self.obj3.musikeralias_set.create(alias='Boop')
        duplicates = self.get_duplicate_instances('kuenstler_name', 'musikeralias__alias')
        self.assertIn(self.obj1, duplicates)
        self.assertIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

        self.obj1.musikeralias_set.create(alias='Boop')
        duplicates = self.get_duplicate_instances('kuenstler_name', 'musikeralias__alias')
        self.assertNotIn(self.obj1, duplicates)
        self.assertNotIn(self.obj2, duplicates)
        self.assertNotIn(self.obj3, duplicates)

    def test_duplicates_reverse_fk_joins(self):
        # Assert that the number of duplicates found is not affected by table joins.
        self.obj1.musikeralias_set.create(alias='Beep')
        self.obj2.musikeralias_set.create(alias='Beep')
        self.obj1.musikeralias_set.create(alias='Boop')
        self.obj2.musikeralias_set.create(alias='Boop')
        duplicates = self.get_duplicate_instances('kuenstler_name', 'musikeralias__alias')
        self.assertEqual(len(duplicates), 2)


class TestHumanNameQuerySet(MyTestCase):

    def test_find_person(self):
        obj = make(_models.Person, vorname='Peter', nachname='Lustig')
        for name in ('Peter Lustig', 'Lustig, Peter'):
            with self.subTest():
                results = _models.Person.objects.find(name)
                msg = "Name looked up: %s" % name
                self.assertIn((obj.pk, 'Peter Lustig'), results, msg=msg)

    def test_find_autor(self):
        obj = make(
            _models.Autor,
            person__vorname='Peter', person__nachname='Lustig', kuerzel='PL'
        )
        names = (
            'Peter Lustig', 'Lustig, Peter', 'Peter (PL) Lustig',
            'Peter Lustig (PL)', 'Lustig, Peter (PL)'
        )
        for name in names:
            with self.subTest():
                results = _models.Autor.objects.find(name)
                msg = "Name looked up: %s" % name
                self.assertIn((obj.pk, 'Peter Lustig (PL)'), results, msg=msg)


class TestFindSpecialCases(DataTestCase):

    model = _models.Band
    raw_data = [{'band_name': 'Ümlautße'}]

    def test_find_sharp_s(self):
        # Assert that a 'ß' search term is handled properly.
        # ('ß'.casefold() performed in BaseSearchQuery.clean_string() results in 'ss')
        results = self.model.objects.find('ß')
        self.assertTrue(
            results, msg="Expected to find the instance with 'ß' in its name.")

    def test_find_umlaute(self):
        # SQLlite performs case sensitive searches for strings containing chars
        # outside the ASCII range (such as Umlaute ä, ö, ü).
        for q in ('ü', 'Ü'):
            with self.subTest(q=q):
                results = self.model.objects.find(q)
                self.assertTrue(
                    results,
                    msg="Expected to find matches regardless of case of Umlaut."
                )
