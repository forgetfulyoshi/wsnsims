from wsnsims.core import segment
import numpy as np


def test_segments_have_unique_ids():
    segments = [segment.Segment([0, 0]) for _ in range(10)]
    segment_ids_list = [s.segment_id for s in segments]
    segments_ids_set = set(segment_ids_list)
    assert len(segment_ids_list) == len(segments_ids_set)


def test_segments_can_be_used_for_drawing_lines():
    segment_1 = segment.Segment(np.array([0, -1]))
    segment_2 = segment.Segment(np.array([0, 1]))
    assert segment_1.location.distance(segment_2.location) == 2


def test_segments_have_arbitrary_cluster_ids():
    seg = segment.Segment(np.array([0, 0]))
    seg.cluster_id = 88
    assert seg.cluster_id == 88
