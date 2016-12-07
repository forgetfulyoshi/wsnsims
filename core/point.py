import collections
import math
from operator import attrgetter
from operator import methodcaller

import numpy as np


class Vec2Error(Exception):
    pass


class Vec2(object):
    def __init__(self, nd=None):
        if not isinstance(nd, np.ndarray):
            self.nd = np.zeros(2)
        else:
            self.nd = nd

    @property
    def x(self):
        return self.nd[0]

    @x.setter
    def x(self, value):
        self.nd[0] = value

    @property
    def y(self):
        return self.nd[1]

    @y.setter
    def y(self, value):
        self.nd[1] = value

    def __str__(self):
        return "({nd[0]}, {nd[1]})".format(nd=self.nd)

    def __repr__(self):
        return str(self)

    def __sub__(self, other):
        return Vec2(nd=(self.nd - other.nd))

    def __add__(self, other):
        return Vec2(nd=(self.nd + other.nd))

    def dot(self, other):
        return np.dot(self.nd, other.nd)

    def cross(self, other):
        return np.cross(self.nd, other.nd)

    def to_unit(self, origin=None):

        if not origin:
            nd = self.nd / self.norm()
        else:
            temp = self - origin
            nd = temp.nd / temp.norm()

        return Vec2(nd=nd)

    def polar_angle(self, origin=None):
        if origin == self:
            return 0.0

        if origin:
            orig = origin
        else:
            orig = Vec2(np.zeros(2))

        new_vec = self - orig
        new_vec_theta = math.atan2(new_vec.y, new_vec.x)

        return new_vec_theta

    def distance(self, other):
        temp = self - other
        return temp.norm()

    def norm(self):
        return np.linalg.norm(self.nd)

    def set_length(self, length):
        self.nd = np.linalg.norm(self.nd) * length
        return self

    def scale(self, scale):
        self.nd *= scale
        return self

    def __eq__(self, other):
        return np.allclose(self.nd, other.nd)


def closest_point(v, w, p):
    """
    Find the point closest to p on the line between v and w
    Modified from StackOverflow at http://stackoverflow.com/a/1501725

    Returns the distance and the point on the line segment between v and w
    """
    length = v.distance(w) ** 2
    t = max(0, min(1, ((p - v) * (w - v)) / length))
    projection = v + (w - v).scale(t)
    return projection.distance(p), projection


def direction(p0, p1, p2):
    cp = (p2 - p0) ^ (p1 - p0)
    return cp


def sort_polar(points, field=None):
    if not field:
        lowest = min(points, key=attrgetter('y', 'x'))
        # noinspection PyArgumentList
        sorted_points = sorted(points,
                               key=methodcaller('polar_angle', origin=lowest))



    else:
        lowest = min(points, key=attrgetter(field + '.y', field + '.x'))
        decorated = [(getattr(p, field).polar_angle(
            origin=getattr(lowest, field)), i, p) for i, p in
                     enumerate(points)]
        decorated.sort()
        sorted_points = [p for _, _, p in decorated]

    return sorted_points


def rotate_to_start(points, new_start):
    d = collections.deque(points)
    start_index = points.index(new_start)
    d.rotate(start_index * -1)
    rotated_points = list(d)
    return rotated_points


def graham_scan(points):
    my_points = list(points)

    sorted_points = sort_polar(my_points)

    hull = list()
    hull.append(sorted_points[0])
    hull.append(sorted_points[1])
    hull.append(sorted_points[2])

    for i in range(3, len(sorted_points)):
        pi = sorted_points[i]

        turn = direction(hull[-2:][0], hull[-1:][0], pi)
        while turn > 0.0:
            hull.pop()
            turn = direction(hull[-2:][0], hull[-1:][0], pi)

        hull.append(pi)

    interior = list(set(sorted_points).difference(hull))
    return hull, interior


class WorldPositionMixin(Vec2):
    def __init__(self, x=0.0, y=0.0):
        super(WorldPositionMixin, self).__init__(x, y)
