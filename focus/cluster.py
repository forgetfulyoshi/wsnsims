import quantities as pq

from core.cluster import BaseCluster


class FOCUSCluster(BaseCluster):
    def __init__(self):
        super(FOCUSCluster, self).__init__()
        self.intersections = list()
        self.mdc_speed = 0. * (pq.meter / pq.second)
        self.move_cost = 0. * (pq.J / pq.meter)