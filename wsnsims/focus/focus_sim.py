import itertools
import logging
import time
import typing

import matplotlib.pyplot as plt
import numpy as np
import scipy.sparse.csgraph as sp
import scipy.spatial.distance as sp_dist
from pyclustering.cluster.cure import cure as Cure

from wsnsims.core.environment import Environment
from wsnsims.core.segment import Segment
from wsnsims.focus.cluster import FOCUSCluster
from wsnsims.focus.focus_runner import FOCUSRunner

logger = logging.getLogger(__name__)


class FOCUS(object):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """
        self.env = environment

        locs = np.random.rand(self.env.segment_count, 2) * self.env.grid_height
        self.segments = [Segment(nd) for nd in locs]

        self.clusters = list()  # type: typing.List[FOCUSCluster]

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
            xy_text = xy + 1.

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
            xy_text = xy + 1.

            ax.annotate(clust, xy=xy, xytext=xy_text)

        plt.show()

    def to_segments(self, locs):

        segments = list()
        for loc in locs:
            for segment in self.segments:
                if np.all(np.isclose(loc, segment.location.nd)):
                    segments.append(segment)

        return segments

    def create_clusters(self):

        segment_locs = [list(seg.location.nd) for seg in self.segments]
        cluster_count = self.env.mdc_count

        cure = Cure(segment_locs, cluster_count, number_represent_points=5,
                    compression=0.2)

        cure.process()
        loc_clusters = cure.get_clusters()
        segment_clusters = list()
        for loc_cluster in loc_clusters:
            segment_cluster = self.to_segments(loc_cluster)
            segment_clusters.append(segment_cluster)

        for segment_cluster in segment_clusters:
            new_cluster = FOCUSCluster(self.env)
            for segment in segment_cluster:
                new_cluster.add(segment)

            self.clusters.append(new_cluster)

    def closest_reps(self, cluster_1, cluster_2):
        """

        :param cluster_1:
        :type cluster_1: FOCUSCluster
        :param cluster_2:
        :type cluster_2: FOCUSCluster
        :return: The two closest representative segments
        :rtype: Segment, Segment
        """

        c1_locs = [list(seg.location.nd) for seg in cluster_1.nodes]
        c2_locs = [list(seg.location.nd) for seg in cluster_2.nodes]

        cure_1 = Cure(c1_locs, 1, number_represent_points=5, compression=0.)
        cure_2 = Cure(c2_locs, 1, number_represent_points=5, compression=0.)

        cure_1.process()
        cure_2.process()

        c1_reps = cure_1.get_representors()[0]
        c2_reps = cure_2.get_representors()[0]

        distances = sp_dist.cdist(c1_reps, c2_reps)
        indexes = np.unravel_index(np.argmin(distances), distances.shape)

        c1_seg = self.to_segments([c1_reps[indexes[0]]])[0]
        c2_seg = self.to_segments([c2_reps[indexes[1]]])[0]

        return c1_seg, c2_seg

    def compute_edge_weights(self, cluster_1, cluster_2):
        """

        :param cluster_1:
        :type cluster_1: FOCUSCluster
        :param cluster_2:
        :type cluster_2: FOCUSCluster
        :return: w(c1, c2), w(c2, c1)
        :rtype: (float, float), (Segment, Segment)
        """

        rep_segment_1, rep_segment_2 = self.closest_reps(cluster_1, cluster_2)

        tnw_1 = cluster_1.tour_length
        tnw_2 = cluster_2.tour_length

        cluster_1.add(rep_segment_2)
        tn_1 = cluster_1.tour_length
        cluster_1.remove(rep_segment_2)

        cluster_2.add(rep_segment_1)
        tn_2 = cluster_2.tour_length
        cluster_2.remove(rep_segment_1)

        w_1 = (tn_1 - tnw_1)
        w_2 = (tn_2 - tnw_2)

        return (w_1, w_2), (rep_segment_1, rep_segment_2)

    def merge_clusters(self, cluster_1, cluster_2):
        pass

    def join_clusters(self):

        # Generate an empty, N x N sparse graph
        node_count = len(self.clusters)
        dense = np.zeros((node_count, node_count), dtype=float)

        expand = {}

        cluster_pairs = itertools.combinations(self.clusters, 2)
        for cluster_pair in cluster_pairs:
            weights, segs = self.compute_edge_weights(*cluster_pair)
            c1_index = self.clusters.index(cluster_pair[0])
            c2_index = self.clusters.index(cluster_pair[1])

            dense[c1_index, c2_index] = weights[0]
            dense[c2_index, c1_index] = weights[1]

            expand[(c1_index, c2_index)] = segs[1]
            expand[(c2_index, c1_index)] = segs[0]

        sparse = sp.csgraph_from_dense(dense)
        mst = sp.minimum_spanning_tree(sparse)

        edges = mst.nonzero()
        edges = zip(edges[0], edges[1])
        for edge in edges:
            cluster = self.clusters[edge[0]]
            cluster.add(expand[edge])
            cluster.intersections.append(self.clusters[edge[1]])

    def compute_paths(self):
        self.create_clusters()
        # self.show_state()
        self.join_clusters()
        # self.show_state()
        return self

    def run(self):
        """

        :return:
        :rtype: focus.focus_runner.FOCUSRunner
        """
        sim = self.compute_paths()
        runner = FOCUSRunner(sim, self.env)
        logger.debug("Maximum comms delay: {}".format(
            runner.maximum_communication_delay()))
        logger.debug("Energy balance: {}".format(runner.energy_balance()))
        logger.debug("Average energy: {}".format(runner.average_energy()))
        logger.debug("Max buffer size: {}".format(runner.max_buffer_size()))
        return runner


def main():
    env = Environment()
    seed = int(time.time())

    # General testing ...
    # seed = 1484764250
    # env.segment_count = 12
    # env.mdc_count = 5

    # seed = 1487736569
    env.comms_range = 125

    logger.debug("Random seed is %s", seed)
    np.random.seed(seed)

    sim = FOCUS(env)
    sim.run()
    sim.show_state()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('focus_sim')
    main()
