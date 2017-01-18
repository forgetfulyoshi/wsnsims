import numpy as np

from core import environment

from flower.cell import Cell

data_memo = {}


def volume(src, dst):
    if isinstance(src, Cell):
        return cell_volume(src, dst)

    if (src, dst) in data_memo:
        return data_memo[(src, dst)]

    env = environment.Environment()
    size = np.random.normal(env.isdva, env.isdvsd)
    size *= env.isdva.units
    data_memo[(src, dst)] = size
    return size


def cell_volume(src, dst):
    """

    :param src:
    :type src: Cell
    :param dst:
    :type dst: Cell
    :return:
    """
    segment_pairs = [(s, d) for s in src.segments for d in dst.segments
                     if s != d]

    env = environment.Environment()
    total_data = 0. * env.isdva.units
    for s, d in segment_pairs:
        if (s, d) in data_memo:
            total_data += data_memo[(s, d)]

        size = np.random.normal(env.isdva, env.isdvsd)
        size *= env.isdva.units
        data_memo[(s, d)] = size
        total_data += size

    return total_data
