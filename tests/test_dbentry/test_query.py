from unittest.mock import patch

from django.core.exceptions import FieldDoesNotExist, FieldError

from dbentry.query import MIZQuerySet
from tests.case import DataTestCase
from tests.factory import make
from tests.models import Band


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
        # noinspection PyUnresolvedReferences
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

    # noinspection SpellCheckingInspection
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
