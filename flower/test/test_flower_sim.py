import unittest

from flower import builder


class FlowerSimTests(unittest.TestCase):
    def test_much_greater_than(self):
        self.assertTrue(builder.much_greater_than(1000, 1))
        self.assertFalse(builder.much_greater_than(1, 1000))

        self.assertTrue(builder.much_greater_than(6, 1))
        self.assertFalse(builder.much_greater_than(1, 6))
