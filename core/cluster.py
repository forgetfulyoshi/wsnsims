import itertools
import logging

import numpy as np
import quantities as pq

from core import params, tour, environment, linalg, point
from core.orderedset import OrderedSet


class CoreClusterError(Exception):
    pass


class BaseCluster(object):
    count = 0

    def __init__(self):

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
        self.env = environment.Environment()

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
        logging.debug("Setting %s RN to %s", self, value)
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

        location = linalg.centroid(np.array(points)) * pq.meter
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

        points = np.array(points) * pq.meter
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
            logging.debug("Adding %s to %s", node, self)
            node.cluster_id = self.cluster_id
            self.nodes.append(node)
            self._invalidate_cache()
        else:
            logging.warning("Re-added %s to %s", node, self)

    def remove(self, node):
        logging.debug("Removing %s from %s", node, self)
        self.nodes.remove(node)
        node.cluster_id = -1
        self._invalidate_cache()

    def merge(self, other, *args, **kwargs):
        new_cluster = type(self)(*args, **kwargs)
        new_cluster.nodes = list(OrderedSet(self.nodes + other.nodes))
        return new_cluster


def combine_clusters(clusters, centroid):
    index = 0
    decorated = list()

    cluster_pairs = itertools.combinations(clusters, 2)
    for c_i, c_j in cluster_pairs:
        tc_1 = c_i.merge(c_j).merge(centroid)
        tc_2 = c_i.merge(centroid)

        combination_cost = tc_1.tour_length - tc_2.tour_length
        decorated.append((combination_cost, index, c_i, c_j))
        index += 1

    cost, _, c_i, c_j = min(decorated)
    logging.info("Combining %s and %s (Cost: %f)", c_i, c_j, cost)

    new_clusters = list(clusters)
    new_cluster = c_i.merge(c_j)

    for node in new_cluster.nodes:
        node.cluster_id = new_cluster.cluster_id

    new_clusters.remove(c_i)
    new_clusters.remove(c_j)
    new_clusters.append(new_cluster)
    return new_clusters


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


def closest_points(points_1, points_2):
    pairs = itertools.product(points_1, points_2)
    decorated = [(point_1.distance(point_2), i, point_1, point_2) for
                 i, (point_1, point_2) in enumerate(pairs)]
    closest = min(decorated)
    points = closest[2], closest[3]
    return points


class RelayNode(object):
    def __init__(self, position):
        self.location = point.Vec2(position)
        self.cluster_id = -1

    def __str__(self):
        return "RelayNode {}".format(self.location)

    def __repr__(self):
        return "RN{}".format(self.location)
