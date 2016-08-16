"""Main FLOWER simulation logic"""

import logging
import random

import matplotlib.pyplot as plt

import cluster
import constants
import grid
import mobile
import point
import segment

logging.basicConfig(level=logging.DEBUG)


class Simulation(object):
    def __init__(self):

        self.segments = list()
        self.grid = grid.Grid(1700, 1100)
        self.segment_cover = list()
        self.damaged = self.grid.center()
        self.virtual_clusters = list()
        self.mechanical_energy = 0
        self.communication_energy = 0
        self.ISDVA = 10.0
        self.ISDVSD = 2.0
        self.mobile_nodes = list()

    def show_state(self):
        # show all segments
        plot(self.segments, 'rx')

        # show all cells
        plot(self.segment_cover, 'bo')
        scatter(self.segment_cover, constants.COMMUNICATION_RANGE)

        # show all virtual clusters
        plot(self.virtual_clusters, 'bx')

        # show the MDC tours
        for vc in self.virtual_clusters:
            plot(vc.tour())

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

                    if candidate.onehop < cell.signal_hop_count:
                        candidate = cell
                        continue

                    if candidate.prox > cell.proximity:
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

        # Add the central VC to the end of the list
        sorted_vcs.append(vck)

        for vc in sorted_vcs:
            for cell in vc.cells:
                logging.info("Cell %r is in VC %d", cell, cell.virtual_cluster_id)

        self.virtual_clusters = sorted_vcs

    def compute_total_energy(self):
        for mdc in self.mobile_nodes:
            self.mechanical_energy += mdc.motion_energy()
            self.communication_energy += mdc.communication_energy()

        logging.info("Total motion energy: %f", self.mechanical_energy)
        logging.info("Total communication energy: %f", self.communication_energy)

    def phase_two(self):

        for vc in self.virtual_clusters:
            mdc = mobile.MDC(vc)
            self.mobile_nodes.append(mdc)

        self.compute_total_energy()

    def update_cluster_anchors(self):
        pass

    def expand_clusters(self):
        pass


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
    sim.phase_two()
    # sim.show_state()


if __name__ == '__main__':
    main()
