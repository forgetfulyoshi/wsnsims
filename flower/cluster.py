import logging

from core import params, _tour, data
from core.cluster import BaseCluster, closest_nodes


class FlowerCluster(BaseCluster):
    def __init__(self):
        super(FlowerCluster, self).__init__()

        self.completed = False
        self.anchor = None
        self.central_cluster = None
        self._recent = None

    def __str__(self):
        return "Flower Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "FC{}".format(self.cluster_id)

    @property
    def cells(self):
        return self.nodes

    @cells.setter
    def cells(self, value):
        self.nodes = value

    @property
    def recent(self):
        return self._recent

    def add(self, cell):
        super(FlowerCluster, self).add(cell)
        cell.cluster = self
        cell.cluster_id = self.cluster_id

    def remove(self, cell):
        super(FlowerCluster, self).remove(cell)
        cell.cluster = None
        cell.cluster_id = params.NOT_CLUSTERED

    @recent.setter
    def recent(self, value):
        logging.debug("Setting RC(%r) to %r", self, value)
        self._recent = value

        if value not in self.nodes:
            logging.warning("%r is not a member of %r", value, self)

    def calculate_tour(self):
        if not self.cells:
            self._tour = []
            self._tour_length = 0
            return

        if len(self.cells) == 1:
            cells = self.cells + self.central_cluster.cells
        elif self.anchor:
            cells = self.cells + [self.anchor]
        else:
            cells = list(self.cells)

        self._tour = _tour.find_tour(cells, radius=0)
        self._tour_length = _tour.tour_length(self._tour)

    def update_anchor(self):
        # First, remove any cells that don't have our cluster id
        # new_cells = [c for c in self.cells if c.cluster_id == self.cluster_id]
        # if not new_cells:
        #     return

        if not self.cells:
            self.anchor = None
            return

        # Now, find the closest cell in the central cluster, and add it to ourselves
        _, anchor = closest_nodes(self, self.central_cluster, cell_distance=False)
        # new_cells.append(anchor)
        # self.cells = new_cells

        # self.central_cluster.anchors[self] = anchor
        self.anchor = anchor

    def merge(self, other):
        new_cluster = super(FlowerCluster, self).merge(other)
        new_cluster.central_cluster = self.central_cluster
        return new_cluster

    def data_volume_mbits(self, all_clusters, all_cells):
        if not self.cells:
            return 0

        # Handle all intra-cluster data
        cluster_cells = [c for c in all_cells if c.cluster_id == self.cluster_id]
        cluster_segs = [seg for segs in [c.segments for c in cluster_cells] for seg in segs]
        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in cluster_segs if src != dst]
        data_vol = sum([data.data(src, dst) for src, dst in intracluster_seg_pairs])

        # Handle inter-cluster data at the anchor
        other_cells = [c for c in all_cells if c.cluster_id != self.cluster_id]
        other_segs = [seg for segs in [c.segments for c in other_cells] for seg in segs]
        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in other_segs]
        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in cluster_segs]

        # data volume for inter-cluster traffic
        data_vol += sum(
            data.data(src, dst) for src, dst in intercluster_seg_pairs)

        return data_vol


class FlowerVirtualCluster(FlowerCluster):
    def __init__(self):
        super(FlowerVirtualCluster, self).__init__()

        self.virtual_cluster_id = params.NOT_CLUSTERED

    def __str__(self):
        return "Flower Virtual Cluster {}".format(self.virtual_cluster_id)

    def __repr__(self):
        return "FVC{}".format(self.virtual_cluster_id)

    def calculate_tour(self):
        if not self.cells:
            self._tour = []
            self._tour_length = 0
            return

        cells = self.cells + self.central_cluster.cells
        self._tour = _tour.find_tour(cells, radius=0)
        self._tour_length = _tour.tour_length(self._tour)

    def data_volume_mbits(self, all_clusters, all_cells):
        if not self.cells:
            return 0

        # Handle all intra-cluster data
        cluster_cells = [c for c in all_cells if c.virtual_cluster_id == self.virtual_cluster_id]
        cluster_segs = [seg for segs in [c.segments for c in cluster_cells] for seg in segs]
        intracluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in cluster_segs if src != dst]
        data_vol = sum([data.data(src, dst) for src, dst in intracluster_seg_pairs])

        # Handle inter-cluster data at the anchor
        other_cells = [c for c in all_cells if c.virtual_cluster_id != self.virtual_cluster_id]
        other_segs = [seg for segs in [c.segments for c in other_cells] for seg in segs]
        intercluster_seg_pairs = [(src, dst) for src in cluster_segs for dst in other_segs]
        intercluster_seg_pairs += [(src, dst) for src in other_segs for dst in cluster_segs]

        # data volume for inter-cluster traffic
        data_vol += sum(
            data.data(src, dst) for src, dst in intercluster_seg_pairs)

        return data_vol


class FlowerHub(FlowerCluster):
    def __init__(self):
        super(FlowerHub, self).__init__()
        # self.anchors = {}

    def calculate_tour(self):
        # cells = self.cells + list(self.anchors.values())
        cells = list(self.cells)
        self._tour = _tour.find_tour(cells, radius=0)
        self._tour_length = _tour.tour_length(self._tour)

    def __str__(self):
        return "Flower Hub Cluster"

    def __repr__(self):
        return "FH"

    def data_volume_mbits(self, all_clusters, all_cells):
        if not self.cells:
            return 0

        # Handle all intra-cluster data for the hub
        hub_cells = [c for c in all_cells if c.cluster_id == self.cluster_id]
        hub_segs = [seg for segs in [c.segments for c in hub_cells] for seg in segs]
        hub_seg_pairs = [(src, dst) for src in hub_segs for dst in hub_segs if src != dst]
        data_vol = sum([data.data(src, dst) for src, dst in hub_seg_pairs])

        # Handle inter-cluster data for other clusters
        anchor_cells = [a for a in [c.anchor for c in all_clusters if c.cluster_id != self.cluster_id]]
        anchor_cells = list(set(anchor_cells))
        for cell in anchor_cells:
            # Get the segments served by this anchor
            local_clusters = [c for c in all_clusters if c.anchor == cell]
            local_cells = [c for c in all_cells if c.cluster_id in [clust.cluster_id for clust in local_clusters]]
            local_segs = [seg for segs in [c.segments for c in local_cells] for seg in segs]

            # Get the segments not served by this anchor
            remote_clusters = [c for c in all_clusters if c.anchor != cell and c != self]
            remote_cells = [c for c in all_cells if c.cluster_id in [clust.cluster_id for clust in remote_clusters]]
            remote_segs = [seg for segs in [c.segments for c in remote_cells] for seg in segs]

            # Generate the pairs of local-to-remote segments
            seg_pairs = [(seg_1, seg_2) for seg_1 in local_segs for seg_2 in remote_segs]

            # Generate the pairs of remote-to-local segments
            seg_pairs += [(seg_1, seg_2) for seg_1 in remote_segs for seg_2 in local_segs]

            # Add the inter-cluster data volume
            data_vol += sum(data.data(src, dst) for src, dst in seg_pairs)

        # Handle inter-cluster data for the hub itself
        # This is done by the above loop

        return data_vol


class FlowerVirtualHub(FlowerVirtualCluster):
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