from nameparser import HumanName

from DBentry import utils
from DBentry.tests.base import MyTestCase

class TestTextUtils(MyTestCase):
    
    def test_concat_limit(self):
        t = ['2020', '2021', '2024']
        self.assertEqual(utils.concat_limit([]), '')
        self.assertEqual(utils.concat_limit(t), '2020, 2021, 2024')
        self.assertEqual(utils.concat_limit(t, width = 1), '2020, [...]')
        self.assertEqual(utils.concat_limit(t, width = 1, z = 6), '002020, [...]')
        
    def test_parse_name(self):
        expected = ("Alice Jane", "Tester")
        self.assertEqual(utils.parse_name("Alice Jane Tester"), expected)
        self.assertEqual(utils.parse_name("Prof. Alice Jane Tester"), expected)
        self.assertEqual(utils.parse_name("Alice Jane (Beep) Tester"), expected)
        self.assertEqual(utils.parse_name("Tester, Alice Jane"), expected)
        
    def test_coerce_human_name(self):
        # full_name is neither str nor HumanName
        self.assertIsInstance(utils.coerce_human_name(13), HumanName)
        self.assertIsInstance(utils.coerce_human_name('13'), HumanName)
        self.assertIsInstance(utils.coerce_human_name(HumanName('13')), HumanName)
        
