import itertools

import numpy as np
import quantities as pq

from core import data, environment
from tocs.energy import ToCSEnergyModel
from tocs.movement import ToCSMovementModel


class ToCSRunnerError(Exception):
    pass


class ToCSRunner(object):
    def __init__(self, sim):
        """

        :param sim: The simulation after a run of ToCS
        :type sim: tocs.tocs_sim.TOCS
        """

        #: The simulation segment_volume
        self.sim = sim

        self.env = environment.Environment()
        self.movement_model = ToCSMovementModel(self.sim)
        self.energy_model = ToCSEnergyModel(self.sim)

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

        travel_delay = self.movement_model.shortest_distance(begin,
                                                             end) / self.env.mdc_speed

        if begin.cluster_id == end.cluster_id:
            transmission_count = 1
        elif (begin.cluster_id == self.sim.centroid.cluster_id) or (
                    end.cluster_id == self.sim.centroid.cluster_id):
            transmission_count = 2
        else:
            transmission_count = 3

        transmission_delay = transmission_count
        transmission_delay *= data.segment_volume(begin, end)
        transmission_delay /= self.env.comms_rate

        relay_delay = self.holding_time(begin, end)

        total_delay = travel_delay + transmission_delay + relay_delay
        return total_delay

    def find_cluster(self, seg):
        """

        :param seg:
        :type seg: core.segment.Segment
        :return:
        :rtype: tocs.cluster.ToCSCluster
        """

        cluster_id = seg.cluster_id
        found_cluster = None
        for clust in self.sim.clusters + [self.sim.centroid]:
            if clust.cluster_id == cluster_id:
                found_cluster = clust
                break

        if not found_cluster:
            raise ToCSRunnerError("Could not find cluster for {}".format(seg))

        return found_cluster

    def holding_time(self, begin, end):
        """

        :param begin:
        :type begin: core.segment.Segment
        :param end:
        :type end: core.segment.Segment
        :return:
        :rtype: pq.second
        """

        if begin.cluster_id == end.cluster_id:
            return 0. * pq.second

        begin_cluster = self.find_cluster(begin)
        centroid_time = self.tour_time(self.sim.centroid)

        latency = centroid_time
        for cluster in self.sim.clusters:
            if cluster == begin_cluster:
                continue

            latency += self.tour_time(cluster)

        return latency

    def tour_time(self, clust):
        """

        :param clust:
        :type clust: tocs.cluster.ToCSCluster
        :return:
        :rtype: pq.second
        """

        travel_time = clust.tour_length / self.env.mdc_speed

        if clust == self.sim.centroid:
            data_volume = self.energy_model.centroid_data_volume(
                clust.cluster_id)
        else:
            data_volume = self.energy_model.cluster_data_volume(
                clust.cluster_id)

        transmit_time = data_volume / self.env.comms_rate
        total_time = travel_time + transmit_time
        return total_time

    def energy_balance(self):
        """

        :return:
        :rtype: pq.J
        """

        energy = list()
        for clust in self.sim.clusters + [self.sim.centroid]:
            energy.append(self.energy_model.total_energy(clust.cluster_id))

        balance = np.std(energy) * pq.J
        return balance

    def average_energy(self):
        """

        :return:
        :rtype: pq.J
        """
        energy = list()
        for clust in self.sim.clusters + [self.sim.centroid]:
            energy.append(self.energy_model.total_energy(clust.cluster_id))

        average = np.mean(energy) * pq.J
        return average

    def max_buffer_size(self):

        data_volumes = list()
        for current in self.sim.clusters + [self.sim.centroid]:
            external_segments = [s for s in self.sim.segments if
                                 s.cluster_id != current.cluster_id]

            pairs = itertools.product(external_segments, current.segments)

            incoming = np.sum(
                [data.segment_volume(src, dst) for src, dst in pairs]) * pq.bit

            outgoing = np.sum(
                [data.segment_volume(src, dst) for dst, src in pairs]) * pq.bit

            data_volumes.append(incoming + outgoing)

        max_data_volume = np.max(data_volumes) * pq.bit
        return max_data_volume
