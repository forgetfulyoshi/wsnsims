import numpy as np
import quantities as pq


class SingletonDecorator:
    """
    From http://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html
    """

    def __init__(self, klass):
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kwds):
        if not self.instance:
            self.instance = self.klass(*args, **kwds)
        return self.instance


class _Environment(object):
    def __init__(self):
        # Common things to change
        self.mdc_count = 5
        self.segment_count = 12
        self.comms_range = 100. * pq.m
        self.isdva = 45. * pq.mebi * pq.bit
        self.isdvsd = 3.

        # Used for computing movement energy use
        self.move_cost = 1. * pq.J / pq.m
        self.mdc_speed = 1. * pq.m / pq.s

        # Used for computing communication energy use
        self.comms_rate = 0.1 * pq.mebi * pq.bit / pq.s
        self.delta = 2
        self.alpha = 100. * pq.nano * pq.J
        self.beta = 0.1 * pq.nano * pq.J / pq.m ** self.delta

        # Size of the simulated grid
        self.grid_width = 1200. * pq.m
        self.grid_height = 1200. * pq.m

    @property
    def comms_cost(self):
        """ The energy required to transmit 1 bit in J/Mb """
        j = self.alpha + self.beta * np.power(self.comms_range, self.delta)
        jpb = j / (pq.mebi * pq.bit)
        return jpb


Environment = SingletonDecorator(_Environment)
