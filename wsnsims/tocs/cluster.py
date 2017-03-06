import itertools
import logging

from wsnsims.core import point

from wsnsims.core.cluster import BaseCluster

logger = logging.getLogger(__name__)


class ToCSCluster(BaseCluster):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """
        super(ToCSCluster, self).__init__(environment)

    @property
    def rendezvous_point(self):
        return self.relay_node

    @rendezvous_point.setter
    def rendezvous_point(self, value):
        self.relay_node = value

    @property
    def segments(self):
        return self.nodes

    @segments.setter
    def segments(self, value):
        self.nodes = value

    def __str__(self):
        return "ToCS Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "TC{}".format(self.cluster_id)


class ToCSCentroid(ToCSCluster):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """
        super(ToCSCentroid, self).__init__(environment)
        self._radio_range = 0.  # * pq.meter
        self._segments = []

    def add_segment(self, segment):
        """
        Because the central cluster can contain both rendezvous points and
        segments, we need a way to do some tracking of the segments separate
        from the RPs. This way, we can query for just the segments in the
        central cluster during the ToCS optimization phase. To add an RP,
        use add() as normal, but to add a segment, use this method. This will
        also take care of adding the segment to the tour path.

        :param segment: The segment to add to the central cluster.
        :type segment: core.segment.Segment
        :return: None
        """

        if segment not in self._segments:
            self._segments.append(segment)
            self.add(segment)

    def remove_segment(self, segment):
        """
        This routine provides the inverse to add_segment(). See its
        documentation for an explanation of when to use these instead of the
        standard add() or remove().

        :param segment: The segment to remove from the central cluster.
        :type segment: core.segment.Segment
        :return: None
        """

        self._segments.remove(segment)
        self.remove(segment)

    @property
    def segments(self):
        """
        As the central cluster can contain both segments and rendezvous points,
        this property allows you to get only the actual segments (if any
        exist).

        :return: The list of segments in the central cluster
        :rtype: list(core.segment.Segment)
        """
        return self._segments

    def __str__(self):
        return "ToCS Centroid"

    def __repr__(self):
        return "TCentroid"


def combine_clusters(clusters, centroid):
    """

    :param clusters:
    :param centroid:
    :return:
    """
    index = 0
    decorated = list()

    cluster_pairs = itertools.combinations(clusters, 2)
    for c_i, c_j in cluster_pairs:
        tc_1 = c_i.merge(c_j).merge(centroid)
        tc_2 = c_i.merge(centroid)

        combination_cost = tc_1.tour_length - tc_2.tour_length
        decorated.append((combination_cost, index, c_i, c_j))
        index += 1

    cost, _, c_i, c_j = min(decorated)
    logger.debug("Combining %s and %s (Cost: %f)", c_i, c_j, cost)

    new_clusters = list(clusters)
    new_cluster = c_i.merge(c_j)

    for node in new_cluster.nodes:
        node.cluster_id = new_cluster.cluster_id

    new_clusters.remove(c_i)
    new_clusters.remove(c_j)
    new_clusters.append(new_cluster)
    return new_clusters


class RelayNode(object):
    def __init__(self, position):
        self.location = point.Vec2(position)
        self.cluster_id = -1

    def __str__(self):
        return "RelayNode {}".format(self.location)

    def __repr__(self):
        return "RN{}".format(self.location)
