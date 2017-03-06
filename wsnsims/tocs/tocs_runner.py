import numpy as np

from wsnsims.core import data
from wsnsims.tocs.energy import ToCSEnergyModel

from wsnsims.tocs.movement import ToCSMovementModel


class ToCSRunnerError(Exception):
    pass


class ToCSRunner(object):
    def __init__(self, sim, environment):
        """

        :param sim: The simulation after a run of ToCS
        :type sim: tocs.tocs_sim.TOCS
        :param environment:
        :type environment: core.environment.Environment
        """

        self.sim = sim

        self.env = environment
        self.movement_model = ToCSMovementModel(self.sim, self.env)
        self.energy_model = ToCSEnergyModel(self.sim, self.env)

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
        transmission_delay *= data.segment_volume(begin, end, self.env)
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
            return 0.

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

        balance = np.std(energy)
        return balance

    def average_energy(self):
        """

        :return:
        :rtype: pq.J
        """
        energy = list()
        for clust in self.sim.clusters + [self.sim.centroid]:
            energy.append(self.energy_model.total_energy(clust.cluster_id))

        average = np.mean(energy)
        return average

    def max_buffer_size(self):

        data_volumes = list()
        for cluster in self.sim.clusters:
            volume = self.energy_model.cluster_data_volume(
                cluster.cluster_id, intercluster_only=False)
            data_volumes.append(volume)

        centroid_volume = self.energy_model.centroid_data_volume(
            self.sim.centroid.cluster_id)
        data_volumes.append(centroid_volume)

        max_data_volume = np.max(data_volumes)
        return max_data_volume
