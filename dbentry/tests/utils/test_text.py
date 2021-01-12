from dbentry import utils
from dbentry.tests.base import MyTestCase


class TestTextUtils(MyTestCase):

    def test_concat_limit(self):
        t = ['2020', '2021', '2024']
        params = [
            ({'values': []}, ''),
            ({'values': t}, '2020, 2021, 2024'),
            ({'values': t, 'width': 1}, '2020, [...]'),
            ({'values': t, 'width': 0}, '2020, 2021, 2024'),
            ({'values': [''] + t}, '2020, 2021, 2024'),
            ({'values': [None] + t}, '2020, 2021, 2024'),
            ({'values': iter(t)}, '2020, 2021, 2024'),
            ({'values': filter(lambda i:i, t)}, '2020, 2021, 2024'),
            ({'values': (i for i in t)}, '2020, 2021, 2024')
        ]
        for kwargs, expected in params:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(utils.concat_limit(**kwargs), expected)

    def test_parse_name(self):
        expected = ("Alice Jane", "Tester")
        params = [
            ("Alice Jane Tester", expected),
            ("Prof. Alice Jane Tester", expected),
            ("Alice Jane (Beep) Tester", expected),
            ("Tester, Alice Jane", expected),
            ("Tester", ('', 'Tester'))
        ]
        for name, expected in params:
            with self.subTest(name=name):
                self.assertEqual(utils.parse_name(name), expected)
