import unittest

import scipy.spatial as sp

from core import segments


class SegmentTests(unittest.TestCase):
    def test_create_random(self):
        segs = segments.Segments(30)

        pos_4 = segs.position(4)
        pos_20 = segs.position(20)

        distance = sp.distance.euclidean(pos_4, pos_20)
        self.assertGreater(distance, 0.)

    def test_container_ids(self):
        segs = segments.Segments(30)
        segs.assign_container(4, 20)
        segs.assign_container(8, 31)

        self.assertEqual(20, segs.container(4))
        self.assertEqual(31, segs.container(8))
        self.assertEqual(0, segs.container(20))

    def test_compute_complete_hull(self):
        segs = segments.Segments(30)
        hull = segs.convex_hull()

        self.assertGreater(len(hull.simplices), 0)
