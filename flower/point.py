import collections
import math
from operator import attrgetter
from operator import methodcaller


class Vec2(object):
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def __str__(self):
        return "(%f, %f)" % (self.x, self.y)

    def __repr__(self):
        return "(%f, %f)" % (self.x, self.y)

    def __sub__(self, other):
        x = self.x - other.x
        y = self.y - other.y
        return Vec2(x, y)

    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        return Vec2(x, y)

    def __mul__(self, other):
        dot = self.x * other.x + self.y * other.y
        return dot

    def __xor__(self, other):
        cross = self.x * other.y - other.x * self.y
        return cross

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return id(self) == id(other)

    def normalized(self, origin=None):
        if not self.length():
            return Vec2(0, 0)

        if not origin:
            x = self.x / self.length()
            y = self.y / self.length()
        else:
            temp = self - origin
            x = temp.x / temp.length()
            y = temp.y / temp.length()

        return Vec2(x, y)

    def polar_angle(self, origin=None):
        if origin == self:
            return 0.0

        if origin:
            orig = origin
        else:
            orig = Vec2(0, 0)

        new_vec = self - orig
        new_vec_theta = math.atan2(new_vec.y, new_vec.x)

        return new_vec_theta

    def distance(self, other):
        temp = self - other
        dist = temp.length()
        return dist

    def length(self):
        length = math.hypot(self.x, self.y)
        return length

    def set_length(self, length):
        v = self.normalized()
        self.x = v.x * length
        self.y = v.y * length
        return self


def direction(p0, p1, p2):
    cp = (p2 - p0) ^ (p1 - p0)
    return cp


def sort_polar(points, field=None):
    if not field:
        lowest = min(points, key=attrgetter('y', 'x'))
        # noinspection PyArgumentList
        sorted_points = sorted(points, key=methodcaller('polar_angle', origin=lowest))
    else:
        lowest = min(points, key=attrgetter(field + '.y', field + '.x'))
        decorated = [(getattr(p, field).polar_angle(origin=getattr(lowest, field)), i, p) for i, p in enumerate(points)]
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
