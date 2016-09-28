import random

from flower import params

data_memo = {}


def data(src, dst):
    if (src, dst) in data_memo:
        return data_memo[(src, dst)]

    size = random.gauss(params.ISDVA, params.ISDVSD)
    data_memo[(src, dst)] = size
    return size
