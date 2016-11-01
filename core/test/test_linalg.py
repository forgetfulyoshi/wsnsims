import unittest

import numpy as np
import quantities as pq

from core import linalg


class LinalgTests(unittest.TestCase):
    def test_ccw(self):
        p0 = np.array([0., 0.])
        p1 = np.array([.5, .5])

        # Test that counterclockwise returns True
        p2 = np.array([.5, 1.])
        self.assertTrue(linalg.ccw(p0, p1, p2))

        # Test that clockwise returns False
        p2 = np.array([.5, 0.])
        self.assertFalse(linalg.ccw(p0, p1, p2))

        # Test that colinear returns False
        p2 = np.array([1., 1.])
        self.assertFalse(linalg.ccw(p0, p1, p2))

    def test_ccw_with_units(self):
        p0 = np.array([0., 0.]) * pq.m
        p1 = np.array([.5, .5]) * pq.m
        p2 = np.array([.5, 1.]) * pq.m
        self.assertTrue(linalg.ccw(p0, p1, p2))

    def test_ccw_only_2d(self):
        p0 = np.array([0., 0.])
        p1 = np.array([.5, .5])
        p2 = np.array([.5, 0.])

        with self.assertRaises(linalg.LinalgError):
            linalg.ccw(np.array([0.]), p1, p2)

        with self.assertRaises(linalg.LinalgError):
            linalg.ccw(p0, np.array([.5, 0., 0.]), p2)

        with self.assertRaises(linalg.LinalgError):
            linalg.ccw(p0, p1, np.array([]))

    def test_perpendicular(self):
        start = np.array([0., 1.])
        end = np.array([1., 1.])
        p = np.array([.5, .5])

        perp = linalg.perpendicular(start, end, p)
        np.testing.assert_allclose(perp, np.array([.5, 1.]))

    def test_perpendicular_out_of_range(self):
        start = np.array([0., 1.])
        end = np.array([1., 1.])
        p = np.array([2., .5])

        expected = np.array([np.inf, np.inf])
        np.testing.assert_array_equal(expected, linalg.perpendicular(start, end, p))

        p = np.array([-2., .5])
        np.testing.assert_array_equal(expected, linalg.perpendicular(start, end, p))

    def test_perpendicular_with_units(self):
        start = np.array([0., 1.]) * pq.m
        end = np.array([1., 1.]) * pq.m
        p = np.array([.5, 0.]) * pq.m

        perp = linalg.perpendicular(start, end, p)
        self.assertEqual(perp.units, pq.m)

        # Have to just test the magnitude as assert_allclose doesn't like units
        expected = np.array([0.5, 1.]) * pq.m
        np.testing.assert_allclose(perp.magnitude, expected.magnitude)

    def test_centroid(self):
        points = np.random.rand(30, 2)
        com = linalg.centroid(points)

        self.assertEqual(points[0].shape, com.shape)

    def test_centroid_with_units(self):
        points = np.random.rand(30, 2) * pq.m
        com = linalg.centroid(points)

        self.assertEqual(com.units, pq.m)
        self.assertEqual(points[0].shape, com.shape)