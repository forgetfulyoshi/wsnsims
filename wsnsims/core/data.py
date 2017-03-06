import numpy as np

data_memo = {}


def segment_volume(src, dst, env):
    if (src, dst) in data_memo:
        return data_memo[(src, dst)]

    size = np.random.normal(env.isdva, env.isdvsd)
    # size *= env.isdva.units
    data_memo[(src, dst)] = size
    return size
