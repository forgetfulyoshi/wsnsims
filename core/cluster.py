import itertools
import logging

import numpy as np
import quantities as pq

from core import params, tour, environment, linalg, point
from core.orderedset import OrderedSet


class CoreClusterError(Exception):
    pass


class BaseCluster(object):

    cluster_count = 0

    def __init__(self):

        self.cluster_id = BaseCluster.cluster_count
        BaseCluster.cluster_count += 1

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

    def _invalidate_cache(self):
        self._location = None
        self._tour = None

    @property
    def relay_node(self):
        return self._relay_node

    @relay_node.setter
    def relay_node(self, value):
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
    def tour(self):
        if self._tour:
            return self._tour

        points = [node.location.nd for node in self.nodes]

        # If we have a relay node, make sure to add it to the tour
        if self.relay_node:
            points.append(self.relay_node.location.nd)

        points = np.array(points) * pq.meter
        self._tour = tour.compute_tour(points,
                                       radio_range=self._radio_range)
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
        if node not in self.nodes:
            try:
                node.location.nd.units
            except AttributeError:
                raise CoreClusterError()

            logging.debug("Adding %s to %s", node, self)
            self.nodes.append(node)
            self._invalidate_cache()
        else:
            logging.warning("Re-added %s to %s", node, self)

    def remove(self, node):
        logging.debug("Removing %s from %s", node, self)
        self.nodes.remove(node)
        self._invalidate_cache()

    def motion_energy(self):
        cost = params.MOVEMENT_COST * self.tour_length
        return cost

    def data_volume_bits(self, all_clusters, all_nodes):
        # Volume in megabits
        data_volume = self.data_volume_mbits(all_clusters, all_nodes)

        # Volume in bits
        data_volume *= 1024 * 1024
        return data_volume

    def data_volume_mbits(self, all_clusters, all_nodes):
        raise NotImplementedError()

    def communication_energy(self, all_clusters, all_nodes):
        # Volume in bits
        data_volume = self.data_volume_bits(all_clusters, all_nodes)

        e_c = data_volume * (
            params.ALPHA + params.BETA * pow(params.COMMUNICATION_RANGE,
                                             params.DELTA))
        # e_c = data_volume * 2.0 * pow(10, -6)

        return e_c

    def total_energy(self, all_clusters, all_nodes):
        total = self.motion_energy() + self.communication_energy(all_clusters,
                                                                 all_nodes)
        return total

    def merge(self, other):
        new_cluster = type(self)()
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
        node.cluster = new_cluster

    new_clusters.remove(c_i)
    new_clusters.remove(c_j)
    new_clusters.append(new_cluster)
    return new_clusters


def closest_nodes(cluster_1, cluster_2, cell_distance=True):
    if isinstance(cluster_1, BaseCluster):
        node_list_1 = cluster_1.nodes
    else:
        node_list_1 = cluster_1

    if isinstance(cluster_2, BaseCluster):
        node_list_2 = cluster_2.nodes
    else:
        node_list_2 = cluster_2

    pairs = itertools.product(node_list_1, node_list_2)

    if cell_distance:
        decorated = [(cell_1.cell_distance(cell_2), i, cell_1, cell_2) for
                     i, (cell_1, cell_2) in enumerate(pairs)]
    else:
        decorated = [(cell_1.distance(cell_2), i, cell_1, cell_2) for
                     i, (cell_1, cell_2) in enumerate(pairs)]

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
