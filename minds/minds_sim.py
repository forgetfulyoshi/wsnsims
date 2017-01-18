import logging
import time

import itertools
import matplotlib.pyplot as plt
import numpy as np
import quantities as pq
import scipy.sparse.csgraph as sp
from scipy.sparse import csr_matrix

from core import segment, environment, cluster
from minds import minds_runner

logger = logging.getLogger(__name__)

class MINDS(object):
    def __init__(self, locs):
        self.segments = [segment.Segment(nd) for nd in locs]
        self.env = environment.Environment()

        self.clusters = []

    def show_state(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)

        # Show the location of all segments
        segment_points = [seg.location.nd for seg in self.segments]
        segment_points = np.array(segment_points)
        ax.plot(segment_points[:, 0], segment_points[:, 1], 'bo')

        # Annotate the segments for easier debugging
        for seg in self.segments:
            xy = seg.location.nd
            xy_text = xy + (1. * pq.meter)

            ax.annotate(seg, xy=xy, xytext=xy_text)

        # Show the outline of the clusters
        for clust in self.clusters:
            route = clust.tour
            points = route.points
            ax.plot(points[route.vertices, 0], points[route.vertices, 1],
                    'b--', lw=2)

        # Annotate the clusters for easier debugging
        for clust in self.clusters:
            xy = clust.location.nd
            xy_text = xy + (1. * pq.meter)

            ax.annotate(clust, xy=xy, xytext=xy_text)

        plt.show()

    def _compute_adjacency_matrix(self, indexes):
        """
        Construct the adjacency graph over all segments

        :return:
        :rtype: sp.csr_matrix
        """

        if indexes:
            segs = [self.segments[i] for i in indexes]
        else:
            segs = self.segments

        # Generate an empty, N x N sparse graph
        node_count = len(segs)
        g_sparse = np.zeros((node_count, node_count), dtype=float)

        # Generate all pairs of segments
        segment_pairs = itertools.combinations(range(node_count), 2)

        # Fill the graph with the distances between segments
        for src, dst in segment_pairs:
            src_pos = segs[src].location.nd
            dst_pos = segs[dst].location.nd
            distance = np.linalg.norm(src_pos - dst_pos)
            g_sparse[src, dst] = distance

        g_sparse = sp.csgraph_from_dense(g_sparse)
        return g_sparse

    def build_cluster(self, segment_ids, relay):
        new_cluster = cluster.BaseCluster()

        for seg in segment_ids:
            new_cluster.add(self.segments[seg])

        new_cluster.relay_node = self.segments[relay]
        return new_cluster

    def compute_mst(self, indexes=None):
        """
        Compute the MST over the segments
        :return:
        """

        adj_matrix = self._compute_adjacency_matrix(indexes)
        tree = sp.minimum_spanning_tree(adj_matrix)
        return tree

    def find_mst_center(self, mst):
        """

        :param mst:
        :type mst: csr_matrix
        :return:
        :rtype: (int, int, int, csr_matrix)
        """

        distances = sp.floyd_warshall(mst, directed=False)
        segment_count, _ = distances.shape

        center = 0
        farthest_distance = np.inf
        farthest_node = 0
        for i in range(segment_count):
            distance = np.max(distances[i])
            if distance < farthest_distance:
                center = i
                farthest_distance = distance
                farthest_node = np.argmax(distances[i])

        branches = self.group_branches(mst, center)
        second_node = 0
        second_distance = 0
        for branch in branches:
            if farthest_node in branch:
                continue

            for node in branch:
                distance = distances[center, node]
                if distance > second_distance:
                    second_distance = node
                    second_node = node

        return center, farthest_node, second_node, distances

    def group_branches(self, graph, root, directed=False):
        """

        :param graph:
        :type graph: csr_matrix
        :param root:
        :type root: int
        :return:
        :rtype: list(list(int))
        """

        dft, preds = sp.depth_first_order(graph, root, directed=directed,
                                          return_predecessors=True)
        branches = []
        current_branch = -1
        for node in dft[1:]:
            if preds[node] == root:
                current_branch += 1
                branches.append([])
            branches[current_branch].append(node)

        return branches

    def split_mst(self, mst):
        """

        :param mst:
        :type mst: csr_matrix
        :return:
        :rtype: list(int), list(int), int
        """

        center, farthest, second, distances = self.find_mst_center(mst)
        branches = self.group_branches(mst, center)

        if len(branches) == 1:
            self.show_state()
            raise NotImplementedError("This case should not occur")

        if len(branches) == 2:
            return branches[0], branches[1], center

        farthest_branch = None
        second_branch = None
        for branch in branches:
            if farthest in branch:
                farthest_branch = branch

            if second in branch:
                second_branch = branch

        branches.remove(farthest_branch)
        branches.remove(second_branch)

        for branch in branches:
            dist_to_farthest = distances[farthest_branch[0], branch[0]]
            dist_to_second = distances[second_branch[0], branch[0]]

            if dist_to_farthest > dist_to_second:
                second_branch.extend(branch)
            else:
                farthest_branch.extend(branch)

        return farthest_branch, second_branch, center

    def compute_paths(self):

        segment_ids = [s.segment_id for s in self.segments]
        original_cluster = self.build_cluster(segment_ids, 0)
        self.clusters.append(original_cluster)

        if self.env.mdc_count == 1:
            return self

        for r in range(self.env.mdc_count):
            longest_cluster = max(self.clusters, key=lambda c: c.tour_length)
            segment_ids = [s.segment_id for s in longest_cluster.nodes]
            segment_ids.append(longest_cluster.relay_node.segment_id)

            cluster_mst = self.compute_mst(indexes=segment_ids)
            first, second, center = self.split_mst(cluster_mst)

            first_segments = list()
            for i in first:
                first_segments.append(segment_ids[i])

            second_segments = list()
            for i in second:
                second_segments.append(segment_ids[i])

            central_segment = segment_ids[center]

            first_cluster = self.build_cluster(first_segments, central_segment)
            second_cluster = self.build_cluster(second_segments,
                                                central_segment)

            self.clusters.remove(longest_cluster)
            self.clusters.append(first_cluster)
            self.clusters.append(second_cluster)

        return self

    def run(self):
        """

        :return:
        :rtype: minds.minds_runner.MINDSRunner
        """
        sim = self.compute_paths()
        runner = minds_runner.MINDSRunner(sim)
        logger.debug("Maximum comms delay: {}".format(
            runner.maximum_communication_delay()))
        logger.debug("Energy balance: {}".format(runner.energy_balance()))
        logger.debug("Average energy: {}".format(runner.average_energy()))
        logger.debug("Max buffer size: {}".format(runner.max_buffer_size()))
        return runner


def main():
    env = environment.Environment()
    # env.grid_height = 20000. * pq.meter
    # env.grid_width = 20000. * pq.meter
    # env.segment_count = 6
    # env.mdc_count = 3
    seed = int(time.time())
    # seed = 1483675991
    # seed = 1483676009  # center has in-degree of 3
    # seed = 1483998718  # center has in-degree of 2

    seed = 1484764250
    env.segment_count = 12
    env.mdc_count = 5

    logger.debug("Random seed is %s", seed)
    np.random.seed(seed)
    locs = np.random.rand(env.segment_count, 2) * env.grid_height
    sim = MINDS(locs)
    sim.run()
    sim.show_state()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('minds_sim')
    main()
