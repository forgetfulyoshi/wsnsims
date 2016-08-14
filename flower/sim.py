"""Main FLOWER simulation logic"""

import logging
import random

import matplotlib.pyplot as plt

import constants
import point
import tour
from grid import Grid
from grid import WorldPositionMixin

logging.basicConfig(level=logging.DEBUG)


class Cluster(object):
    def __init__(self):
        self.is_center = False
        self.segments = list()


class VirtualCluster(WorldPositionMixin):
    def __init__(self, central_cell):
        super(VirtualCluster, self).__init__()

        self.vcid = 0

        self._cells = list()
        self._tour = list()
        self._tour_length = 0
        self._central_cell = central_cell

    def _calculate_tour(self):
        cells = list(set(self._cells + [self._central_cell]))
        self._tour = tour.find_tour(cells, radius=0, start=self._central_cell)
        self._tour_length = tour.tour_length(self._tour)

    def _calculate_location(self):
        com = tour.centroid(self._cells + [self._central_cell])
        self.x = com.x
        self.y = com.y

    def update(self):
        self._calculate_tour()
        self._calculate_location()

    @property
    def tour_length(self):
        return self._tour_length

    @property
    def cells(self):
        return self._cells

    @cells.setter
    def cells(self, value):
        self._cells = value
        self.update()

    def append(self, *args):
        self._cells.append(args)
        self.update()

    def tour(self):
        return [c.collection_point for c in self._tour]

    def __add__(self, other):
        new_vc = VirtualCluster(self._central_cell)
        new_vc.cells = list(set(self.cells + other.cells))
        return new_vc


class Segment(WorldPositionMixin):
    count = 0

    def __init__(self, x, y):
        super(Segment, self).__init__()
        self.cluster = None
        self.x = x
        self.y = y
        self.segment_id = Segment.count
        Segment.count += 1

    def __eq__(self, other):
        return self.segment_id == other.segment_id

    def __hash__(self):
        return hash(self.segment_id)

    def __str__(self):
        return "SEG %d: (%f, %f)" % (self.segment_id, self.x, self.y)

    def __repr__(self):
        return "SEG %d" % self.segment_id


class Simulation(object):
    def __init__(self):

        self.segments = list()
        self.grid = Grid(1700, 1100)
        self.segment_cover = list()
        self.damaged = self.grid.center()

    def init_segments(self):

        while len(self.segments) < constants.SEGMENT_COUNT:
            x_pos = random.random() * self.grid.width
            y_pos = random.random() * self.grid.hieght

            dist_from_center = (point.Vec2(x_pos, y_pos) - self.damaged).length()
            if dist_from_center < constants.DAMAGE_RADIUS:
                continue

            segment = Segment(x_pos, y_pos)
            self.segments.append(segment)

            # logging.info("Created segment: %s (%f)", segment, dist_from_center)
            plot(self.segments, 'rx')
            scatter([self.damaged], constants.DAMAGE_RADIUS)

    def init_cells(self):

        for cell in self.grid.cells():
            #
            # Find all segments within range of the cell
            #
            for segment in self.segments:
                distance = cell.distance(segment)
                if distance < constants.COMMUNICATION_RANGE:
                    cell.segments.append(segment)

            #
            # Compute the cell's access as simply the length of its
            # set of segments.
            #
            cell.access = len(cell.segments)

            #
            # Calculate the cell's proximity as it's cell distance from
            # the center of the "damaged area."
            #
            cell.prox = cell.cell_distance(self.damaged)

        #
        # Calculate the number of one-hop segments within range of each cell
        #
        for cell in self.grid.cells():
            segments = set()
            for nbr in cell.neighbors:
                segments = set.union(segments, nbr.segments)

            cell.onehop = len(segments)

        segment_cover = set()  # temporary set to track progress 
        cell_cover = set()

        #
        # Get a representation of the cells sorted by access in descending order
        #
        cells = list(self.grid.cells())

        while segment_cover != set(self.segments):
            # logging.debug("Current segment cover: %s", segment_cover)

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

                    if candidate.onehop < cell.onehop:
                        candidate = cell
                        continue

                    if candidate.prox > cell.prox:
                        candidate = cell
                        continue

            segment_cover.update(candidate.segments)
            cell_cover.add(candidate)

        #
        # Initialized!!
        #
        logging.info("Length of cover: %d", len(cell_cover))

        self.segment_cover = cell_cover
        # plot(self.segment_cover, 'bo')

    def phase_one(self):

        vcs = list()
        central_cell = self.damaged
        vck = VirtualCluster(central_cell)
        vck.cells = [central_cell]

        for cell in self.segment_cover:
            vc = VirtualCluster(central_cell)
            vc.cells = [cell]
            vcs.append(vc)

        while len(vcs) > constants.MDC_COUNT:
            logging.info("Current VCs: %r", vcs)
            vcs = combine_vcs(vcs, vck)

        for vc in vcs:
            plot(vc.tour())

        scatter(self.segment_cover, constants.COMMUNICATION_RANGE)
        plot(vcs, 'bx')
        scatter([central_cell], constants.COMMUNICATION_RANGE)
        plt.show()


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
    plt.show()


if __name__ == '__main__':
    main()
