import itertools

import quantities as pq

from wsnsims.core.data import segment_volume


def cell_volume(src, dst, env):
    """

    :param src:
    :type src: flower.cell.Cell
    :param dst:
    :type dst: flower.cell.Cell
    :param env:
    :type env: core.environment.Environment
    :return:
    """

    segment_pairs = itertools.product(src.segments, dst.segments)
    total_volume = 0. * pq.bit
    for src, dst in segment_pairs:
        total_volume += segment_volume(src, dst, env)

    return total_volume
