import numpy as np

from wsnsims.core import point


def test_points_can_be_set_by_lists():
    vec = point.Vec2([1, -2])
    assert vec.x == 1
    assert vec.y == -2


def test_points_can_be_set_by_np_arrays():
    vec = point.Vec2(np.array([1, -2]))
    assert vec.x == 1
    assert vec.y == -2


def test_empty_points_default_to_0_0():
    vec = point.Vec2()
    assert vec.x == 0
    assert vec.y == 0


def test_points_can_be_added():
    point_1 = point.Vec2([1, 2])
    point_2 = point.Vec2([3, 4])

    resultant = point_1 + point_2
    assert resultant.x == 4
    assert resultant.y == 6


def test_points_can_be_subtracted():
    point_1 = point.Vec2([1, 2])
    point_2 = point.Vec2([3, 4])

    resultant = point_1 - point_2
    assert resultant.x == -2
    assert resultant.y == -2
