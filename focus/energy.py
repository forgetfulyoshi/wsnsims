import logging

import quantities as pq
import numpy as np
import scipy.sparse.csgraph as sp

import core.environment
import core.data

logger = logging.getLogger(__name__)

class FOCUSEnergyModelError(Exception):
    pass


class FOCUSEnergyModel(object):
    def __init__(self, simulation_data):
        """

        :param clust:
        :type simulation_data: focus.focus_sim.FOCUS
        """

        self.sim = simulation_data
        self.env = core.environment.Environment()

        self._ids_to_clusters = {}
        self._ids_to_movement_energy = {}
        self._ids_to_comms_energy = {}

        self._calculate_cluster_speeds()

    def _calculate_cluster_speeds(self):

        # Generate an empty, N x N sparse graph
        clusters = self.sim.clusters
        node_count = len(clusters)
        dense = np.zeros((node_count, node_count), dtype=float)
        root_cluster = -1
        most_intesections = 0
        for cluster in clusters:
            cluster_index = clusters.index(cluster)
            if len(cluster.intersections) > most_intesections:
                most_intesections = len(cluster.intersections)
                root_cluster = cluster_index

            for child in cluster.intersections:
                child_index = clusters.index(child)
                dense[cluster_index, child_index] = 1

        sparse = sp.csgraph_from_dense(dense)
        nodes, preds = sp.breadth_first_order(sparse, root_cluster,
                                              return_predecessors=True)

        for node in nodes:
            parent_idx = preds[node]
            child_idx = node
            if parent_idx == -9999:
                clusters[child_idx].mdc_speed = self.env.mdc_speed
            else:
                self._set_child_speed(clusters[parent_idx],
                                      clusters[child_idx])

    def _set_child_speed(self, parent, child):
        """

        :param parent:
        :type parent: focus.cluster.FOCUSCluster
        :param child:
        :type child: focus.cluster.FOCUSCluster
        :return:
        """

        parent_time = parent.tour_length / parent.mdc_speed
        child_speed = child.tour_length / parent_time
        child.mdc_speed = child_speed
        logger.debug("Set %s speed to %s", child, child.mdc_speed)

    def _cluster_data_volume(self, cluster_id):
        """

        :param cluster_id:
        :return:
        :rtype: pq.bit
        """

        cluster = self._find_cluster(cluster_id)

        if not cluster.nodes:
            return 0 * pq.bit

        # Handle all intra-cluster data
        cluster_segs = cluster.nodes
        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  cluster_segs if src != dst]
        data_vol = np.sum([core.data.volume(src, dst) for src, dst in
                           intracluster_seg_pairs]) * pq.bit

        # Handle inter-cluster data at the rendezvous point
        all_segments = self.sim.segments
        other_segs = [c for c in all_segments if
                      c.cluster_id != cluster.cluster_id]
        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  other_segs]
        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in
                                   cluster_segs]

        # data volume for inter-cluster traffic
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
        :rtype: focus.cluster.FOCUSCluster
        """
        if cluster_id in self._ids_to_clusters:
            return self._ids_to_clusters[cluster_id]

        found_cluster = None
        for clust in self.sim.clusters:
            if clust.cluster_id == cluster_id:
                found_cluster = clust
                break

        if not found_cluster:
            raise FOCUSEnergyModelError(
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
        energy = current_cluster.tour_length * current_cluster.move_cost
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
