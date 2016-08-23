from flower import constants
from flower import tour
from flower.grid import WorldPositionMixin


class ClusterMixin(object):
    def __init__(self, central_cell):
        self._cells = list()
        self._tour = list()
        self._tour_length = 0
        self._central_cell = central_cell
        self._recent = None

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

    def add(self, cell):
        self.cells = list(set(self.cells + [cell]))
        self._recent = cell

    def remove(self, cell):
        self.cells.remove(cell)

    def tour(self):
        return [c.collection_point for c in self._tour]

    def motion_energy(self):
        cost = constants.MOVEMENT_COST * self.tour_length
        return cost

    def communication_energy(self):

        data_volume = 0
        for cell in self.cells:
            for s in cell.segments:
                data_volume += s.total_data_volume()

        pcr = constants.ALPHA + constants.BETA * pow(constants.COMMUNICATION_RANGE, constants.DELTA)
        energy = data_volume * pcr
        return energy

    def total_energy(self):
        total = self.motion_energy() + self.communication_energy()
        return total


class Cluster(ClusterMixin):
    def __init__(self, central_cell):
        ClusterMixin.__init__(self, central_cell)

        self.cluster_id = constants.NOT_CLUSTERED
        self.completed = False
        self.anchor = central_cell

    def update(self):
        super(Cluster, self).update()
        for c in self._cells:
            c.cluster_id = self.cluster_id

    def recent(self):
        if self._recent:
            return self._recent

        recent_cell = self.cells[-1:][0]
        return recent_cell

    def update_anchor(self, central_cluster):
        candidates = list()
        for cell in self.cells:
            closest = min(central_cluster.cells, key=lambda x: x.distance(cell))
            distance = closest.distance(cell)
            candidates.append((distance, closest))

        _, anchor = min(candidates, key=lambda x: x[0])
        self.anchor = anchor
        self._central_cell = anchor

        self.update()


class VirtualCluster(WorldPositionMixin, ClusterMixin):
    def __init__(self, central_cell):
        WorldPositionMixin.__init__(self)
        ClusterMixin.__init__(self, central_cell)

        self.virtual_cluster_id = constants.NOT_CLUSTERED

    def update(self):
        super(VirtualCluster, self).update()
        for c in self._cells:
            c.virtual_cluster_id = self.virtual_cluster_id

    def __add__(self, other):
        new_vc = VirtualCluster(self._central_cell)
        new_vc.cells = list(set(self.cells + other.cells))
        return new_vc
