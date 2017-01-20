import collections

import itertools
import quantities as pq
import numpy as np
import scipy.sparse.csgraph as sp

import core.environment
import core.data


class MINDSEnergyModelError(Exception):
    pass


class MINDSEnergyModel(object):
    def __init__(self, simulation_data):
        """

        :param clust:
        :type simulation_data: tocs.tocs_sim.TOCS
        """

        self.sim = simulation_data
        self.env = core.environment.Environment()
        self.cluster_graph = self.build_cluster_graph()

        self._ids_to_clusters = {}
        self._ids_to_movement_energy = {}
        self._ids_to_comms_energy = {}

    def build_cluster_graph(self):

        cluster_graph = collections.defaultdict(list)
        for cluster in self.sim.clusters:

            other_clusters = list(self.sim.clusters)
            other_clusters.remove(cluster)
            for other_cluster in other_clusters:
                if other_cluster.relay_node == cluster.relay_node:
                    cluster_graph[cluster].append(other_cluster)

        node_count = len(self.sim.clusters)
        dense = np.zeros((node_count, node_count), dtype=float)

        for cluster, neighbors in cluster_graph.items():

            cluster_index = self.sim.clusters.index(cluster)
            for neighbor in neighbors:
                neighbor_index = self.sim.clusters.index(neighbor)

                dense[cluster_index, neighbor_index] = 1
                dense[neighbor_index, cluster_index] = 1

        sparse = sp.csgraph_from_dense(dense)
        return sparse

    def sum_cluster_volume(self, parent, cluster):

        children = list()
        for other_cluster in self.sim.clusters:
            if other_cluster == parent:
                continue

            if other_cluster.relay_node == cluster.relay_node:
                children.append(other_cluster)

        child_pairs = list()
        for child in children:
            child_pairs.append(self.sum_cluster_volume(cluster, child))

        # All inter-cluster pairs for this cluster
        other_segments = list(set(self.sim.segments) - set(cluster.nodes))
        segment_pairs = list(itertools.permutations(other_))



    def _cluster_data_volume(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: pq.bit
        """

        cluster = self._find_cluster(cluster_id)
        cluster_index = self.sim.clusters.index(cluster)
        cluster_tree, preds = sp.breadth_first_order(self.cluster_graph,
                                                     cluster_index,
                                                     directed=False,
                                                     return_predecessors=True)



    def total_comms_energy(self, cluster_id):

        if cluster_id in self._ids_to_comms_energy:
            return self._ids_to_comms_energy[cluster_id]

        data_volume = self._cluster_data_volume(cluster_id)
        energy = data_volume * self.env.comms_cost
        self._ids_to_comms_energy[cluster_id] = energy

        return energy

    def _find_cluster(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: core.cluster.BaseCluster
        """
        if cluster_id in self._ids_to_clusters:
            return self._ids_to_clusters[cluster_id]

        found_cluster = None
        for clust in self.sim.clusters:
            if clust.cluster_id == cluster_id:
                found_cluster = clust
                break

        if not found_cluster:
            raise MINDSEnergyModelError(
                "Could not find cluster {}".format(cluster_id))

        self._ids_to_clusters[cluster_id] = found_cluster
        return found_cluster

    def total_movement_energy(self, cluster_id):
        """
        Return the amount of energy required to complete a single tour of the
        specified cluster.

        :param cluster_id: The numeric identifier of the cluster.

        :return: The amount of energy required.
        :rtype: pq.J
        """

        if cluster_id in self._ids_to_movement_energy:
            return self._ids_to_movement_energy[cluster_id]

        current_cluster = self._find_cluster(cluster_id)
        energy = current_cluster.tour_length * self.env.move_cost
        self._ids_to_movement_energy[cluster_id] = energy
        return energy

    def total_energy(self, cluster_id):
        """
        Get the sum of communication and movement energy for the given cluster.

        :param cluster_id:
        :return:
        :rtype: pq.J
        """

        energy = self.total_comms_energy(cluster_id)
        energy += self.total_movement_energy(cluster_id)
        return energy
