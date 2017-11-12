import itertools
import logging

import numpy as np

from wsnsims.core import tour, point
from ordered_set import OrderedSet

from wsnsims.core import linalg

logger = logging.getLogger(__name__)


class BaseCluster(object):
    count = 0

    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """

        self._cluster_id = BaseCluster.count
        BaseCluster.count += 1

        #: List of elements contained in the cluster. These are typically
        #: segments. The only requirement is that the objects have a "location"
        #: attribute that is a Vec2.
        self._nodes = list()

        #: Cached value of the location of this cluster. This must be set to
        #: None when a node is added or removed.
        self._location = None

        #: Cached value of the tour over this cluster's nodes. This must be
        #: set to None when a node is added or removed.
        self._tour = None

        #: The current simulation environment
        self.env = environment

        #: The assigned cluster RN, if it exists.
        self._relay_node = None

        #: Easily allow subclasses to override the radio range. This is
        #: intended to be used by centroid clusters where the radio range needs
        #: to be set to zero (we want the MDC to actually travel to the relay
        #: points).
        self._radio_range = self.env.comms_range

    def _invalidate_cache(self) -> None:
        self._location = None
        self._tour = None

    def __str__(self):
        return "Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "BC {}".format(self.cluster_id)

    @property
    def cluster_id(self):
        return self._cluster_id

    @cluster_id.setter
    def cluster_id(self, value):
        self._cluster_id = value

    @property
    def relay_node(self):
        return self._relay_node

    @relay_node.setter
    def relay_node(self, value):
        logger.debug("Setting %s RN to %s", self, value)
        self._relay_node = value
        self._invalidate_cache()

    @property
    def location(self):
        if self._location:
            return self._location

        points = [node.location.nd for node in self.nodes]

        # If we have a relay node, make sure to include it in the centroid
        # calculation.
        if self.relay_node:
            points.append(self.relay_node.location.nd)

        location = linalg.centroid(np.array(points))
        self._location = point.Vec2(location)
        return self._location

    @property
    def tour(self) -> tour.Tour:
        if self._tour:
            return self._tour

        points = [node.location.nd for node in self.nodes]

        # If we have a relay node, make sure to add it to the tour
        if self.relay_node:
            points.append(self.relay_node.location.nd)

        points = np.array(points)
        self._tour = tour.compute_tour(points,
                                       radio_range=self._radio_range)

        self._tour.objects = list(self.nodes)
        if self.relay_node:
            self._tour.objects.append(self.relay_node)

        return self._tour

    @property
    def tour_length(self):
        return self.tour.length

    @property
    def nodes(self):
        return self._nodes

    @nodes.setter
    def nodes(self, value):
        self._nodes = value

    def add(self, node):
        """

        :param node:
        :type node: core.segment.Segment
        :return:
        """
        if node not in self.nodes:
            logger.debug("Adding %s to %s", node, self)
            node.cluster_id = self.cluster_id
            self.nodes.append(node)
            self._invalidate_cache()
        else:
            logger.debug("Re-added %s to %s", node, self)
            node.cluster_id = self.cluster_id
            self._invalidate_cache()

    def remove(self, node):
        logger.debug("Removing %s from %s", node, self)
        self.nodes.remove(node)
        node.cluster_id = -1
        self._invalidate_cache()

    def merge(self, other):
        new_cluster = type(self)(self.env)
        new_cluster.nodes = list(OrderedSet(self.nodes + other.nodes))
        return new_cluster


def closest_nodes(cluster_1, cluster_2, dist=None):
    if isinstance(cluster_1, BaseCluster):
        node_list_1 = cluster_1.nodes
    else:
        node_list_1 = cluster_1

    if isinstance(cluster_2, BaseCluster):
        node_list_2 = cluster_2.nodes
    else:
        node_list_2 = cluster_2

    pairs = itertools.product(node_list_1, node_list_2)

    if dist:
        decorated = [(dist(cell_1, cell_2), i, cell_1, cell_2) for
                     i, (cell_1, cell_2) in enumerate(pairs)]
    else:
        decorated = [(np.linalg.norm(cell_1.location.nd - cell_2.location.nd),
                      i, cell_1, cell_2)
                     for i, (cell_1, cell_2) in enumerate(pairs)]

    closest = min(decorated)
    cells = closest[2], closest[3]
    return cells
