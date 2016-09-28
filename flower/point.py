import collections
import math
from operator import attrgetter
from operator import methodcaller


class Vec2Error(Exception):
    pass


class Vec2(object):
    def __init__(self, x, y):
        self._x = 0
        self._y = 0

        self.x = x
        self.y = y

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

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        f_value = float(value)

        if math.isnan(f_value):
            raise Vec2Error("Attempt to set x to nan (pre-cast: {})".format(value))

        if math.isinf(f_value):
            raise Vec2Error("Attempt to set x to inf (pre-case: {})".format(value))

        if f_value > 10000:
            raise Vec2Error("Vector is growing very large in the x dimension ({})".format(f_value))

        if f_value < -10000:
            raise Vec2Error("Vector is growing very small in the x dimension ({})".format(f_value))

        self._x = f_value

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        f_value = float(value)

        if math.isnan(f_value):
            raise Vec2Error("Attempt to set y to nan (pre-cast: {})".format(value))

        if math.isinf(f_value):
            raise Vec2Error("Attempt to set y to inf (pre-case: {})".format(value))

        if f_value > 10000:
            raise Vec2Error("Vector is growing very large in the y dimension ({})".format(f_value))

        if f_value < -10000:
            raise Vec2Error("Vector is growing very small in the y dimension ({})".format(f_value))

        self._y = f_value

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

    def scale(self, scale):
        self.x *= scale
        self.y *= scale
        return self


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


class WorldPositionMixin(Vec2):
    def __init__(self, x=0.0, y=0.0):
        super(WorldPositionMixin, self).__init__(x, y)
