import math

import numpy as np


class Vec2(object):
    def __init__(self, nd=None):
        if isinstance(nd, list):
            self.nd = np.array(nd)
        elif not isinstance(nd, np.ndarray):
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




