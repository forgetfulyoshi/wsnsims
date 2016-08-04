import unittest

from flower.point import Vec2
from flower.point import direction


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

if __name__ == '__main__':
    unittest.main()
