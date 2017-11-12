import logging

import numpy as np

import ordered_set as orderedset
from wsnsims.focus.energy import FOCUSEnergyModel
from wsnsims.focus.movement import FOCUSMovementModel

from wsnsims.core import data

logger = logging.getLogger(__name__)


class FOCUSRunner(object):
    def __init__(self, sim, environment):
        """

        :param sim: The simulation after a run of MINDS
        :type sim: focus.focus_sim.FOCUS
        :param environment:
        :type environment: core.environment.Environment
        """

        #: The simulation segment_volume
        self.sim = sim

        self.env = environment
        self.movement_model = FOCUSMovementModel(self.sim, self.env)
        self.energy_model = FOCUSEnergyModel(self.sim, self.env)

    def print_all_distances(self):
        """
        For debugging, iterate over all segments and print the tour distances
        between them.

        :return: None
        """
        seg_pairs = [(begin, end) for begin in self.sim.segments
                     for end in self.sim.segments if begin != end]

        for begin, end in seg_pairs:
            msg = "{} to {} is {}".format(
                begin, end, self.movement_model.shortest_distance(begin, end))

            logger.debug(msg)

        self.sim.show_state()

    def maximum_communication_delay(self):
        """
        Compute the average communication delay across all segments.

        :return: The delay time in seconds
        :rtype: pq.quantity.Quantity
        """

        segment_pairs = ((src, dst) for src in self.sim.segments for dst in
                         self.sim.segments if src != dst)

        delays = []
        for src, dst in segment_pairs:
            delay = self.communication_delay(src, dst)
            delays.append(delay)

        delays = np.array(delays)
        max_delay = np.max(delays)
        # max_delay *= pq.second

        return max_delay

    def segment_clusters(self, segment):
        """

        :param segment:
        :type segment: core.segment.Segment
        :return:
        :rtype: list(core.cluster.BaseCluster)
        """
        clusters = list()
        for cluster in self.sim.clusters:
            if segment in cluster.tour.objects:
                clusters.append(cluster)

        return clusters

    def count_clusters(self, path):
        """

        :param path:
        :type path: list(core.segment.Segment)
        :return:
        :rtype: list(core.cluster.BaseCluster)
        """
        path_clusters = list()
        current_segment = path[0]
        for next_segment in path[1:]:

            current_clusters = self.segment_clusters(current_segment)
            next_clusters = self.segment_clusters(next_segment)

            if len(current_clusters) > 1 and len(next_clusters) > 1:
                # Both are on relay points, so the current_segment cluster must
                # be the common one between them.

                for cluster in current_clusters:
                    if cluster in next_clusters:
                        path_clusters.append(cluster)
                        break

            elif len(current_clusters) > 1:
                # The current_segment segment is on a relay point. In this
                # case, the next_segment segment is not on a relay point, so
                # we can just use that.

                path_clusters.append(next_clusters[0])

            elif len(next_clusters) > 1:
                # The next_segment segment is on a relay point. In this case,
                # the current_segment segment is only in one cluster, so we
                # just use that.

                path_clusters.append(current_clusters[0])

            else:
                # Neither segments are relay points, just use the
                # current_segment cluster
                pass

            # Move current_segment to the next_segment segment
            current_segment = next_segment

        # Remove any duplicates
        path_clusters = list(orderedset.OrderedSet(path_clusters))
        return path_clusters

    def communication_delay(self, begin, end):
        """
        Compute the communication delay between any two segments. This is done
        as per Equation 1 in FLOWER.

        :param begin:
        :type begin: core.segment.Segment
        :param end:
        :type end: core.segment.Segment

        :return: The total communication delay in seconds
        :rtype: pq.second
        """

        duration, path = self.movement_model.shortest_distance(begin, end)
        path_clusters = self.count_clusters(path)

        segment_speed_pairs = list()
        path_index = 0
        last_segment = None
        for path_cluster in path_clusters:
            segments = list()
            if last_segment:
                segments.append(last_segment)

            while path[path_index] in path_cluster.tour.objects:
                segments.append(path[path_index])
                last_segment = path[path_index]

                path_index += 1
                if path_index >= len(path):
                    break

            segment_speed_pairs.append((path_cluster.mdc_speed, segments))

        travel_delay = 0.  # * pq.second
        for speed, segments in segment_speed_pairs:
            cluster_distance = 0  # * pq.meter
            start_segment = segments[0]
            for end_segment in segments[1:]:
                distance = np.linalg.norm(
                    start_segment.location.nd - end_segment.location.nd)
                cluster_distance += distance

            travel_delay += cluster_distance / speed

        transmission_delay = len(path_clusters)
        transmission_delay *= data.segment_volume(begin, end, self.env)
        transmission_delay /= self.env.comms_rate

        relay_delay = self.holding_time(path_clusters[1:])

        total_delay = travel_delay + transmission_delay + relay_delay
        return total_delay

    def holding_time(self, clusters):
        """

        :param clusters:
        :type clusters: list(BaseCluster)
        :return:
        :rtype: pq.second
        """

        latency = np.sum([self.tour_time(c) for c in clusters])
        return latency

    def tour_time(self, cluster):
        """

        :param cluster:
        :type cluster: focus.cluster.FOCUSCluster
        :return:
        :rtype: pq.second
        """

        if np.all(np.isclose(cluster.mdc_speed, 0.)):
            travel_time = 0.
        else:
            travel_time = cluster.tour_length / cluster.mdc_speed

        data_volume = self.energy_model.cluster_data_volume(cluster.cluster_id)
        transmit_time = data_volume / self.env.comms_rate

        total_time = travel_time + transmit_time
        return total_time

    def energy_balance(self):
        """

        :return:
        :rtype: pq.J
        """

        energy = list()
        for clust in self.sim.clusters:
            energy.append(self.energy_model.total_energy(clust.cluster_id))

        balance = np.std(energy)
        return balance

    def average_energy(self):
        """

        :return:
        :rtype: pq.J
        """
        energy = list()
        for clust in self.sim.clusters:
            energy.append(self.energy_model.total_energy(clust.cluster_id))

        average = np.mean(energy)
        return average

    def max_buffer_size(self):

        data_volumes = list()
        for cluster in self.sim.clusters:
            volume = self.energy_model.cluster_data_volume(
                cluster.cluster_id, intercluster_only=False)
            data_volumes.append(volume)

        max_data_volume = np.max(data_volumes)
        return max_data_volume
