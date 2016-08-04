import math
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

    def __xor__(self, other):
        cross = self.x * other.y - other.x * self.y
        return cross

    def normalized(self, origin=None):
        if not origin:
            x = self.x / self.length()
            y = self.y / self.length()
        else:
            temp = self - origin
            x = temp.x / temp.length()
            y = temp.y / temp.length()

        return Vec2(x, y)

    def polar_angle(self, origin=None):

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


def direction(p0, p1, p2):
    cp = (p2 - p0) ^ (p1 - p0)
    return cp


def sort_polar(points, start):
    if start in points:
        points.remove(start)

    # noinspection PyArgumentList
    s_points = sorted(points, key=methodcaller('polar_angle', origin=start))
    n_points = list()

    n_points.append(start)
    for point in s_points:

        if point == start:
            continue

        last = n_points[-1:][0]

        last_cp = start ^ last
        current_cp = start ^ point

        if current_cp == last_cp:
            last_dist = start.distance(last)
            current_dist = start.distance(point)
            if last_dist < current_dist:
                n_points.pop()

        n_points.append(point)

    return n_points


def graham_scan(points):
    hull = list()

    #
    # Find the point with the minimum y-coordinate
    #
    lowest = points[0]
    for p in points:
        if lowest.y > p.y:
            lowest = p

    #
    # Don't want to re-refernce the starting point
    #
    points.remove(lowest)

    sorted_points = sort_polar(points, lowest)

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

    hull.append(lowest)
    interior = list(set(sorted_points).difference(hull))
    return hull, interior
