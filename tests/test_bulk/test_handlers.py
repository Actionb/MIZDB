import re
from typing import Union

from django.test import TestCase

from dbentry.tools.bulk.handlers import GroupingHandler, ItemHandler, NumericHandler, RangeGroupingHandler, RangeHandler


class TestItemHandler(TestCase):

    def test_init_sets_regex_from_kwarg(self):
        """Assert that init sets regex from a passed in kwarg."""
        handler = ItemHandler(regex='new_regex')
        self.assertEqual(handler.regex.pattern, 'new_regex')

    def test_init_compiles_pattern(self):
        """Assert that init sets self.regex to a compiled regex."""
        regex_type = type(re.compile(''))
        test_data = [
            ('regex', 'regex was string'),
            (re.compile('regex'), 'regex was already compiled')
        ]
        for regex, test_info in test_data:
            with self.subTest(info=test_info):
                handler = ItemHandler(regex=regex)
                self.assertIsInstance(handler.regex, regex_type)


class TestMethodsMixin:
    valid_data = ()
    invalid_data = ()

    def test_is_valid_valid_input(self: Union['TestMethodsMixin', 'HandlerTestCase']):
        for valid_input, _expected in self.valid_data:
            with self.subTest(input=valid_input):
                self.assertTrue(self.handler.is_valid(valid_input))

    def test_is_valid_invalid_input(self: Union['TestMethodsMixin', 'HandlerTestCase']):
        for invalid_input in self.invalid_data:
            with self.subTest(input=invalid_input):
                self.assertFalse(self.handler.is_valid(invalid_input))

    def test_handle(self: Union['TestMethodsMixin', 'HandlerTestCase']):
        for valid_input, expected in self.valid_data:
            with self.subTest(input=valid_input):
                self.assertEqual(list(self.handler.handle(valid_input)), expected)


class HandlerTestCase(TestCase):
    handler_class = None
    handler = None

    def setUp(self):
        super().setUp()
        if self.handler_class:
            self.handler = self.handler_class()


class TestNumericHandler(TestMethodsMixin, HandlerTestCase):
    handler_class = NumericHandler
    valid_data = [('1', ['1'])]
    invalid_data = ['a', '!']


class TestRangeHandler(TestMethodsMixin, HandlerTestCase):
    handler_class = RangeHandler
    valid_data = [
        ('1-2', ['1', '2']),
        ('1-4', ['1', '2', '3', '4'])
    ]
    invalid_data = ['1', '1-4*2', '1/2', '1--2', '1--2*3', '1-2**3']


class TestRangeGroupingHandler(TestMethodsMixin, HandlerTestCase):
    handler_class = RangeGroupingHandler
    valid_data = [
        ('1-4*2', [['1', '2'], ['3', '4']])
    ]
    invalid_data = ['1', '1-2', '1/2', '1--2', '1--2*3', '1-2**3']


class TestGroupingHandler(TestMethodsMixin, HandlerTestCase):
    handler_class = GroupingHandler
    valid_data = [
        ('1/2', [['1', '2']]),
        ('1/2/3', [['1', '2', '3']])
    ]
    invalid_data = ['1', '1-2', '1-4*2', '1--2', '1--2*3', '1-2**3']
