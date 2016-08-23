import random
import unittest
from operator import attrgetter

# import matplotlib.pyplot as plt

from flower.grid import Cell
from flower.tour import find_tour
from flower.tour import tour_length


class TourTests(unittest.TestCase):
    def test_n_element_tour(self):
        cells = list()
        for _ in range(20):
            x = random.randint(1, 1000)
            y = random.randint(1, 1000)
            cell = Cell(x, y)
            cells.append(cell)

        start = min(cells, key=attrgetter('y', 'x'))
        tour = find_tour(cells, 2, start)

        self.assertEqual(len(cells) + 1, len(tour))
        self.assertEqual(start, tour[0])
        self.assertEqual(start, tour[-1:][0])

        # x = [c.x for c in tour]
        # y = [c.y for c in tour]
        # plt.plot(x, y)
        #
        # x = [c.x for c in cells]
        # y = [c.y for c in cells]
        # plt.plot(x, y, 'ro')
        #
        # plt.plot([start.x], [start.y], 'go')
        # plt.show()

    def test_one_element_tour_length(self):
        cell = Cell()
        cell.x, cell.y = 5, 30

        length = tour_length([cell])
        self.assertEqual(0, length)

    def test_one_element_tour(self):
        cell = Cell()
        cell.x, cell.y = 5, 30

        tour = find_tour([cell])
        self.assertListEqual([cell], tour)

    def test_two_element_tour(self):

        cells = list()
        for _ in range(2):
            x = random.randint(1, 100)
            y = random.randint(1, 100)
            c = Cell(x, y)
            cells.append(c)

        start = min(cells, key=attrgetter('y', 'x'))
        tour = find_tour(cells, start=start)
        self.assertEqual(3, len(tour))
        self.assertEqual(start, tour[0])

    def test_two_element_tour_default_start(self):
        cells = list()
        for _ in range(2):
            x = random.randint(1, 100)
            y = random.randint(1, 100)
            c = Cell(x, y)
            cells.append(c)

        tour = find_tour(cells)
        self.assertEqual(3, len(tour))
        self.assertEqual(tour[-1:][0], tour[0])




if __name__ == '__main__':
    unittest.main()
