import random
import unittest
from operator import attrgetter

from original_flower.grid import Cell
from original_flower.point import Vec2
from original_flower.point import direction
from original_flower.point import graham_scan
from original_flower.point import rotate_to_start
from original_flower.point import sort_polar


class Vec2Tests(unittest.TestCase):
    def test_addition(self):
        vec1 = Vec2(3, -5)
        vec2 = Vec2(4, -2)
        result = vec1 + vec2
        expected = Vec2(7, -7)

        self.assertEqual((expected.x, expected.y), (result.x, result.y))

    def test_subtraction(self):
        vec1 = Vec2(3, -5)
        vec2 = Vec2(4, -2)
        result = vec1 - vec2
        expected = Vec2(-1, -3)

        self.assertEqual((expected.x, expected.y), (result.x, result.y))

    def test_cross_product(self):
        vec1 = Vec2(3, -5)
        vec2 = Vec2(4, -2)
        result = vec1 ^ vec2
        expected = 14  # WolframAlpha

        self.assertEqual(expected, result)

    def test_turns_left(self):
        vec1 = Vec2(1, 1)
        vec2 = vec1 + Vec2(0, 2)
        turn = direction(Vec2(0, 0), vec1, vec2)
        self.assertLess(turn, 0)

    def test_turns_right(self):
        vec1 = Vec2(1, 1)
        vec2 = vec1 + Vec2(2, 0)
        turn = direction(Vec2(0, 0), vec1, vec2)
        self.assertGreater(turn, 0)

    def test_turns_straight(self):
        vec1 = Vec2(1, 1)
        vec2 = vec1 + Vec2(1, 1)
        turn = direction(Vec2(0, 0), vec1, vec2)
        self.assertEqual(turn, 0)

    def test_grow(self):
        vec = Vec2(1, 1)
        vec.set_length(5)
        self.assertAlmostEqual(5, vec.length())

    def test_shrink(self):
        vec = Vec2(10, 10)
        vec.set_length(3)
        self.assertAlmostEqual(3, vec.length())

    def test_dot_product(self):
        vec1 = Vec2(3, 8)
        vec2 = Vec2(11, -3)

        result = vec1 * vec2
        expected = 9

        self.assertEqual(expected, result)

    def test_dot_product_commutative(self):
        vec1 = Vec2(3, 8)
        vec2 = Vec2(11, -3)

        self.assertEqual(vec1 * vec2, vec2 * vec1)

    def test_dot_product_distributive(self):
        vec1 = Vec2(3, 8)
        vec2 = Vec2(11, -3)
        vec3 = Vec2(-4, 17)

        self.assertEqual(vec1 * (vec2 + vec3), vec1 * vec2 + vec1 * vec3)


class ConvexHullTests(unittest.TestCase):
    def test_graham_scan(self):
        points = list()
        for _ in range(1, 50):
            x = random.randint(1, 1000)
            y = random.randint(1, 1000)
            p = Vec2(x, y)
            points.append(p)

        start = min(points, key=attrgetter('y', 'x'))
        hull, interior = graham_scan(points)

        self.assertEqual(start, hull[0])

        for point in hull:
            self.assertNotIn(point, interior)

        p0 = hull[0]
        p1 = hull[1]
        for p2 in hull[2:]:
            self.assertLess(direction(p0, p1, p2), 0)
            p0 = p1
            p1 = p2

    def test_graham_scan_multi_start(self):
        points = list()
        for _ in range(1, 50):
            x = random.randint(1, 1000)
            y = random.randint(1, 1000)
            p = Vec2(x, y)
            points.append(p)

        start_points = list()
        start_points.append(min(points, key=attrgetter('x', 'y')))
        start_points.append(min(points, key=attrgetter('y', 'x')))
        start_points.append(max(points, key=attrgetter('x', 'y')))
        start_points.append(max(points, key=attrgetter('y', 'x')))

        for start in start_points:
            hull, interior = graham_scan(points)

            hull = rotate_to_start(hull, start)
            self.assertEqual(start, hull[0])

            p0 = hull[0]
            p1 = hull[1]
            for p2 in hull[2:]:
                self.assertLess(direction(p0, p1, p2), 0)
                p0 = p1
                p1 = p2


class PolarSortTests(unittest.TestCase):
    def test_sort(self):
        points = [Vec2(0, 0)]
        for _ in range(1, 50):
            x = random.randint(1, 1000)
            y = random.randint(1, 1000)
            p = Vec2(x, y)
            points.append(p)

        sorted_points = sort_polar(points)
        self.assertEqual(len(points), len(sorted_points))

        last = sorted_points[0]
        for point in sorted_points[1:]:
            self.assertLess(last.polar_angle(), point.polar_angle())
            last = point

    def test_equal_angle(self):
        points = list()
        for i in range(1, 20, 3):
            x = 2 * i
            y = i
            points.append(Vec2(x, y))

        sorted_points = sort_polar(points)

        self.assertEqual(len(points), len(sorted_points))
        self.assertEqual(points[0], sorted_points[0])
        self.assertEqual(points[-1:][0], sorted_points[-1:][0])

    def test_sort_attribute(self):
        c = Cell()
        c.collection_point = Vec2(0, 0)
        cells = [c]
        for _ in range(1, 50):
            x = random.randint(1, 1000)
            y = random.randint(1, 1000)
            cell = Cell()
            cell.collection_point = Vec2(x, y)
            cells.append(cell)

        sorted_cells = sort_polar(cells, field='collection_point')

        self.assertEqual(len(cells), len(sorted_cells))

        last = sorted_cells[0]
        for cell in sorted_cells[1:]:
            self.assertLessEqual(last.collection_point.polar_angle(), cell.collection_point.polar_angle())
            last = cell


if __name__ == '__main__':
    unittest.main()
