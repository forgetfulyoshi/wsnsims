import itertools

import numpy as np

from wsnsims.flower.data import cell_volume


class FLOWEREnergyModelError(Exception):
    pass


class FLOWEREnergyModel(object):
    def __init__(self, simulation_data, environment):
        """

        :param simulation_data:
        :type simulation_data: flower.flower_sim.FlowerSim
        :param environment:
        :type environment: core.environment.Environment
        """

        self.sim = simulation_data
        self.env = environment

    def cluster_data_volume(self, cluster, intercluster_only=False):
        """

        :param cluster:
        :type cluster: flower.cluster.FLOWERCluster
        :return:
        :rtype: pq.bit
        """

        if not intercluster_only:
            # Handle the intra-cluster data volume
            cell_pairs = itertools.permutations(cluster.cells, 2)
            internal_volume = np.sum(
                [cell_volume(s, d, self.env) for s, d in cell_pairs])
        else:
            internal_volume = 0.  # * pq.bit

        # Handle the inter-cluster data volume
        external_cells = list(set(self.sim.cells) - set(cluster.cells))
        # Outgoing data ...
        cell_pairs = list(itertools.product(cluster.cells, external_cells))

        # Incoming data ...
        cell_pairs += list(itertools.product(external_cells, cluster.cells))
        external_volume = np.sum(
            [cell_volume(s, d, self.env) for s, d in cell_pairs])  # * pq.bit

        total_volume = internal_volume + external_volume
        return total_volume

    def neighbor_clusters(self, cluster):
        """

        :param cluster:
        :type cluster: flower.cluster.FLOWERCluster
        :return:
        :type: list(flower.cluster.FLOWERCluster)
        """

        neighbors = list()
        for other_cluster in self.sim.clusters:
            if other_cluster.anchor == cluster.anchor:
                neighbors.append(other_cluster)

        return neighbors

    def hub_data_volume(self, hub):
        """

        :param hub:
        :type hub: flower.cluster.FLOWERHubCluster
        :return:
        :rtype: pq.bit
        """

        # Only consider intra-hub traffic for cells that belong ONLY to the
        # hub cluster.
        cells = list(hub.cells)
        for cell in hub.cells:
            for cluster in self.sim.clusters:
                if cell in cluster.cells:
                    cells.remove(cell)

        if cells:
            # Handle the intra-hub data volume
            cell_pairs = itertools.permutations(hub.cells, 2)
            volume = np.sum([cell_volume(s, d, self.env)
                             for s, d in cell_pairs])  # * pq.bit
        else:
            volume = 0  # * pq.bit

        cluster_pairs = list()
        # Handle the incoming volume from each cluster
        for cluster in self.sim.clusters:
            # If a cluster shares an anchor with another, then the hub MDC
            # won't need to handle data between those clusters. Therefore, we
            # need to carefully build our set of cluster pairs.

            other_clusters = list(self.sim.clusters)

            # Filter out clusters that share an anchor with this one
            neighbors = self.neighbor_clusters(cluster)
            for neighbor in neighbors:
                other_clusters.remove(neighbor)

            for other_cluster in other_clusters:
                # Cluster -> Other Cluster
                cluster_pairs.append((cluster, other_cluster))

                # Other Cluster -> Cluster
                cluster_pairs.append((other_cluster, cluster))

        for src_cluster, dst_cluster in cluster_pairs:
            src_cells = src_cluster.cells
            dst_cells = dst_cluster.cells

            cell_pairs = itertools.product(src_cells, dst_cells)
            volume += np.sum(
                [cell_volume(s, d, self.env) for s, d in cell_pairs])

        return volume

    def total_comms_energy(self, clust):

        # if cluster_id in self._ids_to_comms_energy:
        #     return self._ids_to_comms_energy[cluster_id]

        if clust == self.sim.hub:
            data_volume = self.hub_data_volume(clust)
        else:
            data_volume = self.cluster_data_volume(clust)

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

    def total_movement_energy(self, cluster):
        """
        Return the amount of energy required to complete a single tour of the
        specified cluster.

        :param cluster: An instance of a FLOWER cluster.

        :return: The amount of energy required.
        :rtype: pq.J
        """

        # if cluster_id in self._ids_to_movement_energy:
        #     return self._ids_to_movement_energy[cluster_id]

        energy = cluster.tour_length * self.env.move_cost
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
