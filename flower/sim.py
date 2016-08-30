"""Main FLOWER simulation logic"""

import collections
import itertools
import logging
import random
import statistics

import matplotlib.pyplot as plt

from flower import cluster
from flower import constants
from flower import grid
from flower import point
from flower import segment

logging.basicConfig(level=logging.DEBUG)


def much_greater_than(em, ec, r=0.2, r_prime=0.2):
    if em / ec > 1 / r:
        logging.info("Em >> Ec (%f)", em / ec)
        return True

    if ec / em > 1 / r_prime:
        logging.info("Ec >> Em (%f)", ec / em)
        return True

    return False


class Simulation(object):
    def __init__(self):

        self.segments = list()
        self.grid = grid.Grid(1200, 1200)
        self.segment_cover = list()
        self.damaged = self.grid.center()
        self.virtual_clusters = list()
        self.mechanical_energy = 0
        self.communication_energy = 0
        self.ISDVA = 45.0 * 1024 * 1024
        self.ISDVSD = 0.0
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
        vck = cluster.VirtualCluster()
        vck.cells = [central_cell]
        central_cell.virtual_cluster_id = constants.MDC_COUNT
        vck.virtual_cluster_id = constants.MDC_COUNT

        # Create new a virtual cluster for each segment
        for cell in self.segment_cover:
            vc = cluster.VirtualCluster()
            vc.cells = [central_cell, cell]
            vc.calculate_tour()
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
        logging.info("Hit special case!")

    def phase_two_a(self):
        self.compute_total_energy(self.virtual_clusters + [self.central_virtual_cluster])

        if much_greater_than(self.mechanical_energy, self.communication_energy):
            self.handle_special_cases()

        self.central_cluster = cluster.Cluster()
        self.central_cluster.cells = self.central_virtual_cluster.cells
        self.central_cluster.cluster_id = self.central_virtual_cluster.virtual_cluster_id
        self.central_cluster.recent = self.damaged
        self.central_cluster.calculate_tour()

        for vc in self.virtual_clusters:
            c = cluster.Cluster()
            c.cluster_id = vc.virtual_cluster_id
            c.central_cluster = self.central_cluster

            candidates = [c for c in vc.cells if c != self.damaged]
            c_rt = min(candidates, key=lambda x: x.cell_distance(self.damaged))
            c_rt.cluster_id = c.cluster_id
            c.cells = [c_rt]
            c.recent = c_rt
            c.calculate_tour()
            self.clusters.append(c)

        r = 0
        while any(not c.completed for c in self.clusters):

            r += 1

            [c.calculate_tour() for c in self.clusters + [self.central_cluster]]

            candidates = list(self.clusters) + [self.central_cluster]
            candidates = [c for c in candidates if not c.completed]
            c_least = min(candidates, key=lambda x: x.total_energy())

            cells = [s for s in self.segment_cover if s.cluster_id == constants.NOT_CLUSTERED]

            if not cells:
                c_least.completed = True
                logging.info("All cells assigned. Marking %s as completed", c_least)
                continue

            if c_least == self.central_cluster:
                if c_least.cells == [self.damaged]:
                    # find the nearest cell to cg and move Ck to it
                    best_cell = min(cells, key=lambda x: x.proximity)
                    self.central_cluster.cells = [best_cell]
                    self.damaged.cluster_id = constants.NOT_CLUSTERED
                    logging.info("ROUND %d: Moved central cluster to %r", r, best_cell)
                else:
                    best_cell = min(cells, key=lambda x: x.cell_distance(self.central_cluster.recent))
                    self.central_cluster.add(best_cell)
                    logging.info("ROUND %d: Added %r to central cluster", r, best_cell)

                best_cell.cluster_id = self.central_cluster.cluster_id
                c_least.recent = best_cell
                [c.update_anchor() for c in self.clusters]
            else:

                best_cell = None

                index = self.clusters.index(c_least)
                vci = next(i for i in self.virtual_clusters if i.virtual_cluster_id == index + 1)

                candidates = [c for c in vci.cells if c.cluster_id == constants.NOT_CLUSTERED and c != self.damaged]
                if candidates:
                    best_cell = min(candidates, key=lambda x: x.cell_distance(c_least.recent))

                else:
                    for i in range(1, max(self.grid.cols, self.grid.rows) + 1):
                        recent = c_least.recent
                        nbrs = self.grid.cell_neighbors(recent.row, recent.col, radius=i)

                        for nbr in nbrs:
                            # filter out cells that are not part of a virtual cluster
                            if nbr.virtual_cluster_id == constants.NOT_CLUSTERED:
                                continue

                            # filter out cells that are not in neighboring VCs
                            if abs(nbr.virtual_cluster_id - vci.virtual_cluster_id) != 1:
                                continue

                            # if the cell we find is already clustered, we are done working
                            # on this cluster
                            if nbr.cluster_id != constants.NOT_CLUSTERED:
                                c_least.completed = True
                                break

                            best_cell = nbr
                            break

                        if best_cell:
                            break

                if best_cell:
                    logging.info("ROUND %d: Added %r to %s", r, best_cell, c_least)
                    c_least.add(best_cell)
                    c_least.recent = best_cell
                    best_cell.cluster_id = c_least.cluster_id

                else:
                    c_least.completed = True
                    logging.info("ROUND %d: No best cell found. Marking %s completed", r, c_least)

                [c.calculate_tour() for c in self.clusters + [self.central_cluster]]

    def phase_two_b(self):

        stdev = statistics.pstdev([c.total_energy() for c in self.clusters])

        c_least = min(self.clusters, key=lambda x: x.total_energy())
        c_most = max(self.clusters, key=lambda x: x.total_energy())

        r = 0
        while True:
            if self.central_cluster == c_least:
                _, c_in = closest_cells(self.central_cluster, c_most)

                c_most.remove(c_in)
                self.central_cluster.add(c_in)
                c_in.cluster_id = self.central_cluster.cluster_id

                [c.update_anchor() for c in self.clusters]
                [c.calculate_tour() for c in self.clusters]

                # emulate a do ... while loop
                stdev_new = statistics.pstdev([c.total_energy() for c in self.clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)

                # if this round didn't reduce stdev, then revert the changes and exit the loop
                if stdev_new >= stdev:
                    self.central_cluster.remove(c_in)
                    c_most.add(c_in)
                    c_in.cluster_id = c_most.cluster_id
                    break

            elif self.central_cluster == c_most:
                # shrink c_most
                c_out, _ = closest_cells(self.central_cluster, c_least)

                self.central_cluster.remove(c_out)
                c_least.add(c_out)
                c_out.cluster_id = c_least.cluster_id

                [c.update_anchor() for c in self.clusters]
                [c.calculate_tour() for c in self.clusters]


                # emulate a do ... while loop
                stdev_new = statistics.pstdev([c.total_energy() for c in self.clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)

                # if this round didn't reduce stdev, then revert the changes and exit the loop
                if stdev_new >= stdev:
                    c_least.remove(c_out)
                    self.central_cluster.add(c_out)
                    c_out.cluster_id = self.central_cluster.cluster_id
                    break

            else:
                # grow c_least
                c_out, _ = closest_cells(self.central_cluster, c_least)
                self.central_cluster.remove(c_out)
                c_least.add(c_out)
                c_out.cluster_id = c_least.cluster_id

                # shrink c_most
                _, c_in = closest_cells(self.central_cluster, c_most)
                c_most.remove(c_in)
                self.central_cluster.add(c_in)
                c_in.cluster_id = self.central_cluster.cluster_id

                [c.update_anchor() for c in self.clusters]
                [c.calculate_tour() for c in self.clusters]

                # emulate a do ... while loop
                stdev_new = statistics.pstdev([c.total_energy() for c in self.clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)

                # if this round didn't reduce stdev, then revert the changes and exit the loop
                if stdev_new >= stdev:
                    c_least.remove(c_out)
                    self.central_cluster.add(c_out)
                    c_out.cluster_id = self.central_cluster.cluster_id

                    self.central_cluster.remove(c_in)
                    c_most.add(c_in)
                    c_in.cluster_id = c_most.cluster_id

                    break

        [c.update_anchor() for c in self.clusters]
        [c.calculate_tour() for c in self.clusters]


def combine_vcs(vcs, center):
    index = 0
    decorated = list()
    for vci in vcs:
        for vcj in vcs[vcs.index(vci) + 1:]:
            temp_vc_1 = vci + vcj + center
            temp_vc_1.calculate_tour()

            temp_vc_2 = vci + center
            temp_vc_2.calculate_tour()

            combination_cost = temp_vc_1.tour_length - temp_vc_2.tour_length
            decorated.append((combination_cost, index, vci, vcj))
            index += 1

    decorated.sort()
    cost, _, vci, vcj = decorated[0]
    logging.info("Combining %s and %s (%f)", vci, vcj, cost)

    new_vcs = list(vcs)
    new_vc = vci + vcj
    new_vc.calculate_tour()

    new_vcs.remove(vci)
    new_vcs.remove(vcj)
    new_vcs.append(new_vc)
    return new_vcs


def closest_cells(cluster_1, cluster_2):
    pairs = itertools.product(cluster_1.cells, cluster_2.cells)
    decorated = [(cell_1.cell_distance(cell_2), i, cell_1, cell_2) for i, (cell_1, cell_2) in enumerate(pairs)]
    closest = min(decorated)
    cells = closest[2], closest[3]
    return cells


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

    sim.phase_two_a()
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
