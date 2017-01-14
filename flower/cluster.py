import itertools
import logging

from core import _tour, data
from core.cluster import BaseCluster

logger = logging.getLogger(__name__)

class FlowerCluster(BaseCluster):
    def __init__(self):
        super(FlowerCluster, self).__init__()

        self.completed = False
        self.recent = None

    @property
    def cluster_id(self):
        return super(FlowerCluster, self).cluster_id

    @cluster_id.setter
    def cluster_id(self, value):
        self._cluster_id = value
        for cell in self.cells:
            cell.cluster_id = self.cluster_id

    @property
    def cells(self):
        return self.nodes

    @cells.setter
    def cells(self, value):
        self.nodes = value

    @property
    def segments(self):
        cluster_segments = list()
        for cell in self.cells:
            cluster_segments.extend(cell.segments)

        return cluster_segments

    @property
    def anchor(self):
        return self.relay_node

    @anchor.setter
    def anchor(self, value):
        self.relay_node = value

    def add(self, cell):
        super(FlowerCluster, self).add(cell)
        self.recent = cell

    def remove(self, cell):
        super(FlowerCluster, self).remove(cell)
        if cell == self.recent:
            self.recent = None

    def __str__(self):
        return "Flower Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "FC{}".format(self.cluster_id)

    # def calculate_tour(self):
    #     if not self.cells:
    #         self._tour = []
    #         self._tour_length = 0
    #         return
    #
    #     if len(self.cells) == 1:
    #         cells = self.cells + self.central_cluster.cells
    #     elif self.anchor:
    #         cells = self.cells + [self.anchor]
    #     else:
    #         cells = list(self.cells)
    #
    #     self._tour = _tour.find_tour(cells, radius=0)
    #     self._tour_length = _tour.tour_length(self._tour)

    def merge(self, other, *args, **kwargs):
        c = super(FlowerCluster, self).merge(other)
        return c

    def data_volume_mbits(self, all_clusters, all_cells):
        if not self.cells:
            return 0

        # Handle all intra-cluster volume
        cluster_cells = [c for c in all_cells if
                         c.cluster_id == self.cluster_id]
        cluster_segs = [seg for segs in [c.segments for c in cluster_cells] for
                        seg in segs]
        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  cluster_segs if src != dst]
        data_vol = sum(
            [data.volume(src, dst) for src, dst in intracluster_seg_pairs])

        # Handle inter-cluster volume at the anchor
        other_cells = [c for c in all_cells if c.cluster_id != self.cluster_id]
        other_segs = [seg for segs in [c.segments for c in other_cells] for seg
                      in segs]
        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  other_segs]
        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in
                                   cluster_segs]

        # volume volume for inter-cluster traffic
        data_vol += sum(
            data.volume(src, dst) for src, dst in intercluster_seg_pairs)

        return data_vol


class FlowerVirtualCluster(FlowerCluster):
    def __init__(self):
        super(FlowerVirtualCluster, self).__init__()

    def __str__(self):
        return "Flower Virtual Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "FVC{}".format(self.cluster_id)

    @property
    def cluster_id(self):
        return super(FlowerVirtualCluster, self).cluster_id

    @cluster_id.setter
    def cluster_id(self, value):
        self._cluster_id = value
        for cell in self.cells:
            cell.virtual_cluster_id = self.cluster_id

    # def calculate_tour(self):
    #     if not self.cells:
    #         self._tour = []
    #         self._tour_length = 0
    #         return
    #
    #     cells = self.cells + self.central_cluster.cells
    #     self._tour = _tour.find_tour(cells, radius=0)
    #     self._tour_length = _tour.tour_length(self._tour)

    def data_volume_mbits(self, all_clusters, all_cells):
        if not self.cells:
            return 0

        # Handle all intra-cluster volume
        cluster_cells = [c for c in all_cells if
                         c.virtual_cluster_id == self.virtual_cluster_id]
        cluster_segs = [seg for segs in [c.segments for c in cluster_cells] for
                        seg in segs]
        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  cluster_segs if src != dst]
        data_vol = sum(
            [data.volume(src, dst) for src, dst in intracluster_seg_pairs])

        # Handle inter-cluster volume at the anchor
        other_cells = [c for c in all_cells if
                       c.virtual_cluster_id != self.virtual_cluster_id]
        other_segs = [seg for segs in [c.segments for c in other_cells] for seg
                      in segs]
        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in
                                  other_segs]
        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in
                                   cluster_segs]

        # volume volume for inter-cluster traffic
        data_vol += sum(
            data.volume(src, dst) for src, dst in intercluster_seg_pairs)

        return data_vol


