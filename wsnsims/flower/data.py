import itertools

from wsnsims.core.data import segment_volume

data_memo = {}


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

    if (src, dst) in data_memo:
        return data_memo[(src, dst)]

    segment_pairs = itertools.product(src.segments, dst.segments)
    total_volume = 0.  # pq.bit
    for src, dst in segment_pairs:
        total_volume += segment_volume(src, dst, env)

    data_memo[(src, dst)] = total_volume
    return total_volume
