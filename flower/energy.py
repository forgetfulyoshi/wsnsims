import numpy as np
import quantities as pq

import core.data
import core.environment


class FlowerEnergyModelError(Exception):
    pass


class FlowerEnergyModel(object):
    def __init__(self, simulation_data):
        """

        :param simulation_data:
        :type simulation_data: flower.flower_sim.Flower
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
        cluster_segs = current_cluster.segments

        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  cluster_segs if src != dst]

        data_vol = np.sum([core.data.volume(src, dst) for src, dst in
                           intracluster_seg_pairs]) * pq.bit

        # Handle inter-cluster volume at the rendezvous point
        other_segs = [c for c in self.sim.segments if
                      c.cluster_id != cluster_id]
        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  other_segs]
        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in
                                   cluster_segs]

        # volume volume for inter-cluster traffic
        data_vol += np.sum([core.data.volume(src, dst) for src, dst in
                            intercluster_seg_pairs]) * pq.bit

        return data_vol

    def _hub_data_volume(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: pq.bit
        """

        current_cluster = self._find_cluster(cluster_id)

        # Handle all intra-cluster volume for the hub
        if current_cluster.segments:
            hub_segs = current_cluster.segments
            hub_seg_pairs = [(src, dst) for src in hub_segs for dst in
                             hub_segs if src != dst]
            data_vol = np.sum([core.data.volume(src, dst) for src, dst in
                               hub_seg_pairs]) * pq.bit
        else:
            data_vol = 0. * pq.bit

        # Handle inter-cluster volume for other clusters
        for clust in self.sim.clusters:
            if clust.cluster_id == cluster_id:
                continue

            local_segs = clust.segments
            remote_segs = [seg for seg in self.sim.segments if
                           seg.cluster_id != cluster_id]

            # Generate the pairs of local-to-remote segments
            seg_pairs = [(seg_1, seg_2) for seg_1 in local_segs for seg_2 in
                         remote_segs]

            # Generate the pairs of remote-to-local segments
            seg_pairs += [(seg_1, seg_2) for seg_1 in remote_segs for seg_2 in
                          local_segs]

            # Add the inter-cluster volume volume
            data_vol += np.sum([core.data.volume(src, dst) for src, dst in
                                seg_pairs]) * pq.bit

        # Handle inter-cluster volume for the hub itself
        # This is done by the above loop

        return data_vol

    def total_comms_energy(self, cluster_id):

        # if cluster_id in self._ids_to_comms_energy:
        #     return self._ids_to_comms_energy[cluster_id]

        if cluster_id == self.sim.hub.cluster_id:
            data_volume = self._hub_data_volume(cluster_id)

        elif cluster_id == self.sim.virtual_hub.cluster_id:
            data_volume = self._hub_data_volume(cluster_id)

        else:
            data_volume = self._cluster_data_volume(cluster_id)

        energy = data_volume * self.env.comms_cost
        # self._ids_to_comms_energy[cluster_id] = energy

        return energy

    def _find_cluster(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: flower.cluster.FlowerCluster
        """
        # if cluster_id in self._ids_to_clusters:
        #     return self._ids_to_clusters[cluster_id]

        all_clusters = self.sim.clusters + self.sim.virtual_clusters
        all_clusters.append(self.sim.hub)
        all_clusters.append(self.sim.virtual_hub)

        found_cluster = None
        for clust in all_clusters:
            if clust.cluster_id == cluster_id:
                found_cluster = clust
                break

        if not found_cluster:
            raise FlowerEnergyModelError(
                "Could not find cluster {}".format(cluster_id))

        # self._ids_to_clusters[cluster_id] = found_cluster
        return found_cluster

    def total_movement_energy(self, cluster_id):
        """
        Return the amount of energy required to complete a single tour of the
        specified cluster.

        :param cluster_id: The numeric identifier of the cluster.

        :return: The amount of energy required.
        :rtype: pq.J
        """

        # if cluster_id in self._ids_to_movement_energy:
        #     return self._ids_to_movement_energy[cluster_id]

        current_cluster = self._find_cluster(cluster_id)
        energy = current_cluster.tour_length * self.env.move_cost
        # self._ids_to_movement_energy[cluster_id] = energy
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

    def total_sim_movement_energy(self, virtual=False):
        """

        :param virtual:
        :return:
        :rtype: pq.J
        """

        total_energy = 0. * pq.J
        if virtual:
            for clust in self.sim.virtual_clusters + [self.sim.virtual_hub]:
                total_energy += self.total_movement_energy(clust.cluster_id)
        else:
            for clust in self.sim.clusters + [self.sim.hub]:
                total_energy += self.total_movement_energy(clust.cluster_id)

        return total_energy

    def total_sim_comms_energy(self, virtual=False):
        """

        :param virtual:
        :return:
        :rtype: pq.J
        """

        total_energy = 0. * pq.J
        if virtual:
            for clust in self.sim.virtual_clusters + [self.sim.virtual_hub]:
                total_energy += self.total_comms_energy(clust.cluster_id)
        else:
            for clust in self.sim.clusters + [self.sim.hub]:
                total_energy += self.total_comms_energy(clust.cluster_id)

        return total_energy
