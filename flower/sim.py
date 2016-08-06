"""Main FLOWER simulation logic"""

import logging
import random

import matplotlib.pyplot as plt

import constants
import point
from grid import Grid
from grid import WorldPositionMixin

logging.basicConfig(level=logging.DEBUG)


class Cluster(object):
    def __init__(self):
        self.is_center = False
        self.segments = list()


class VirtualCluster(object):
    def __init__(self, central=False):
        self.is_center = central
        self.cells = list()
        self.vcid = 0

        self._hull = list()
        self._interior = list()

    def calculate_tour(self):
        hull, interior = point.graham_scan(self.cells)

        self._hull = hull
        self._interior = interior

        return self._hull

    def tour_length(self):
        last = self._hull[0]
        distance = 0
        for cell in self._hull[1:]:
            distance += last.distance(cell)
            last = cell

        return distance


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

        self.segment_count = 18
        self.segments = list()
        self.mobile_nodes = list()
        self.trips = list()
        self.data_sets = list()
        self.clusters = list()
        self.center = (0, 0)
        self.grid = Grid(1700, 1100)
        self.cells = list()

    def init_segments(self):

        for _ in range(self.segment_count):
            x_pos = random.random() * self.grid.width
            y_pos = random.random() * self.grid.hieght
            segment = Segment(x_pos, y_pos)
            self.segments.append(segment)

            logging.info("Created segment: %s", segment)

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
            # Calculate the cell's proximaty as it's cell distance from
            # the center of the "damaged area."
            #
            cell.prox = cell.cell_distance(self.grid.center())

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
        # Get a representation of the cells sorted by access in decending order
        #
        cells = list(self.grid.cells())

        while segment_cover != set(self.segments):
            logging.debug("Current segment cover: %s", segment_cover)

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

        # for cell in cell_cover:
        #    print cell.grid_pos.row, cell.grid_pos.col, cell.access

        x = list()
        y = list()
        for segment in self.segments:
            x.append(segment.x)
            y.append(segment.y)

        plt.plot(x, y, 'bo')

        x = list()
        y = list()
        for cell in cell_cover:
            x.append(cell.x)
            y.append(cell.y)

        plt.plot(x, y, 'ro')

        self.cells = cell_cover

    def phase_one(self):

        vcs = list()
        central_cluster = VirtualCluster(central=True)
        central_cluster.cells = [self.grid.center()]
        vcs.append(central_cluster)

        for cell in self.cells:
            vc = VirtualCluster()
            vc.cells.append(cell)
            vcs.append(vc)

        for vc in vcs:
            logging.info("Tour: %s", vc.calculate_tour())
            logging.info("Tour length: %f", vc.tour_length())


def main():
    sim = Simulation()
    sim.init_segments()
    sim.init_cells()
    sim.phase_one()
    plt.show()


if __name__ == '__main__':
    main()
