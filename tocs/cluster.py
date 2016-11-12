import quantities as pq

from core import data
from core import point
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

    def data_volume_mbits(self, all_clusters, all_segments):
        if not self.segments:
            return 0

        # Handle all intra-cluster data
        cluster_segs = self.segments
        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  cluster_segs if src != dst]
        data_vol = sum(
            [data.data(src, dst) for src, dst in intracluster_seg_pairs])

        # Handle inter-cluster data at the rendezvous point
        other_segs = [c for c in all_segments if c.cluster != self]
        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  other_segs]
        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in
                                   cluster_segs]

        # data volume for inter-cluster traffic
        data_vol += sum(
            data.data(src, dst) for src, dst in intercluster_seg_pairs)

        return data_vol

    def __str__(self):
        return "ToCS Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "TC{}".format(self.cluster_id)


class RelayNode(object):
    def __init__(self, position):
        self.location = point.Vec2(position)
        self.cluster_id = -1

    def __str__(self):
        return "RelayNode {}".format(self.location)

    def __repr__(self):
        return "RN{}".format(self.location)

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

    def data_volume_mbits(self, all_clusters, all_segments):

        # Handle all intra-cluster data for the hub
        if self.segments:
            hub_segs = self.segments
            hub_seg_pairs = [(src, dst) for src in hub_segs for dst in hub_segs
                             if src != dst]
            data_vol = sum([data.data(src, dst) for src, dst in hub_seg_pairs])
        else:
            data_vol = 0

        # Handle inter-cluster data for other clusters
        for clust, _ in self.rendezvous_points.items():
            local_segs = clust.segments
            remote_segs = [seg for seg in all_segments if seg.cluster != clust]

            # Generate the pairs of local-to-remote segments
            seg_pairs = [(seg_1, seg_2) for seg_1 in local_segs for seg_2 in
                         remote_segs]

            # Generate the pairs of remote-to-local segments
            seg_pairs += [(seg_1, seg_2) for seg_1 in remote_segs for seg_2 in
                          local_segs]

            # Add the inter-cluster data volume
            data_vol += sum(data.data(src, dst) for src, dst in seg_pairs)

        # Handle inter-cluster data for the hub itself
        # This is done by the above loop

        return data_vol

    def __str__(self):
        return "ToCS Centroid"

    def __repr__(self):
        return "TCentroid"
