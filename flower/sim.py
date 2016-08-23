"""Main FLOWER simulation logic"""

import logging
import math
import random

import matplotlib.pyplot as plt

from flower import cluster
from flower import constants
from flower import grid
from flower import point
from flower import segment

logging.basicConfig(level=logging.DEBUG)


def much_greater_than(a, b, magnitude=10):
    c = a / b
    result = c > magnitude
    return result


class Simulation(object):
    def __init__(self):

        self.segments = list()
        self.grid = grid.Grid(1700, 1100)
        self.segment_cover = list()
        self.damaged = self.grid.center()
        self.virtual_clusters = list()
        self.mechanical_energy = 0
        self.communication_energy = 0
        self.ISDVA = 10.0 * 1024 * 1024
        self.ISDVSD = 2.0
        self.mobile_nodes = list()
        self.central_cluster = None
        self.central_virtual_cluster = None
        self.clusters = list()
        self.mdc_k = None

    def show_state(self):
        # show all segments
        plot(self.segments, 'rx')

        # show all cells
        plot(self.segment_cover, 'bo')
        scatter(self.segment_cover, constants.COMMUNICATION_RANGE)

        if self.clusters:
            # show all clusters
            plot(self.clusters, 'bx')

            # show the MDC tours
            for vc in self.clusters:
                plot(vc.tour(), 'g')

            plot(self.central_cluster.tour(), 'r')

        elif self.virtual_clusters:
            # show all clusters
            plot(self.virtual_clusters, 'bx')

            # show the MDC tours
            for vc in self.virtual_clusters:
                plot(vc.tour(), 'g')

            plot(self.central_virtual_cluster.tour(), 'r')

        plot([self.damaged], 'go')

        plt.show()

    def init_segments(self):

        while len(self.segments) < constants.SEGMENT_COUNT:
            x_pos = random.random() * self.grid.width
            y_pos = random.random() * self.grid.hieght

            dist_from_center = (point.Vec2(x_pos, y_pos) - self.damaged).length()
            if dist_from_center < constants.DAMAGE_RADIUS:
                continue

            seg = segment.Segment(x_pos, y_pos)
            self.segments.append(seg)

        # Initialize the data for each segment
        segment.initialize_traffic(self.segments, self.ISDVA, self.ISDVSD)

    def init_cells(self):

        for cell in self.grid.cells():

            # Find all segments within range of the cell
            for seg in self.segments:
                distance = cell.distance(seg)
                if distance < constants.COMMUNICATION_RANGE:
                    cell.segments.append(seg)

            # Compute the cell's access as simply the length of its
            # set of segments.
            cell.access = len(cell.segments)

            # Calculate the cell's proximity as it's cell distance from
            # the center of the "damaged area."
            cell.proximity = cell.cell_distance(self.damaged)

        # Calculate the number of one-hop segments within range of each cell
        for cell in self.grid.cells():
            segments = set()
            for nbr in cell.neighbors:
                segments = set.union(segments, nbr.segments)

            cell.signal_hop_count = len(segments)

        # Calculate the set cover over the segments
        segment_cover = set()
        cell_cover = set()

        cells = list(self.grid.cells())

        while segment_cover != set(self.segments):

            candidate = None
            for cell in cells:
                if cell.access == 0:
                    continue

                if not candidate:
                    candidate = cell

                if len(segment_cover) == 0:
                    break

                pot_cell_union = len(segment_cover.union(cell.segments))
                pot_candidate_union = len(segment_cover.union(candidate.segments))

                if pot_candidate_union < pot_cell_union:
                    candidate = cell
                    continue

                elif pot_candidate_union == pot_cell_union:

                    if candidate.access < cell.access:
                        candidate = cell
                        continue

                    if candidate.signal_hop_count < cell.signal_hop_count:
                        candidate = cell
                        continue

                    if candidate.proximity > cell.proximity:
                        candidate = cell
                        continue

            segment_cover.update(candidate.segments)
            cell_cover.add(candidate)

        # Initialized!!
        logging.info("Length of cover: %d", len(cell_cover))

        self.segment_cover = cell_cover

    def phase_one(self):

        vcs = list()

        # Get the central cell of the damaged area
        central_cell = self.damaged

        # Create a virtual cluster containing only the central cell
        vck = cluster.VirtualCluster(central_cell)
        vck.cells = [central_cell]
        central_cell.virtual_cluster_id = constants.MDC_COUNT
        vck.virtual_cluster_id = constants.MDC_COUNT

        # Create new a virtual cluster for each segment
        for cell in self.segment_cover:
            vc = cluster.VirtualCluster(central_cell)
            vc.cells = [cell]
            vcs.append(vc)

        # Combine the clusters until we have MDC_COUNT - 1 non-central, virtual
        # clusters
        while len(vcs) >= constants.MDC_COUNT:
            logging.info("Current VCs: %r", vcs)
            vcs = combine_vcs(vcs, vck)

        # Sort the VCs in polar order and assign an id
        sorted_vcs = point.sort_polar(vcs)
        for i, vc in enumerate(sorted_vcs, start=1):
            vc.virtual_cluster_id = i

            # Assign the virtual cluster ID to each cell in the VC
            for cell in vc.cells:
                cell.virtual_cluster_id = i

        for vc in sorted_vcs:
            for cell in vc.cells:
                logging.info("Cell %r is in VC %d", cell, cell.virtual_cluster_id)

        self.virtual_clusters = sorted_vcs
        self.central_virtual_cluster = vck

    def compute_total_energy(self, clusters):
        for c in clusters:
            self.mechanical_energy += c.motion_energy()
            self.communication_energy += c.communication_energy()

        logging.info("Total motion energy: %f", self.mechanical_energy)
        logging.info("Total communication energy: %f", self.communication_energy)

    def handle_special_cases(self):
        pass

    def recompute_anchors(self):
        for c in self.clusters:
            c.update_anchor(self.central_cluster)

    def phase_two(self):
        self.compute_total_energy(self.virtual_clusters + [self.central_virtual_cluster])

        if much_greater_than(self.mechanical_energy, self.communication_energy):
            self.handle_special_cases()
        elif much_greater_than(self.communication_energy, self.mechanical_energy):
            self.handle_special_cases()

        self.central_cluster = cluster.Cluster(self.damaged)
        self.central_cluster.cells = self.central_virtual_cluster.cells
        self.central_cluster.cluster_id = self.central_virtual_cluster.virtual_cluster_id
        self.damaged.cluster_id = self.central_cluster.cluster_id

        for vc in self.virtual_clusters:
            c = cluster.Cluster(self.damaged)
            crt = min(vc.cells, key=lambda x: x.cell_distance(self.damaged))
            c.cells = [crt]
            c.cluster_id = vc.virtual_cluster_id
            self.clusters.append(c)

        r = 0
        cover_set = list(self.segment_cover)
        while any(not c.completed for c in self.clusters):

            r += 1

            c_least = None
            candidates = self.clusters + [self.central_cluster]
            while not c_least:
                c_least = min(candidates, key=lambda x: x.total_energy())
                if c_least.completed:
                    candidates.remove(c_least)
                    c_least = None
                    continue

            if c_least == self.central_cluster:
                if c_least.cells == [self.damaged]:
                    c_nearest = min(cover_set, key=lambda x: x.proximity)
                    self.central_cluster.cells = [c_nearest]
                    self.central_cluster._central_cell = c_nearest
                    cover_set.remove(c_nearest)
                    c_nearest.cluster_id = c_least.cluster_id
                    logging.info("ROUND %d: Moved central cluster to %r", r, c_nearest)
                else:
                    best_cell = min(cover_set, key=lambda x: x.cell_distance(c_least.recent()))
                    self.central_cluster.add(best_cell)
                    cover_set.remove(best_cell)
                    logging.info("ROUND %d: Added %r to central cluster", r, best_cell)
                self.recompute_anchors()
            else:
                if c_least.completed:
                    logging.info("ROUND %d: Cluster %d completed", r, c_least.cluster_id)
                    continue

                best_cell = None

                index = self.clusters.index(c_least)
                vci = next(i for i in self.virtual_clusters if i.virtual_cluster_id == index + 1)

                if any(c.cluster_id == constants.NOT_CLUSTERED for c in vci.cells):
                    unclustered_cells = [c for c in vci.cells if c.cluster_id == constants.NOT_CLUSTERED]
                    best_cell = min(unclustered_cells, key=lambda x: x.cell_distance(c_least.recent()))
                else:

                    for i in range(1, max(self.grid.cols, self.grid.rows) + 1):
                        recent = c_least.recent()
                        nbrs = self.grid.cell_neighbors(recent.row, recent.col, radius=i)

                        for nbr in nbrs:
                            if nbr.virtual_cluster_id == constants.NOT_CLUSTERED:
                                continue

                            if abs(nbr.virtual_cluster_id - vci.virtual_cluster_id) != 1:
                                continue

                            if nbr.cluster_id != constants.NOT_CLUSTERED:
                                c_least.completed = True
                                break

                            best_cell = nbr
                            break

                if best_cell:
                    logging.info("ROUND %d: Added %r to cluster %d", r, best_cell, c_least.cluster_id)
                    c_least.add(best_cell)
                    cover_set.remove(best_cell)

                    if not cover_set:
                        logging.info("ROUND %d: Marking cluster %d completed", r, c_least.cluster_id)
                        c_least.complete = True

                else:
                    c_least.completed = True
                    logging.info("ROUND %d: No best cell found. Marking cluster %d completed", r, c_least.cluster_id)

                if not cover_set:
                    break

    def phase_two_b(self):

        stdev = pstdev([c.total_energy() for c in self.clusters])

        c_least = min(self.clusters, key=lambda x: x.total_energy())
        c_most = max(self.clusters, key=lambda x: x.total_energy())

        r = 0
        while True:
            if self.central_cluster == c_least:
                # grow c_least
                c_out = min(self.central_cluster.cells, key=lambda x: x.cell_distance(c_least.anchor))
                c_least.add(c_out)
                self.central_cluster.remove(c_out)

                self.recompute_anchors()
                [c.update() for c in self.clusters]

                # emulate a do ... while loop
                stdev_new = pstdev([c.total_energy() for c in self.clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)
                if stdev_new >= stdev:
                    c_least.remove(c_out)
                    self.central_cluster.add(c_out)
                    break

            elif self.central_cluster == c_most:
                # shrink c_most
                c_in = min(c_most.cells, key=lambda x: x.cell_distance(c_most.anchor))
                c_most.remove(c_in)
                self.central_cluster.add(c_in)

                self.recompute_anchors()
                [c.update() for c in self.clusters]

                # emulate a do ... while loop
                stdev_new = pstdev([c.total_energy() for c in self.clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)
                if stdev_new >= stdev:
                    c_most.add(c_in)
                    self.central_cluster.remove(c_in)
                    break

            else:
                # shrink c_most
                c_in = min(c_most.cells, key=lambda x: x.cell_distance(c_most.anchor))
                c_most.remove(c_in)
                self.central_cluster.add(c_in)

                # grow c_least
                c_out = min(self.central_cluster.cells, key=lambda x: x.cell_distance(c_least.anchor))
                c_least.add(c_out)
                self.central_cluster.remove(c_out)

                self.recompute_anchors()
                [c.update() for c in self.clusters]

                # emulate a do ... while loop
                stdev_new = pstdev([c.total_energy() for c in self.clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)
                if stdev_new >= stdev:
                    c_most.add(c_in)
                    self.central_cluster.remove(c_in)

                    c_least.remove(c_out)
                    self.central_cluster.add(c_out)
                    break


def pstdev(data):
    mean = math.fsum(data) / len(data)
    new_data = [math.pow(d - mean, 2) for d in data]
    variance = math.fsum(new_data) / len(new_data)
    stdev = math.sqrt(variance)
    return stdev


def combine_vcs(vcs, center):
    index = 0
    decorated = list()
    for vci in vcs:
        for vcj in vcs[vcs.index(vci) + 1:]:
            combination_cost = (vci + vcj + center).tour_length - (vci + center).tour_length
            decorated.append((combination_cost, index, vci, vcj))
            index += 1

    decorated.sort()
    cost, _, vci, vcj = decorated[0]
    logging.info("Combining %s and %s (%f)", vci, vcj, cost)

    new_vcs = list(vcs)
    new_vc = vci + vcj
    new_vcs.remove(vci)
    new_vcs.remove(vcj)
    new_vcs.append(new_vc)
    return new_vcs


def plot(points, *args, **kwargs):
    x = [p.x for p in points]
    y = [p.y for p in points]
    plt.plot(x, y, *args, **kwargs)


def scatter(points, radius):
    plot(points, 'ro')

    axes = plt.axes()
    for p in points:
        circle = plt.Circle((p.x, p.y), radius=radius, alpha=0.5)
        axes.add_patch(circle)

    plt.axis('scaled')


def main():
    sim = Simulation()
    sim.init_segments()
    sim.init_cells()

    sim.phase_one()
    sim.show_state()

    sim.phase_two()
    sim.show_state()

    sim.phase_two_b()

    # collection = list()
    # for c in sim.clusters:
    #     for cell in c.cells:
    #         try:
    #             assert(cell not in collection)
    #         except AssertionError:
    #             logging.debug("Cell %r is a duplicate", cell)
    #             raise
    #     collection += c.cells

    sim.show_state()


if __name__ == '__main__':
    main()
