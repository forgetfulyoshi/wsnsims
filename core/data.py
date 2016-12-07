import numpy as np

from core import environment

data_memo = {}


def volume(src, dst):
    if (src, dst) in data_memo:
        return data_memo[(src, dst)]

    env = environment.Environment()
    size = np.random.normal(env.isdva, env.isdvsd)
    size *= env.isdva.units
    data_memo[(src, dst)] = size
    return size
