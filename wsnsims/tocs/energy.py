import itertools

import numpy as np

from wsnsims.core.data import segment_volume


class ToCSEnergyModelError(Exception):
    pass


class ToCSEnergyModel(object):
    def __init__(self, simulation_data, environment):
        """

        :param simulation_data:
        :type simulation_data: tocs.tocs_sim.TOCS
        :param environment:
        :type environment: core.environment.Environment
        """

        self.sim = simulation_data
        self.env = environment

        self._ids_to_clusters = {}
        self._ids_to_movement_energy = {}
        self._ids_to_comms_energy = {}

    def cluster_data_volume(self, cluster_id, intercluster_only=False):
        """

        :param cluster_id:
        :param intercluster_only:
        :return:
        :rtype: pq.bit
        """

        cluster = self._find_cluster(cluster_id)

        if not intercluster_only:
            # Handle the intra-cluster data volume
            segment_pairs = itertools.permutations(cluster.segments, 2)
            internal_volume = np.sum(
                [segment_volume(s, d, self.env) for s, d in segment_pairs])
        else:
            internal_volume = 0

        # Handle the inter-cluster data volume

        external_segments = list(
            set(self.sim.segments) - set(cluster.segments))
        # Outgoing data ...
        segment_pairs = list(
            itertools.product(cluster.segments, external_segments))

        # Incoming data ...
        segment_pairs += list(
            itertools.product(external_segments, cluster.segments))
        external_volume = np.sum(
            [segment_volume(s, d, self.env) for s, d in segment_pairs])

        total_volume = internal_volume + external_volume
        return total_volume

    def centroid_data_volume(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: pq.bit
        """

        centroid = self._find_cluster(cluster_id)

        # Handle the intra-centroid data volume
        segment_pairs = itertools.permutations(centroid.segments, 2)
        volume = np.sum(
            [segment_volume(s, d, self.env) for s, d in segment_pairs])

        cluster_pairs = list()
        # Handle the incoming volume from each cluster
        for cluster in self.sim.clusters:

            other_clusters = list(self.sim.clusters)
            for other_cluster in other_clusters:
                # Cluster -> Other Cluster
                cluster_pairs.append((cluster, other_cluster))

                # Other Cluster -> Cluster
                cluster_pairs.append((other_cluster, cluster))

        for src_cluster, dst_cluster in cluster_pairs:
            src_segments = src_cluster.segments
            dst_segments = dst_cluster.segments

            segment_pairs = itertools.product(src_segments, dst_segments)
            volume += np.sum(
                [segment_volume(s, d, self.env) for s, d in segment_pairs])

        return volume

    def total_comms_energy(self, cluster_id):

        if cluster_id in self._ids_to_comms_energy:
            return self._ids_to_comms_energy[cluster_id]

        if cluster_id == self.sim.centroid.cluster_id:
            data_volume = self.centroid_data_volume(cluster_id)
        else:
            data_volume = self.cluster_data_volume(cluster_id)

        energy = data_volume * self.env.comms_cost
        self._ids_to_comms_energy[cluster_id] = energy

        return energy

    def _find_cluster(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: tocs.cluster.ToCSCluster
        """
        if cluster_id in self._ids_to_clusters:
            return self._ids_to_clusters[cluster_id]

        found_cluster = None
        for clust in self.sim.clusters + [self.sim.centroid]:
            if clust.cluster_id == cluster_id:
                found_cluster = clust
                break

        if not found_cluster:
            raise ToCSEnergyModelError(
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
