import collections
import itertools

import numpy as np
import quantities as pq

from core import data, environment
from focus.energy import FOCUSEnergyModel
from focus.movement import FOCUSMovementModel


class FOCUSRunnerError(Exception):
    pass


class FOCUSRunner(object):
    def __init__(self, sim):
        """

        :param sim: The simulation after a run of MINDS
        :type sim: focus.focus_sim.FOCUS
        """

        #: The simulation volume
        self.sim = sim

        self.env = environment.Environment()
        self.movement_model = FOCUSMovementModel(self.sim)
        self.energy_model = FOCUSEnergyModel(self.sim)

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
        max_delay *= pq.second

        return max_delay

    def count_clusters(self, path):

        clusters = collections.defaultdict(list)
        for clust in self.sim.clusters:
            for seg in path:
                if seg in clust.nodes:
                    clusters[clust].append(seg)

                if seg == clust.relay_node:
                    clusters[clust].append(seg)

        cluster_count = len([clusters.keys()])

        return cluster_count, clusters

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
        transmission_count, clusters = self.count_clusters(path)

        travel_delay = 0. * pq.second
        segment = path[0]
        for next_segment in path[1:]:
            distance = np.linalg.norm(
                segment.location.nd - next_segment.location.nd) * pq.meter

            current_cluster = None
            for cluster, segments in clusters.items():
                if segment in segments:
                    current_cluster = cluster
                    break

            if np.all(np.isclose(current_cluster.mdc_speed.magnitude, 0.)):
                continue

            travel_delay += distance / current_cluster.mdc_speed

        transmission_delay = transmission_count
        transmission_delay *= data.volume(begin, end)
        transmission_delay /= self.env.comms_rate

        relay_delay = self.holding_time(clusters)

        total_delay = travel_delay + transmission_delay + relay_delay
        return total_delay

    def holding_time(self, clusters):
        """

        :param clusters:
        :type clusters: list(BaseCluster)
        :return:
        :rtype: pq.second
        """

        latency = 0. * pq.second
        for clust in [clusters.keys()][1:]:
            cluster_time = self.tour_time(clust)
            latency += cluster_time

        return latency

    def tour_time(self, clust):
        """

        :param clust:
        :type clust: focus.cluster.FOCUSCluster
        :return:
        :rtype: pq.second
        """

        if np.all(np.isclose(clust.mdc_speed.magnitude, 0.)):
            return 0. * pq.second

        travel_time = clust.tour_length / clust.mdc_speed

        # Compute the time required to upload and download all data from each
        # segment in the cluster. This has to include both inter- and intra-
        # cluster data. Because of this, we're going to simply enumerate all
        # segments and for each one in the cluster, sum the data sent to the
        # segment. Similarly, for each segment in the cluster, we will sum the
        # data sent from the segment to all other segments.

        data_volume = 0. * pq.bit
        pairs = itertools.product(clust.segments, self.sim.segments)
        for src, dst in pairs:
            if src == dst:
                continue

            data_volume += data.volume(src, dst)
            data_volume += data.volume(dst, src)

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

        balance = np.std(energy) * pq.J
        return balance

    def average_energy(self):
        """

        :return:
        :rtype: pq.J
        """
        energy = list()
        for clust in self.sim.clusters:
            energy.append(self.energy_model.total_energy(clust.cluster_id))

        average = np.mean(energy) * pq.J
        return average

    def max_buffer_size(self):

        data_volumes = list()
        for current in self.sim.clusters:
            external_segments = [s for s in self.sim.segments if
                                 (s not in current.nodes) or (
                                     s != current.relay_node)]

            pairs = itertools.product(external_segments, current.nodes)

            incoming = np.sum(
                [data.volume(src, dst) for src, dst in pairs]) * pq.bit

            outgoing = np.sum(
                [data.volume(src, dst) for dst, src in pairs]) * pq.bit

            data_volumes.append(incoming + outgoing)

        max_data_volume = np.max(data_volumes) * pq.bit
        return max_data_volume
