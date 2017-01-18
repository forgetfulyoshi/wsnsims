import itertools
import collections

import numpy as np
import quantities as pq

import core.data
import core.environment


class FLOWEREnergyModelError(Exception):
    pass


class FLOWEREnergyModel(object):
    def __init__(self, simulation_data):
        """

        :param simulation_data:
        :type simulation_data: flower.flower_sim.FlowerSim
        """

        self.sim = simulation_data
        self.env = core.environment.Environment()

    def _cluster_data_volume(self, clust):
        """

        :param cluster_id:
        :return:
        :rtype: pq.bit
        """

        if not clust.cells:
            return 0 * pq.bit

        all_cells = self.sim.cells

        # Handle all intra-cluster data
        cluster_cells = clust.cells
        cluster_segs = [seg for segs in [c.segments for c in cluster_cells] for seg in segs]
        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in cluster_segs if src != dst]
        data_vol = np.sum([core.data.volume(src, dst) for src, dst in intracluster_seg_pairs]) * pq.bit

        # Handle inter-cluster data at the anchor
        other_cells = [c for c in all_cells if c.cluster_id != clust.cluster_id]
        other_segs = [seg for segs in [c.segments for c in other_cells] for seg in segs]
        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in other_segs]
        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in cluster_segs]

        # data volume for inter-cluster traffic
        data_vol += np.sum([core.data.volume(src, dst) for src, dst in intercluster_seg_pairs]) * pq.bit

        return data_vol

        # current_cluster = clust
        #
        # intracluster_pairs = itertools.permutations(current_cluster.cells, 2)
        # data_vol = np.sum([core.data.volume(src, dst) for src, dst in
        #                    intracluster_pairs]) * pq.bit
        #
        # other_cells = list(set(self.sim.cells) - set(current_cluster.cells))
        # itercluster_pairs = [(src, dst) for src in current_cluster.cells
        #                      for dst in other_cells]
        #
        # itercluster_pairs += [(src, dst) for src in other_cells
        #                       for dst in current_cluster.cells]
        #
        # # volume for inter-cluster traffic
        # data_vol += np.sum([core.data.volume(src, dst) for src, dst in
        #                     itercluster_pairs]) * pq.bit
        #
        # return data_vol

    def _hub_data_volume(self, clust):
        """

        :param cluster_id:
        :return:
        :rtype: pq.bit
        """

        if not clust.cells:
            return 0 * pq.bit

        # Handle all intra-cluster data for the hub
        all_cells = self.sim.cells
        hub_cells = [c for c in all_cells if c.cluster_id == clust.cluster_id]
        hub_segs = [seg for segs in [c.segments for c in hub_cells] for seg in segs]
        hub_seg_pairs = [(src, dst) for src in hub_segs for dst in hub_segs if src != dst]
        data_vol = np.sum([core.data.volume(src, dst) for src, dst in hub_seg_pairs]) * pq.bit

        # Handle inter-cluster data for other clusters
        all_clusters = self.sim.clusters + [self.sim.hub]
        anchor_cells = [a for a in [c.anchor for c in all_clusters if c.cluster_id != clust.cluster_id]]
        anchor_cells = list(set(anchor_cells))

        for cell in anchor_cells:
            # Get the segments served by this anchor
            local_clusters = [c for c in all_clusters if c.anchor == cell]
            local_cells = [c for c in all_cells if c.cluster_id in [clust.cluster_id for clust in local_clusters]]
            local_segs = [seg for segs in [c.segments for c in local_cells] for seg in segs]

            # Get the segments not served by this anchor
            remote_clusters = [c for c in all_clusters if c.anchor != cell and c != self]
            remote_cells = [c for c in all_cells if c.cluster_id in [clust.cluster_id for clust in remote_clusters]]
            remote_segs = [seg for segs in [c.segments for c in remote_cells] for seg in segs]

            # Generate the pairs of local-to-remote segments
            seg_pairs = [(seg_1, seg_2) for seg_1 in local_segs for seg_2 in remote_segs]

            # Generate the pairs of remote-to-local segments
            seg_pairs += [(seg_1, seg_2) for seg_1 in remote_segs for seg_2 in local_segs]

            # Add the inter-cluster data volume
            data_vol += np.sum([core.data.volume(src, dst) for src, dst in seg_pairs]) * pq.bit

        # Handle inter-cluster data for the hub itself
        # This is done by the above loop

        return data_vol

        # current_cluster = clust
        #
        # # Handle all intra-cluster volume for the hub
        # if current_cluster.cells:
        #     hub_cells = current_cluster.cells
        #     hub_cell_pairs = [(src, dst) for src in hub_cells for dst in
        #                       hub_cells if src != dst]
        #     data_vol = np.sum([core.data.volume(src, dst) for src, dst in
        #                        hub_cell_pairs]) * pq.bit
        # else:
        #     data_vol = 0. * pq.bit
        #
        # # Handle inter-cluster volume for other clusters
        # for cluster in self.sim.clusters:
        #     local_cells = cluster.cells
        #     remote_cells = [cell for cell in self.sim.cells if
        #                     cell not in cluster.cells]
        #
        #     # Generate the pairs of local-to-remote segments
        #     cell_pairs = [(src, dst) for src in local_cells for dst in
        #                   remote_cells]
        #
        #     # Generate the pairs of remote-to-local segments
        #     cell_pairs += [(src, dst) for src in remote_cells for dst in
        #                    local_cells]
        #
        #     # Add the inter-cluster volume volume
        #     data_vol += np.sum([core.data.volume(src, dst) for src, dst in
        #                         cell_pairs]) * pq.bit
        #
        # # Handle inter-cluster volume for the hub itself
        # # This is done by the above loop
        #
        # return data_vol

    def total_comms_energy(self, clust):

        # if cluster_id in self._ids_to_comms_energy:
        #     return self._ids_to_comms_energy[cluster_id]

        if clust == self.sim.hub:
            data_volume = self._hub_data_volume(clust)
        else:
            data_volume = self._cluster_data_volume(clust)

        energy = data_volume * self.env.comms_cost
        # self._ids_to_comms_energy[cluster_id] = energy

        return energy

    def _find_cluster(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: flower.cluster.FlowerCluster
        """

        all_clusters = self.sim.clusters + [self.sim.hub]

        found_cluster = None
        for clust in all_clusters:
            if clust.cluster_id == cluster_id:
                found_cluster = clust
                break

        if not found_cluster:
            raise FLOWEREnergyModelError(
                "Could not find cluster {}".format(cluster_id))

        return found_cluster

    def total_movement_energy(self, clust):
        """
        Return the amount of energy required to complete a single tour of the
        specified cluster.

        :param clust: An instance of a FLOWER cluster.

        :return: The amount of energy required.
        :rtype: pq.J
        """

        # if cluster_id in self._ids_to_movement_energy:
        #     return self._ids_to_movement_energy[cluster_id]

        energy = clust.tour_length * self.env.move_cost
        # self._ids_to_movement_energy[cluster_id] = energy
        return energy

    def total_energy(self, cluster_id):
        """
        Get the sum of communication and movement energy for the given cluster.

        :param cluster_id:
        :return:
        :rtype: pq.J
        """
        clust = self._find_cluster(cluster_id)
        energy = self.total_comms_energy(clust)
        energy += self.total_movement_energy(clust)
        return energy
