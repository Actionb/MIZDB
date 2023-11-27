from dbentry.utils import flatten
from tests.case import MIZTestCase


class TestFlatten(MIZTestCase):
    def test_flatten(self):
        test_data = [
            ([1, 2, 3, 4], [1, 2, 3, 4]),
            ([[1, 2], [3, 4]], [1, 2, 3, 4]),
            ([[1, 2], [3], 4], [1, 2, 3, 4]),
            ([[1], [2], [[3], 4]], [1, 2, 3, 4]),
            (["2001", "2002"], ["2001", "2002"]),
        ]
        for _list, expected in test_data:
            with self.subTest(_list=_list):
                self.assertEqual(flatten(_list), expected)
