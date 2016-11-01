import numpy as np
import scipy.spatial as sp


class Segments(object):
    def __init__(self, count):
        self._pos = np.random.rand(count, 2)
        self._containers = np.zeros(count, dtype=float)

    def position(self, segment):
        pos = self._pos[segment]
        return pos

    def container(self, segment):
        container_id = self._containers[segment]
        return container_id

    def assign_container(self, segment, container):
        self._containers[segment] = container

    def convex_hull(self):
        hull = sp.ConvexHull(self._pos)
        return hull

