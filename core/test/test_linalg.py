import unittest

import numpy as np
import quantities as pq

from core import linalg


class LinalgTests(unittest.TestCase):
    def test_centroid(self):
        points = np.random.rand(30, 2)
        com = linalg.centroid(points)

        self.assertEqual(points[0].shape, com.shape)

    def test_centroid_with_units(self):
        points = np.random.rand(30, 2) * pq.m
        com = linalg.centroid(points)

        self.assertEqual(com.units, pq.m)
        self.assertEqual(points[0].shape, com.shape)