class FlowerHub(FlowerCluster):
    def __init__(self):
        super(FlowerHub, self).__init__()
        # self.anchors = {}

    # def calculate_tour(self):
    #     # cells = self.cells + list(self.anchors.values())
    #     cells = list(self.cells)
    #     self._tour = _tour.find_tour(cells, radius=0)
    #     self._tour_length = _tour.tour_length(self._tour)

    def __str__(self):
        return "Flower Hub Cluster"

    def __repr__(self):
        return "FH"

    def add(self, node):
        """

        :param node:
        :type node: core.segment.Segment
        :return:
        """
        if node not in self.nodes:
            logger.debug("Adding %s to %s", node, self)
            node.virtual_cluster_id = self.cluster_id
            self.nodes.append(node)
            self._invalidate_cache()
        else:
            logger.warning("Re-added %s to %s", node, self)

    def remove(self, node):
        logger.debug("Removing %s from %s", node, self)
        self.nodes.remove(node)
        node.virtual_cluster_id = -1
        self._invalidate_cache()

    def data_volume_mbits(self, all_clusters, all_cells):
        if not self.cells:
            return 0

        # Handle all intra-cluster volume for the hub
        hub_cells = [c for c in all_cells if c.cluster_id == self.cluster_id]
        hub_segs = [seg for segs in [c.segments for c in hub_cells] for seg in
                    segs]
        hub_seg_pairs = [(src, dst) for src in hub_segs for dst in hub_segs if
                         src != dst]
        data_vol = sum([data.volume(src, dst) for src, dst in hub_seg_pairs])

        # Handle inter-cluster volume for other clusters
        anchor_cells = [a for a in [c.anchor for c in all_clusters if
                                    c.cluster_id != self.cluster_id]]
        anchor_cells = list(set(anchor_cells))
        for cell in anchor_cells:
            # Get the segments served by this anchor
            local_clusters = [c for c in all_clusters if c.anchor == cell]
            local_cells = [c for c in all_cells if
                           c.cluster_id in [clust.cluster_id for clust in
                                            local_clusters]]
            local_segs = [seg for segs in [c.segments for c in local_cells] for
                          seg in segs]

            # Get the segments not served by this anchor
            remote_clusters = [c for c in all_clusters if
                               c.anchor != cell and c != self]
            remote_cells = [c for c in all_cells if
                            c.cluster_id in [clust.cluster_id for clust in
                                             remote_clusters]]
            remote_segs = [seg for segs in [c.segments for c in remote_cells]
                           for seg in segs]

            # Generate the pairs of local-to-remote segments
            seg_pairs = [(seg_1, seg_2) for seg_1 in local_segs for seg_2 in
                         remote_segs]

            # Generate the pairs of remote-to-local segments
            seg_pairs += [(seg_1, seg_2) for seg_1 in remote_segs for seg_2 in
                          local_segs]

            # Add the inter-cluster volume volume
            data_vol += sum(data.volume(src, dst) for src, dst in seg_pairs)

        # Handle inter-cluster volume for the hub itself
        # This is done by the above loop

        return data_vol


class FlowerVirtualHub(FlowerVirtualCluster):
    def __init__(self):
        super(FlowerVirtualHub, self).__init__()

    def calculate_tour(self):
        cells = list(self.cells)

        self._tour = _tour.find_tour(cells, radius=0)
        self._tour_length = _tour.tour_length(self._tour)

    def __str__(self):
        return "Flower Virtual Hub Cluster"

    def __repr__(self):
        return "FVH"

    def data_volume_mbits(self, all_clusters, all_cells):
        return 0

    def register(self, client_cluster):
        pass


def _merge_clusters(clusters, centroid):
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
    logger.info("Combining %s and %s (Cost: %f)", c_i, c_j, cost)

    new_clusters = list(clusters)
    new_cluster = c_i.merge(c_j)

    new_clusters.remove(c_i)
    new_clusters.remove(c_j)
    new_clusters.append(new_cluster)
    return new_clusters, new_cluster


def combine_virtual_clusters(clusters, centroid):
    new_clusters, new_cluster = _merge_clusters(clusters, centroid)

    for node in new_cluster.nodes:
        node.virtual_cluster_id = new_cluster.cluster_id

    return new_clusters
