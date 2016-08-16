import constants
import tour
from grid import WorldPositionMixin


class ClusterMixin(object):
    def __init__(self, central_cell):
        self._cells = list()
        self._tour = list()
        self._tour_length = 0
        self._central_cell = central_cell

    def _calculate_tour(self):
        cells = list(set(self._cells + [self._central_cell]))
        self._tour = tour.find_tour(cells, radius=0, start=self._central_cell)
        self._tour_length = tour.tour_length(self._tour)

    def _calculate_location(self):
        com = tour.centroid(self._cells + [self._central_cell])
        self.x = com.x
        self.y = com.y

    def update(self):
        self._calculate_tour()
        self._calculate_location()

    @property
    def tour_length(self):
        return self._tour_length

    @property
    def cells(self):
        return self._cells

    @cells.setter
    def cells(self, value):
        self._cells = value
        self.update()

    def append(self, *args):
        self._cells.append(args)
        self.update()

    def tour(self):
        return [c.collection_point for c in self._tour]


class Cluster(ClusterMixin):
    def __init__(self, central_cell):
        ClusterMixin.__init__(self, central_cell)

        self.cluster_id = constants.NOT_CLUSTERED


class VirtualCluster(WorldPositionMixin, ClusterMixin):
    def __init__(self, central_cell):
        WorldPositionMixin.__init__(self)
        ClusterMixin.__init__(self, central_cell)

        self.virtual_cluster_id = constants.NOT_CLUSTERED

    def __add__(self, other):
        new_vc = VirtualCluster(self._central_cell)
        new_vc.cells = list(set(self.cells + other.cells))
        return new_vc
