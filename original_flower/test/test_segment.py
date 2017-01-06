import unittest

from original_flower.segment import Segment
from original_flower.segment import initialize_traffic


class SegmentTests(unittest.TestCase):
    def setUp(self):
        self.segments = [Segment() for _ in range(5)]

    def tearDown(self):
        self.segments = None

    def test_initialize_traffic(self):
        """
        Test that we correctly set up the initial data transfers for a group
        of segments.
        """

        initialize_traffic(self.segments, 10, 2)

        for segment in self.segments:
            self.assertEqual(len(self.segments) - 1, len(segment.data))

    def test_initialize_traffic_uniform(self):
        """
        Test that holding standard deviation to zero results in the average volume
        being used for all transmissions.
        """

        initialize_traffic(self.segments, 10, 0)

        for segment in self.segments:
            self.assertEqual(len(self.segments) - 1, len(segment.data))
            for v in list(segment.data.values()):
                self.assertEqual(10, v)

    def test_initialize_traffic_invalid(self):

        self.assertRaises(AssertionError, initialize_traffic, self.segments, 0, 3)
        self.assertRaises(AssertionError, initialize_traffic, self.segments, 10, -1)
        self.assertRaises(AssertionError, initialize_traffic, self.segments, 10, 4)
