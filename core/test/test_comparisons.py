import unittest

from core import comparisons


class ComparisonsTests(unittest.TestCase):
    def test_much_greater_than(self):
        self.assertTrue(comparisons.much_greater_than(1000, 1))
        self.assertFalse(comparisons.much_greater_than(1, 1000))

        self.assertTrue(comparisons.much_greater_than(6, 1))
        self.assertFalse(comparisons.much_greater_than(1, 6))
