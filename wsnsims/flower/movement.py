import itertools
import logging

import numpy as np

import scipy.sparse.csgraph as sp

logger = logging.getLogger(__name__)


class FLOWERMovementError(Exception):
    pass


class FLOWERMovementModel(object):
    def __init__(self, simulation_data, environment):
        self.sim = simulation_data
        self.env = environment

        self._cell_indexes = {}

        #: Cached version of the adjacency matrix. Weights are path lengths.
        self._adj_mat = self._compute_adjacency_matrix()

        self._distance_mat, self._preds = self._compute_paths()

    def _compute_adjacency_matrix(self):
        """
        Build out the adjacency matrix based on the paths created by the
        builder. This takes the cluster paths and builds out a matrix suitable
        for use in Dijkstra's algorithm.

        :return: The adjacency matrix for the simulation
        :rtype: sp.csr_matrix
        """

        # Set up a quick-reference index to map cells to indexes
        for i, cell in enumerate(self.sim.cells):
            self._cell_indexes[cell] = i

        if all([self.sim.hub.cells == [self.sim.damaged],
                self.sim.damaged not in self.sim.cells]):
            # Add the "damaged" virtual cell to the index if we need it
            self._cell_indexes[self.sim.damaged] = len(self.sim.cells)

        node_count = len(list(self._cell_indexes.keys()))
        g_sparse = np.zeros((node_count, node_count), dtype=float)
        g_sparse[:] = np.inf

        for cluster in self.sim.clusters + [self.sim.hub]:
            cluster_tour = cluster.tour
            i = len(cluster_tour.vertices) - 1
            j = 0
            while j < len(cluster_tour.vertices):
                start_vertex = cluster_tour.vertices[i]
                stop_vertex = cluster_tour.vertices[j]

                start_pt = cluster_tour.points[start_vertex]
                stop_pt = cluster_tour.points[stop_vertex]
                distance = np.linalg.norm(stop_pt - start_pt)

                start_seg = cluster_tour.objects[start_vertex]
                stop_seg = cluster_tour.objects[stop_vertex]

                start_index = self._cell_indexes[start_seg]
                stop_index = self._cell_indexes[stop_seg]

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

        distance_mat, preds = sp.dijkstra(self._adj_mat, directed=True,
                                          return_predecessors=True)
        # assert not np.any(np.isinf(distance_mat))
        if np.any(np.isinf(distance_mat)):
            logger.debug("Found inf distance!!")

        return distance_mat, preds

    def shortest_distance(self, begin, end):
        """
        Get the shortest distance between any two segments.

        :param begin:
        :type begin: flower.cell.Cell
        :param end:
        :type end: flower.cell.Cell
        :return: float, list(int)
        """

        begin_index = self._cell_indexes[begin]
        end_index = self._cell_indexes[end]

        distance = self._distance_mat[begin_index, end_index]
        # distance *= pq.meter

        path = [begin]
        inv_index = {v: k for k, v in self._cell_indexes.items()}
        while True:
            next_index = self._preds[end_index, begin_index]
            if next_index == -9999:
                break

            begin_index = next_index

            seg = inv_index[next_index]
            path.append(seg)

        return distance, path

    def print_all_distances(self):

        cell_pairs = itertools.permutations(
            self.sim.cells + [self.sim.damaged], 2)

        for src, dst in cell_pairs:
            distance, _ = self.shortest_distance(src, dst)
            logger.debug("%s -> %s: %f", src, dst, distance)
