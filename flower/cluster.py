import logging

from flower import constants
from flower import tour
from flower.grid import WorldPositionMixin


class ClusterError(Exception):
    pass


class ClusterMixin(WorldPositionMixin):
    def __init__(self):
        WorldPositionMixin.__init__(self)

        self._cells = list()
        self._tour = list()
        self._tour_length = 0

    def calculate_tour(self):
        self._tour = tour.find_tour(list(self.cells), radius=0)
        self._tour_length = tour.tour_length(self._tour)

    def update_location(self):
        com = tour.centroid(self._cells)
        self.x = com.x
        self.y = com.y

    @property
    def tour_length(self):
        return self._tour_length

    @property
    def cells(self):
        return self._cells

    @cells.setter
    def cells(self, value):
        self._cells = value
        self.update_location()

    def append(self, *args):
        self._cells.append(args)
        self.update_location()

    def add(self, cell):
        if cell not in self._cells:
            logging.debug("Adding %s to %s", cell, self)
            self._cells.append(cell)
            self.update_location()
        else:
            logging.warning("Invalid attempt to re-add %s to %s", cell, self)
            raise ClusterError()

    def remove(self, cell):
        if cell not in self._cells:
            logging.warning("Invalid attempt to remove %s from %s %s", cell, self, self._cells)
            raise ClusterError()
        else:
            logging.debug("Removing %s from %s", cell, self)
            self._cells.remove(cell)
            self.update_location()

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
    def __init__(self):
        ClusterMixin.__init__(self)

        self.cluster_id = constants.NOT_CLUSTERED
        self.completed = False
        self.anchor = None
        self.central_cluster = None
        self._recent = None

    def __str__(self):
        return "Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "C{}".format(self.cluster_id)

    @property
    def recent(self):
        return self._recent

    @recent.setter
    def recent(self, value):
        logging.debug("Setting RC(%r) to %r", self, value)
        self._recent = value

        if value not in self.cells:
            logging.warning("%r is not a member of %r", value, self)

    def update_anchor(self):

        candidates = list()
        for cell in self.cells:
            closest = min(self.central_cluster.cells, key=lambda x: x.distance(cell))
            distance = closest.distance(cell)
            candidates.append((distance, closest))

        _, anchor = min(candidates, key=lambda x: x[0])

        self.anchor = anchor


class VirtualCluster(ClusterMixin):
    def __init__(self):
        ClusterMixin.__init__(self)

        self.virtual_cluster_id = constants.NOT_CLUSTERED

    # def __str__(self):
    #     return "Virtual Cluster {}".format(self.virtual_cluster_id)
    #
    # def __repr__(self):
    #     return "VC{}".format(self.virtual_cluster_id)

    def __add__(self, other):
        new_vc = VirtualCluster()
        new_vc.cells = list(set(self.cells + other.cells))
        new_vc.update_location()
        return new_vc
