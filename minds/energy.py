import quantities as pq
import numpy as np

import core.environment
import core.data


class MINDSEnergyModelError(Exception):
    pass


class MINDSEnergyModel(object):
    def __init__(self, simulation_data):
        """

        :param clust:
        :type simulation_data: tocs.tocs_sim.ToCS
        """

        self.sim = simulation_data
        self.env = core.environment.Environment()

        self._ids_to_clusters = {}
        self._ids_to_movement_energy = {}
        self._ids_to_comms_energy = {}

    def _cluster_data_volume(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: pq.bit
        """

        current_cluster = self._find_cluster(cluster_id)

        # Handle all intra-cluster volume
        cluster_segs = current_cluster.nodes

        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  cluster_segs if src != dst]

        data_vol = np.sum([core.data.volume(src, dst) for src, dst in
                           intracluster_seg_pairs]) * pq.bit

        # Handle inter-cluster volume at the rendezvous point
        other_segs = list(self.sim.segments)
        for seg in current_cluster.nodes:
            other_segs.remove(seg)

        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  other_segs if src != dst]

        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in
                                   cluster_segs if src != dst]

        # volume volume for inter-cluster traffic
        data_vol += np.sum([core.data.volume(src, dst) for src, dst in
                            intercluster_seg_pairs]) * pq.bit

        return data_vol

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
        :rtype: tocs.cluster.ToCSCluster
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
