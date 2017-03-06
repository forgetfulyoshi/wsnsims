import logging

import numpy as np

import scipy.sparse.csgraph as sp

logger = logging.getLogger(__name__)


class ToCSMovementModel(object):
    def __init__(self, simulation_data, environment):
        """

        :param simulation_data:
        :type simulation_data: tocs.tocs_sim.TOCS
        :param environment:
        :type environment: core.environment.Environment
        """
        self.sim = simulation_data
        self.env = environment

        self._segment_indexes = {}

        #: Cached version of the adjacency matrix. Weights are path lengths.
        self._adj_mat = self._compute_adjacency_matrix()

        self._distance_mat = self._compute_paths()

    def _compute_adjacency_matrix(self):
        """
        Build out the adjacency matrix based on the paths created by the
        builder. This takes the cluster paths and builds out a matrix suitable
        for use in Dijkstra's algorithm.

        This routine just sets the value of the self.sim attribute.

        :return: None
        """

        i = 0
        for clust in self.sim.clusters + [self.sim.centroid]:
            for seg_vertex in clust.tour.vertices:
                seg = clust.tour.objects[seg_vertex]
                if seg not in self._segment_indexes:
                    self._segment_indexes[seg] = i
                    i += 1

        # First we need to get the total number of segments and relay nodes so
        # we can create an N x N matrix. This is simply the number of segments
        # plus the number of rendezvous points. As ToCS guarantees a single
        # rendezvous point per cluster, we can just use the number of clusters.

        node_count = len(self.sim.segments) + len(self.sim.clusters)
        g_sparse = np.zeros((node_count, node_count), dtype=float)
        g_sparse[:] = np.inf

        for clust in self.sim.clusters + [self.sim.centroid]:
            cluster_tour = clust.tour
            i = len(cluster_tour.vertices) - 1
            j = 0
            while j < len(cluster_tour.vertices):
                start_vertex = cluster_tour.vertices[i]
                stop_vertex = cluster_tour.vertices[j]

                start_pt = cluster_tour.collection_points[start_vertex]
                stop_pt = cluster_tour.collection_points[stop_vertex]
                distance = np.linalg.norm(stop_pt - start_pt)

                start_seg = cluster_tour.objects[start_vertex]
                stop_seg = cluster_tour.objects[stop_vertex]

                start_index = self._segment_indexes[start_seg]
                stop_index = self._segment_indexes[stop_seg]

                g_sparse[start_index, stop_index] = distance

                i = j
                j += 1

        g_sparse = sp.csgraph_from_dense(g_sparse, null_value=np.inf)
        return g_sparse

    def _compute_paths(self):
        """
        Run Dijkstra's algorithm over the adjacency matrix for the paths
        produced by the simulation.

        :return: The distance matrix based on adjacency matrix self._adj_mat
        :rtype: np.array
        """

        distance_mat = sp.dijkstra(self._adj_mat, directed=True)
        # assert not np.any(np.isinf(distance_mat))
        if np.any(np.isinf(distance_mat)):
            logger.debug("Found inf distance!!")

        return distance_mat

    def shortest_distance(self, begin, end):
        """
        Get the shortest distance between any two segments.

        :param begin:
        :type begin: core.segment.Segment
        :param end:
        :type end: core.segment.Segment
        :return: float
        """

        begin_index = self._segment_indexes[begin]
        end_index = self._segment_indexes[end]

        distance = self._distance_mat[begin_index, end_index]
        # distance *= pq.meter
        return distance
