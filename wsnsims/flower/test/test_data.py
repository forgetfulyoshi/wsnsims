import itertools
import unittest

import numpy as np
import quantities as pq
from wsnsims.core.data import segment_volume
from wsnsims.core.segment import Segment
from wsnsims.flower.cell import Cell

from wsnsims.flower.data import cell_volume


class DataVolumeTests(unittest.TestCase):
    def setUp(self):
        src_locs = np.random.rand(5, 2) * pq.meter
        self.src_segments = [Segment(loc) for loc in src_locs]
        self.src_cell = Cell(0, 0)
        self.src_cell.segments = self.src_segments

        dst_locs = np.random.rand(5, 2) * pq.meter
        self.dst_segments = [Segment(loc) for loc in dst_locs]
        self.dst_cell = Cell(1, 1)
        self.dst_cell.segments = self.dst_segments

    def test_volume_equivalency(self):
        segment_pairs = list(itertools.product(self.src_segments,
                                               self.dst_segments))
        total_segment_volume = 0. * pq.bit
        for src, dst in segment_pairs:
            total_segment_volume += segment_volume(src, dst, self.env)

        total_cell_volume = cell_volume(self.src_cell, self.dst_cell, self.env)

        np.testing.assert_almost_equal(total_segment_volume, total_cell_volume)

    def test_repeated_equivalency(self):
        first_volume = cell_volume(self.src_cell, self.dst_cell, self.env)
        second_volume = cell_volume(self.src_cell, self.dst_cell, self.env)

        np.testing.assert_almost_equal(first_volume, second_volume)
