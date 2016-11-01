import unittest

import numpy as np

from core import tour


class TourTests(unittest.TestCase):
    def test_tour(self):
        points = np.random.rand(10, 2)
        route = tour.compute_tour(points)

        np.testing.assert_array_equal(points, route.points)
        self.assertEqual(len(route.points) + 1, len(route.vertices))

        # import matplotlib.pyplot as plt
        # plt.plot(points[:, 0], points[:, 1], 'o')
        # plt.plot(points[route.vertices[0], 0], points[route.vertices[0], 1], 'ro')
        # plt.plot(points[route.vertices, 0], points[route.vertices, 1], 'r--', lw=2)
        # plt.show()

    def test_collection_points(self):
        points = np.random.rand(10, 2)
        route = tour.compute_tour(points, radio_range=.05)

        self.assertEqual(len(route.points), len(route.collection_points))

        # import matplotlib.pyplot as plt
        # cps = route.collection_points
        # plt.plot(points[:, 0], points[:, 1], 'bo')
        # plt.plot(cps[:, 0], cps[:, 1], 'go')
        # plt.plot(cps[route.vertices[0], 0], cps[route.vertices[0], 1], 'ro')
        # plt.plot(points[route.vertices, 0], points[route.vertices, 1], 'r--', lw=2)
        # plt.plot(cps[route.vertices, 0], cps[route.vertices, 1], 'r--', lw=2)
        # plt.show()

    def test_collection_points_zero_radio_range(self):
        points = np.random.rand(30, 2)
        route = tour.compute_tour(points, radio_range=0.)

        np.testing.assert_array_equal(points, route.points)
        np.testing.assert_array_equal(route.points, route.collection_points)

        # import matplotlib.pyplot as plt
        # cps = route.collection_points
        # plt.plot(points[:, 0], points[:, 1], 'bo')
        # plt.plot(cps[:, 0], cps[:, 1], 'go')
        # plt.plot(cps[route.vertices[0], 0], cps[route.vertices[0], 1], 'ro')
        # plt.plot(points[route.vertices, 0], points[route.vertices, 1], 'r--', lw=2)
        # plt.plot(cps[route.vertices, 0], cps[route.vertices, 1], 'r--', lw=2)
        # plt.show()
