import unittest

import quantities as pq

from core import environment


class EnvironmentTests(unittest.TestCase):
    def test_comms_cost(self):
        env = environment.Environment()

        env.comms_range = 100 * pq.m
        cost_100m = env.comms_cost

        env.comms_range = 100 * pq.kilometer
        cost_100km = env.comms_cost

        self.assertEqual(cost_100m.units, pq.J / pq.bit)
        self.assertEqual(cost_100km.units, pq.J / pq.bit)
        # self.assertGreater(cost_100km, cost_100m)

    def test_movement_cost(self):
        env = environment.Environment()

        distance = 5. * pq.m
        cost_5m = distance * env.move_cost

        self.assertEqual(cost_5m.units, pq.J)
        self.assertEqual(5. * pq.J, cost_5m)


