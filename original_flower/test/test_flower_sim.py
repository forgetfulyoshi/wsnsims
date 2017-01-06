import unittest

from original_flower import flower_sim


class FlowerSimTests(unittest.TestCase):
    def test_much_greater_than(self):
        self.assertTrue(flower_sim.much_greater_than(1000, 1))
        self.assertFalse(flower_sim.much_greater_than(1, 1000))

        self.assertTrue(flower_sim.much_greater_than(6, 1))
        self.assertFalse(flower_sim.much_greater_than(1, 6))
