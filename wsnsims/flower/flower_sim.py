"""Main FLOWER simulation logic"""

import collections
import logging
import warnings
from typing import List

import matplotlib.pyplot as plt
import numpy as np

from wsnsims.core import segment
from wsnsims.core.cluster import closest_nodes
from wsnsims.core.comparisons import much_greater_than
from wsnsims.core.environment import Environment
from wsnsims.flower import flower_runner
from wsnsims.flower import grid
from wsnsims.flower.cluster import FlowerCluster
from wsnsims.flower.cluster import FlowerHub
from wsnsims.flower.cluster import FlowerVirtualCluster
from wsnsims.flower.cluster import FlowerVirtualHub
from wsnsims.flower.energy import FLOWEREnergyModel
from wsnsims.tocs.cluster import combine_clusters

logger = logging.getLogger(__name__)
warnings.filterwarnings('error')


class FlowerError(Exception):
    pass


class FLOWER(object):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """

        self.env = environment

        locs = np.random.rand(self.env.segment_count, 2) * self.env.grid_height
        self.segments = [segment.Segment(loc) for loc in locs]

        self.grid = grid.Grid(self.segments, self.env)
        self.cells = list(self.grid.cells())

        segment_centroid = np.mean(locs, axis=0)
        logger.debug("Centroid located at %s", segment_centroid)
        self.damaged = self.grid.closest_cell(segment_centroid)

        self.energy_model = FLOWEREnergyModel(self, self.env)

        self.virtual_clusters = list()  # type: List[FlowerVirtualCluster]
        self.clusters = list()  # type: List[FlowerCluster]

        # Create a virtual cell to represent the center of the damaged area
        virtual_center_cell = self.damaged

        self.virtual_hub = FlowerVirtualHub(self.env)
        self.virtual_hub.add(virtual_center_cell)
        self.virtual_hub.cluster_id = self.env.mdc_count - 1

        self.hub = FlowerHub(self.env)
        self.hub.add(virtual_center_cell)
        self.hub.cluster_id = self.env.mdc_count - 1

        self.em_is_large = False
        self.ec_is_large = False

    def show_state(self):

        fig = plt.figure()
        ax = fig.add_subplot(111)

        # Show the location of all segments
        segment_points = [seg.location.nd for seg in self.segments]
        segment_points = np.array(segment_points)
        ax.plot(segment_points[:, 0], segment_points[:, 1], 'bo')

        # Show the location of all cells
        cell_points = [c.location.nd for c in self.cells]
        cell_points = np.array(cell_points)
        ax.plot(cell_points[:, 0], cell_points[:, 1], 'rx')

        # Illustrate the communication distance from each cell
        for cell_point in cell_points:
            circle = plt.Circle((cell_point[0], cell_point[1]),
                                radius=self.env.comms_range, alpha=0.1)
            ax.add_patch(circle)

        # Annotate the cells for easier debugging
        for cell in self.cells:
            xy = cell.location.nd
            xy_text = xy + 1.
            ax.annotate(cell, xy=xy, xytext=xy_text)

        # Draw lines between each cell the clusters to illustrate the cluster
        # formations.
        for cluster in self.clusters + [self.hub]:
            route = cluster.tour
            cps = route.points
            ax.plot(cps[:, 0], cps[:, 1], 'go')
            ax.plot(cps[route.vertices, 0], cps[route.vertices, 1], 'g--',
                    lw=2)

        for cluster in [self.hub]:
            route = cluster.tour
            cps = route.points
            ax.plot(cps[:, 0], cps[:, 1], 'ro')
            ax.plot(cps[route.vertices, 0], cps[route.vertices, 1], 'r--',
                    lw=2)

        # Annotate the clusters for easier debugging
        for cluster in self.clusters + [self.hub]:
            xy = cluster.location.nd
            xy_text = xy + 1.
            ax.annotate(cluster, xy=xy, xytext=xy_text)

        plt.show()

    def find_cells(self):

        for cell in self.grid.cells():
            # Calculate the cell's proximity as it's cell distance from
            # the center of the "damaged area."
            cell.proximity = grid.cell_distance(cell, self.damaged)

        # Calculate the number of one-hop segments within range of each cell
        for cell in self.grid.cells():
            segments = set()
            for nbr in cell.neighbors:
                segments = set.union(segments, nbr.segments)
                segments = segments.difference(cell.segments)

            cell.single_hop_count = len(segments)

        # First, we need to filter the "families" for the set coverage. We
        # start by filtering for access, then 1-hop count, then proximity.
        families = [c for c in self.grid.cells() if c.segments]

        # Group by segments covered, this also has the effect of filtering by
        # access.
        family_map = collections.defaultdict(list)
        for cell in families:
            family_map[tuple(cell.segments)].append(cell)

        # Filter by 1-hop
        for segments, cells in family_map.items():
            if len(cells) == 1:
                continue

            best_1_hop = 0
            best_cells = list()
            for cell in cells:
                if cell.single_hop_count > best_1_hop:
                    best_1_hop = cell.single_hop_count
                    best_cells.clear()
                    best_cells.append(cell)
                elif cell.single_hop_count == best_1_hop:
                    best_cells.append(cell)

            family_map[segments] = best_cells

        # Filter by proximity
        for segments, cells in family_map.items():
            if len(cells) == 1:
                continue

            best_proximity = np.inf
            best_cells = list()
            for cell in cells:
                if cell.proximity < best_proximity:
                    best_proximity = cell.proximity
                    best_cells.clear()
                    best_cells.append(cell)

            assert best_cells
            family_map[segments] = best_cells

        families = list()
        for _, cells in family_map.items():
            families.extend(cells)

        # Calculate the set cover over the segments
        cover = list()
        uncovered = set(self.segments)

        while uncovered:
            selected = max(families, key=lambda s: len(
                uncovered.intersection(set(s.segments))))
            uncovered -= set(selected.segments)
            cover.append(selected)

        # Initialized!!
        cell_cover = list(cover)
        logger.debug("Length of cover: %d", len(cell_cover))

        assert self.env.mdc_count < len(cell_cover)

        # Remove duplication among the cells
        cell_cover.sort(key=lambda c: len(c.segments), reverse=True)

        covered_segments = list()
        for cell in cell_cover:
            segments = list(cell.segments)
            for seg in segments:
                if seg in covered_segments:
                    # This segment is already served by another cell
                    cell.segments.remove(seg)
                else:
                    covered_segments.append(seg)

        segment_count = 0
        for cell in cell_cover:
            segment_count += len(cell.segments)

        assert segment_count == len(self.segments)

        # For future lookups, set a reference from each segment to its cell
        for cell in cell_cover:
            for seg in cell.segments:
                seg.cell = cell

        # Sort the cells by ID to ensure consistency across runs.
        self.cells = sorted(cell_cover, key=lambda c: c.cell_id)

    @staticmethod
    def _polar_angle(point, origin):
        vector = point - origin
        angle = np.arctan2(vector[1], vector[0])
        return angle

    def polar_sort(self, clusters):
        """

        :param clusters:
        :type clusters: list(FlowerCluster)
        :return:
        """

        points = [c.location.nd for c in clusters]
        origin = self.damaged.location.nd

        polar_angles = [self._polar_angle(p, origin) for p in points]
        indexes = np.argsort(polar_angles)

        sorted_clusters = np.array(clusters)[indexes]
        return list(sorted_clusters)

    def create_virtual_clusters(self):

        for cell in self.cells:
            c = FlowerVirtualCluster(self.env)
            c.add(cell)
            self.virtual_clusters.append(c)

        # Combine the clusters until we have MDC_COUNT - 1 non-central, virtual
        # clusters
        while len(self.virtual_clusters) >= self.env.mdc_count:
            self.virtual_clusters = combine_clusters(self.virtual_clusters,
                                                     self.virtual_hub)

        # FLOWER has some dependencies on the order of cluster IDs, so we need
        # to sort and re-label each virtual cluster.
        sorted_clusters = self.polar_sort(self.virtual_clusters)
        for i, vc in enumerate(sorted_clusters):
            vc.cluster_id = i

    def greedy_expansion(self):

        # First round (initial cell setup and energy calculation)

        for c in self.cells:
            c.cluster_id = -1

        for vc in self.virtual_clusters:
            c = FlowerCluster(self.env)
            c.cluster_id = vc.cluster_id
            c.anchor = self.damaged

            closest_cell, _ = closest_nodes(vc, self.hub)
            c.add(closest_cell)
            self.clusters.append(c)

        assert self.energy_model.total_movement_energy(self.hub) == 0.

        # Rounds 2 through N
        r = 1
        while any(not c.completed for c in self.clusters):

            r += 1

            # Determine the minimum-cost cluster by first filtering out all
            # non-completed clusters. Then find the the cluster with the lowest
            # total cost.
            candidates = self.clusters + [self.hub]
            candidates = [c for c in candidates if not c.completed]
            c_least = min(candidates,
                          key=lambda x: self.total_cluster_energy(x))

            # In general, only consider cells that have not already been added
            # to a cluster. There is an exception to this when expanding the
            # hub cluster.
            cells = [c for c in self.cells if c.cluster_id == -1]

            # If there are no more cells to assign, then we mark this cluster
            # as "completed"
            if not cells:
                c_least.completed = True
                logger.debug("All cells assigned. Marking %s as completed",
                             c_least)
                continue

            if c_least == self.hub:

                # This logic handles the case where the hub cluster is has the
                # fewest energy requirements. Either the cluster will be moved
                # (initialization) or it will be grown.
                #
                # If the hub cluster is still in its original location at the
                # center of the damaged area, we need to move it to an actual
                # cell. If the hub has already been moved, then we expand it by
                # finding the cell nearest to the center of the damaged area,
                # and that itself hasn't already been added to the hub cluster.

                if c_least.cells == [self.damaged]:
                    # Find the nearest cell to the center of the damaged area
                    # and move the hub to it. This is equivalent to finding the
                    # cell with the lowest proximity.
                    best_cell = min(cells, key=lambda x: x.proximity)

                    # As the hub only currently has the virtual center cell in
                    # it, we can just "move" the hub to the nearest real cell
                    # by replacing the virtual cell with it.
                    self.hub.remove(self.damaged)
                    self.hub.add(best_cell)

                    # Just for proper bookkeeping, reset the virtual cell's ID
                    # to NOT_CLUSTERED
                    self.damaged.cluster_id = -1
                    self.damaged.virtual_cluster_id = -1
                    logger.debug("ROUND %d: Moved %s to %s", r, self.hub,
                                 best_cell)

                else:
                    # Find the set of cells that are not already in the hub
                    # cluster
                    available_cells = list(set(cells) - set(self.hub.cells))

                    # Out of those cells, find the one that is closest to the
                    # damaged area
                    best_cell, _ = closest_nodes(available_cells,
                                                 [self.hub.recent])

                    # Add that cell to the hub cluster
                    self.hub.add(best_cell)

                    logger.debug("ROUND %d: Added %s to %s", r, best_cell,
                                 self.hub)

                self.update_anchors()

            else:

                # In this case, the cluster with the lowest energy requirements
                # is one of the non-hub clusters.

                best_cell = None

                # Find the VC that corresponds to the current cluster
                vci = next(vc for vc in self.virtual_clusters if
                           vc.cluster_id == c_least.cluster_id)

                # Get a list of the cells that have not yet been added to a
                # cluster
                candidates = [c for c in vci.cells if c.cluster_id == -1]

                if candidates:

                    # Find the cell that is closest to the cluster's recent
                    # cell
                    best_cell, _ = closest_nodes(candidates, [c_least.recent])

                else:
                    for i in range(1, max(self.grid.cols, self.grid.rows) + 1):
                        recent = c_least.recent
                        nbrs = self.grid.cell_neighbors(recent, radius=i)

                        for nbr in nbrs:
                            # filter out cells that are not part of a virtual
                            # cluster
                            if nbr.virtual_cluster_id == -1:
                                continue

                            # filter out cells that are not in neighboring VCs
                            dist = abs(nbr.virtual_cluster_id - vci.cluster_id)
                            if dist != 1:
                                continue

                            # if the cell we find is already clustered, we are
                            # done working on this cluster
                            if nbr.cluster_id != -1:
                                c_least.completed = True
                                break

                            best_cell = nbr
                            break

                        if best_cell or c_least.completed:
                            break

                if best_cell:
                    logger.debug("ROUND %d: Added %s to %s", r, best_cell,
                                 c_least)
                    c_least.add(best_cell)

                else:
                    c_least.completed = True
                    logger.debug(
                        "ROUND %d: No best cell found. Marking %s completed",
                        r, c_least)

    def total_cluster_energy(self, c):
        energy = self.energy_model.total_energy(c.cluster_id)
        logger.debug("%s requires %s to traverse.", c, energy)
        return energy

    def highest_energy_cluster(self, include_hub=True):
        all_clusters = list(self.clusters)
        if include_hub:
            all_clusters.append(self.hub)
        highest = max(all_clusters, key=lambda x: self.total_cluster_energy(x))
        return highest

    def lowest_energy_cluster(self):
        all_clusters = self.clusters + [self.hub]
        lowest = min(all_clusters, key=lambda x: self.total_cluster_energy(x))
        return lowest

    def energy_balance(self):
        all_clusters = self.clusters + [self.hub]

        energy = [self.total_cluster_energy(c) for c in all_clusters]
        if self.ec_is_large or self.em_is_large:
            energy.append(0.)

        balance = np.std(energy)
        return balance

    def update_anchors(self, custom=None):

        if custom:
            clusters = custom
        else:
            clusters = self.clusters

        if not self.hub.cells:
            for clust in clusters:
                clust.anchor = None
        else:
            for clust in clusters:
                if not clust.cells:
                    continue

                # Find node in the hub that is closest to one in the cluster
                _, anchor = closest_nodes(clust, self.hub)
                clust.anchor = anchor

    def optimization(self):

        for r in range(101):

            logger.debug("Starting round %d of optimization", r)

            if r > 100:
                raise FlowerError("Optimization got lost")

            balance = self.energy_balance()
            c_least = self.lowest_energy_cluster()
            c_most = self.highest_energy_cluster()

            if self.hub == c_least:
                _, c_in = closest_nodes([c_most.anchor], c_most)

                c_most.remove(c_in)
                self.hub.add(c_in)

                # check the effects and revert if necessary
                self.update_anchors()
                new_balance = self.energy_balance()
                logger.debug("Completed %d rounds of 2b", r)

                # if this round didn't reduce stdev, then revert the changes
                # and exit the loop
                if new_balance >= balance:
                    self.hub.remove(c_in)
                    c_most.add(c_in)
                    self.update_anchors()
                    break

            elif self.hub == c_most:
                # shrink c_most
                c_out = c_least.anchor

                if len(self.hub.cells) > 1:
                    self.hub.remove(c_out)

                c_least.add(c_out)

                # check the effects and revert if necessary
                self.update_anchors()
                new_balance = self.energy_balance()
                logger.debug("Completed %d rounds of 2b", r)

                # if this round didn't reduce the energy balance, then revert
                # the changes and exit the loop.
                if new_balance >= balance:
                    c_least.remove(c_out)
                    self.hub.add(c_out)
                    self.update_anchors()
                    break

            else:
                # shrink c_most
                _, c_in = closest_nodes([c_most.anchor], c_most)

                c_most.remove(c_in)
                self.hub.add(c_in)

                # grow c_least
                c_out, _ = closest_nodes(self.hub, [c_least.anchor])
                self.hub.remove(c_out)
                c_least.add(c_out)

                # check the effects and revert if necessary
                self.update_anchors()
                new_balance = self.energy_balance()
                logger.debug("Completed %d rounds of 2b", r)

                # if this round didn't reduce stdev, then revert the changes
                # and exit the loop
                if new_balance >= balance:
                    c_least.remove(c_out)
                    self.hub.add(c_out)

                    self.hub.remove(c_in)
                    c_most.add(c_in)

                    self.update_anchors()
                    break

    def optimize_large_ec(self):

        for r in range(101):
            logger.debug("Starting round %d of Ec >> Em", r)

            if r > 100:
                raise FlowerError("Optimization got lost")

            balance = self.energy_balance()
            logger.debug("Current energy balance is %f", balance)

            c_most = self.highest_energy_cluster(include_hub=False)

            # get the neighbors of c_most
            neighbors = [
                c for c in self.clusters if
                (abs(c.cluster_id - c_most.cluster_id) == 1) or
                (abs(
                    c.cluster_id - c_most.cluster_id) == self.env.mdc_count - 2)]

            assert (len(neighbors) <= 2) and (len(neighbors) > 0)

            # find the minimum energy neighbor
            neighbor = min(neighbors,
                           key=lambda x: self.total_cluster_energy(x))

            # find the cell in c_most nearest the neighbor
            c_out, _ = closest_nodes(c_most, neighbor)

            c_most.remove(c_out)
            neighbor.add(c_out)

            # emulate a do ... while loop
            stdev_new = self.energy_balance()
            logger.debug("Completed %d rounds of Ec >> Em", r + 1)

            # if this round didn't reduce balance, then revert the changes and
            # exit the loop
            if stdev_new >= balance:
                neighbor.remove(c_out)
                c_most.add(c_out)
                break

    def compute_paths(self):
        self.find_cells()
        self.create_virtual_clusters()

        # Check for the case where Em >> Ec
        clusters = list()
        for vc in self.virtual_clusters:
            cluster = FlowerCluster(self.env)
            cluster.cluster_id = vc.cluster_id
            for cell in vc.cells:
                cluster.add(cell)
            clusters.append(cluster)

        self.update_anchors(clusters)

        e_c = np.sum([self.energy_model.total_comms_energy(cluster)
                      for cluster in clusters])  # * pq.J

        e_m = np.sum([self.energy_model.total_movement_energy(cluster)
                      for cluster in clusters])  # * pq.J

        logger.debug("Em is %s", e_m)
        logger.debug("Ec is %s", e_c)

        if much_greater_than(e_m, e_c):
            logger.debug("Em >> Ec, running special case")
            self.em_is_large = True
            self.clusters = clusters
            self.update_anchors()
            return self

        elif much_greater_than(e_c, e_m):
            logger.debug("Ec >> Em, running special case")
            self.ec_is_large = True
            self.clusters = clusters
            self.update_anchors()
            self.optimize_large_ec()

        else:
            logger.debug("Proceeding with standard optimization")
            self.greedy_expansion()
            self.optimization()

        # self.greedy_expansion()
        # self.optimization()

        return self

    def run(self):
        sim = self.compute_paths()
        runner = flower_runner.FLOWERRunner(sim, self.env)

        logger.debug("Maximum comms delay: {}".format(
            runner.maximum_communication_delay()))
        logger.debug("Energy balance: {}".format(runner.energy_balance()))
        logger.debug("Average energy: {}".format(runner.average_energy()))
        logger.debug("Max buffer size: {}".format(runner.max_buffer_size()))
        return runner


def main():
    env = Environment()

    import time
    seed = int(time.time())

    # General testing ...
    # seed = 1488683682
    env.segment_count = 30
    env.mdc_count = 9
    env.isdva = 64
    env.comms_range = 100

    logger.debug("Random seed is %s", seed)
    np.random.seed(seed)
    start = time.time()
    sim = FLOWER(env)
    sim.run()
    finish = time.time()
    delta = finish - start
    logger.debug("Run time: %f seconds", delta)
    sim.show_state()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('flower_sim')
    main()
