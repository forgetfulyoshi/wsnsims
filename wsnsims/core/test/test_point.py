import unittest

import numpy as np

from wsnsims.core import point


class PointTests(unittest.TestCase):
    def test_empty_new(self):
        v = point.Vec2()

        np.testing.assert_array_equal(np.zeros(2), v.nd)
        self.assertAlmostEqual(0., v.x)
        self.assertAlmostEqual(0., v.y)

    def test_populated_new(self):
        nd = np.array([1., 2.])
        v = point.Vec2(nd)

        np.testing.assert_array_equal(nd, v.nd)
        self.assertAlmostEqual(nd[0], v.x)
        self.assertAlmostEqual(nd[1], v.y)

    def test_equality(self):
        a = point.Vec2(np.array([2., 3.]))
        b = point.Vec2(np.array([2., 3.]))
        c = point.Vec2(np.array([2.1, 3.1]))

        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_subtraction(self):
        a = point.Vec2(np.array([2., 3.]))
        b = point.Vec2(np.array([5., -3.]))

        expected = point.Vec2(np.array([-3., 6.]))
        actual = a - b

        np.testing.assert_array_equal(expected.nd, actual.nd)
        self.assertEqual(expected, actual)

    def test_to_unit(self):
        a = point.Vec2(np.array([3., 3.]))

        expected = point.Vec2(np.array([1. / np.sqrt(2.), 1. / np.sqrt(2.)]))
        actual = a.to_unit()

        self.assertEqual(expected, actual)
        self.assertAlmostEqual(1., actual.norm())
