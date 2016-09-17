import random

from flower import constants

data_memo = {}


def data(src, dst):
    if (src, dst) in data_memo:
        return data_memo[(src, dst)]

    size = random.gauss(constants.ISDVA, constants.ISDVSD)
    data_memo[(src, dst)] = size
    return size
