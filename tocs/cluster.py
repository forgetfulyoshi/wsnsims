import quantities as pq

from core.cluster import BaseCluster


class ToCSCluster(BaseCluster):
    def __init__(self):
        super(ToCSCluster, self).__init__()

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
    def __init__(self):
        super(ToCSCentroid, self).__init__()
        self.rendezvous_points = {}
        self._radio_range = 0. * pq.meter
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
