import logging

from core import params, _tour, data
from core.cluster import BaseCluster, closest_nodes


class FlowerCluster(BaseCluster):
    def __init__(self, central_cluster):
        super(FlowerCluster, self).__init__()

        self.central_cluster = central_cluster
        self.central_cluster.register(self)

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
        for cell in self.cells:
            for seg in cell.segments:
                yield seg

    @property
    def anchor(self):
        if not self.relay_node:
            self.update_anchor()

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

    def update_anchor(self):
        # First, remove any cells that don't have our cluster id
        # new_cells = [c for c in self.cells if c.cluster_id == self.cluster_id]
        # if not new_cells:
        #     return

        if not self.cells:
            self.anchor = None
            return

        # Now, find the closest cell in the central cluster, and add it to ourselves
        _, anchor = closest_nodes(self, self.central_cluster)
        assert anchor
        # new_cells.append(anchor)
        # self.cells = new_cells

        # self.central_cluster.anchors[self] = anchor
        self.anchor = anchor

    def merge(self, other, *args, **kwargs):
        c = super(FlowerCluster, self).merge(other, self.central_cluster)
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
    def __init__(self, central_cluster):
        super(FlowerVirtualCluster, self).__init__(central_cluster)

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
        self._client_clusters = list()
        super(FlowerHub, self).__init__(self)
        # self.anchors = {}

    # def calculate_tour(self):
    #     # cells = self.cells + list(self.anchors.values())
    #     cells = list(self.cells)
    #     self._tour = _tour.find_tour(cells, radius=0)
    #     self._tour_length = _tour.tour_length(self._tour)

    def update_anchors(self):
        for clust in self._client_clusters:
            clust.update_anchor()

    def add(self, cell):
        super(FlowerHub, self).add(cell)
        self.update_anchors()

    def remove(self, cell):
        super(FlowerHub, self).remove(cell)
        self.update_anchors()

    def __str__(self):
        return "Flower Hub Cluster"

    def __repr__(self):
        return "FH"

    def register(self, client_cluster):
        if client_cluster == self:
            return

        self._client_clusters.append(client_cluster)

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
        super(FlowerVirtualHub, self).__init__(self)

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
