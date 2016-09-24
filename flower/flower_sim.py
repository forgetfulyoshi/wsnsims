"""Main FLOWER simulation logic"""

import logging
import random
import statistics

import matplotlib.pyplot as plt

from flower import cluster
from flower import constants
from flower import flower_runner
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


class FlowerSim(object):
    def __init__(self):

        self.grid = grid.Grid(1200, 1200)
        self.damaged = self.grid.center()
        self.segments = list()
        self.cells = list()
        self.virtual_clusters = list()

        self.clusters = list()
        self.mechanical_energy = 0
        self.communication_energy = 0

        self.ISDVA = 45.0
        self.ISDVSD = 0.0

        # Create a virtual segment to represent the center of the damaged
        # area
        virtual_center_cell = self.damaged

        self.virtual_hub = cluster.FlowerVirtualHub()
        self.virtual_hub.add(virtual_center_cell)
        self.virtual_hub.virtual_cluster_id = constants.MDC_COUNT
        virtual_center_cell.virtual_cluster_id = constants.MDC_COUNT

        self.hub = cluster.FlowerHub()
        self.hub.add(virtual_center_cell)
        self.hub.recent = virtual_center_cell
        self.hub.cluster_id = constants.MDC_COUNT
        virtual_center_cell.cluster_id = constants.MDC_COUNT

        self.mdc_energy = 1000  # Joules
        self.mdc_speed = 0.1  # meters / second
        self.transmission_rate = 0.1  # Mbps

    def show_state(self):
        # show all segments
        plot(self.segments, 'rx')

        # show all cells
        plot(self.cells, 'bo')
        scatter(self.cells, constants.COMMUNICATION_RANGE)

        if self.clusters:
            # show all clusters
            plot(self.clusters, 'bx')

            # show the MDC tours
            for vc in self.clusters:
                plot(vc.tour(), 'g')

            plot(self.hub.tour(), 'r')

        elif self.virtual_clusters:
            # show all clusters
            plot(self.virtual_clusters, 'bx')

            # show the MDC tours
            for vc in self.virtual_clusters:
                plot(vc.tour(), 'g')

            plot(self.virtual_hub.tour(), 'r')

        plot([self.damaged], 'go')

        plt.show()

    def init_segments(self):

        while len(self.segments) < constants.SEGMENT_COUNT:
            x_pos = random.random() * self.grid.width
            y_pos = random.random() * self.grid.hieght

            dist_from_center = (point.Vec2(x_pos, y_pos) - self.damaged).length()
            if dist_from_center < constants.DAMAGE_RADIUS:
                continue

            seg = segment.FlowerSegment(x_pos, y_pos)
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

        # For future lookups, set a reference from each segment to its cell
        for cell in cell_cover:
            for seg in cell.segments:
                seg.cell = cell

        self.cells = cell_cover

    def create_virtual_clusters(self):

        virtual_clusters = list()
        for cell in self.cells:
            c = cluster.FlowerVirtualCluster()
            c.central_cluster = self.virtual_hub
            c.add(cell)
            c.calculate_tour()
            virtual_clusters.append(c)

        # Combine the clusters until we have MDC_COUNT - 1 non-central, virtual
        # clusters
        while len(virtual_clusters) >= constants.MDC_COUNT:
            logging.info("Current VCs: %r", virtual_clusters)
            virtual_clusters = cluster.combine_clusters(virtual_clusters, self.virtual_hub)

        # Sort the VCs in polar order and assign an id
        sorted_vcs = point.sort_polar(virtual_clusters)
        for i, vc in enumerate(sorted_vcs, start=1):
            vc.virtual_cluster_id = i

            # Assign the virtual cluster ID to each cell in the VC
            for cell in vc.cells:
                cell.virtual_cluster_id = i

        for vc in sorted_vcs:
            for cell in vc.cells:
                logging.info("%s is in %s", cell, vc)

        self.virtual_clusters = sorted_vcs

    def compute_total_energy(self, clusters):
        for c in clusters:
            self.mechanical_energy += c.motion_energy()
            other_segments = [s for s in self.segments if s.cluster != c]
            self.communication_energy += c.communication_energy(other_segments)

        logging.info("Total motion energy: %f", self.mechanical_energy)
        logging.info("Total communication energy: %f", self.communication_energy)

    @staticmethod
    def handle_special_cases():
        logging.info("Hit special case!")

    def greedy_expansion(self):

        # Check for special cases (Em >> Ec or Ec >> Em)
        self.compute_total_energy(self.virtual_clusters + [self.virtual_hub])

        if much_greater_than(self.mechanical_energy, self.communication_energy):
            self.handle_special_cases()

        # First round (initial cell setup and energy calculation)

        for vc in self.virtual_clusters:
            c = cluster.FlowerCluster()
            c.cluster_id = vc.virtual_cluster_id
            c.central_cluster = self.hub

            closest_cell, _ = cluster.closest_nodes(vc, self.hub)
            closest_cell.cluster_id = c.cluster_id

            c.nodes = [closest_cell, self.damaged]
            c.recent = closest_cell
            self.clusters.append(c)

        # Compute the tours for each of the new clusters. This allows us to
        # determine the motion energy needed for an MDC to traverse the cluster.
        # Hub only has one cell though, so we don't need to calculate its tour.
        [c.calculate_tour() for c in self.clusters]

        # Rounds 2 through N
        r = 1
        while any(not c.completed for c in self.clusters):

            r += 1

            # Update the tours for all clusters and the hub cluster
            [c.calculate_tour() for c in self.clusters + [self.hub]]

            # Determine the minimum-cost cluster by first filtering out all
            # non-completed clusters. Then find the the cluster with the lowest
            # total cost.
            candidates = self.clusters + [self.hub]
            candidates = [c for c in candidates if not c.completed]
            c_least = min(candidates, key=lambda x: self.total_cluster_energy(x))

            # In general, only consider cells that have not already been added to a
            # cluster. There is an exception to this when expanding the hub cluster.
            cells = [c for c in self.cells if c.cluster_id == constants.NOT_CLUSTERED]

            # If there are no more cells to assign, then we mark this cluster as "completed"
            if not cells:
                c_least.completed = True
                logging.info("All cells assigned. Marking %s as completed", c_least)
                continue

            if c_least == self.hub:

                # This logic handles the case where the hub cluster is has the fewest energy
                # requirements. Either the cluster will be moved (initialization) or it will
                # be grown.
                #
                # If the hub cluster is still in its original location at the center of the
                # damaged area, we need to move it to an actual cell. If the hub has already
                # been moved, then we expand it by finding the cell nearest to the center of
                # the damaged area, and that itself hasn't already been added to the hub cluster.

                if c_least.cells == [self.damaged]:
                    # Find the nearest cell to the center of the damaged area and move the hub
                    # to it. This is equivalent to finding the cell with the lowest proximity.
                    best_cell = min(cells, key=lambda x: x.proximity)

                    # As the hub only currently has the virtual center cell in it, we
                    # can just "move" the hub to the nearest real cell by replacing the
                    # virtual cell with it.
                    self.hub.nodes = [best_cell]
                    best_cell.cluster = self.hub

                    # Just for proper bookkeeping, reset the virtual cell's ID to NOT_CLUSTERED
                    self.damaged.cluster_id = constants.NOT_CLUSTERED
                    logging.info("ROUND %d: Moved %s to %s", r, self.hub, best_cell)

                else:
                    # Find the set of cells that are not already in the hub cluster
                    available_cells = list(set(self.cells) - set(self.hub.cells))

                    # Out of those cells, find the one that is closest to the damaged area
                    best_cell, _ = cluster.closest_nodes(available_cells, [self.hub.recent])

                    # Add that cell to the hub cluster
                    self.hub.add(best_cell)

                    logging.info("ROUND %d: Added %s to %s", r, best_cell, self.hub)

                # Set the cluster ID for the new cell, mark it as the most recent cell for the hub
                # cluster and update the anchors for all other clusters.
                best_cell.cluster_id = self.hub.cluster_id
                c_least.recent = best_cell
                [c.update_anchor() for c in self.clusters]

            else:

                # In this case, the cluster with the lowest energy requirements is one of the non-hub
                # clusters.

                best_cell = None

                # Find the VC that corresponds to the current cluster
                vci = next(i for i in self.virtual_clusters if i.virtual_cluster_id == c_least.cluster_id)

                # Get a list of the cells that have not yet been added to a cluster
                candidates = [c for c in vci.cells if c.cluster_id == constants.NOT_CLUSTERED]

                if candidates:

                    # Find the cell that is closest to the cluster's recent cell
                    best_cell, _ = cluster.closest_nodes(candidates, [c_least.recent])

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

                        if best_cell or c_least.completed:
                            break

                if best_cell:
                    logging.info("ROUND %d: Added %s to %s", r, best_cell, c_least)
                    c_least.add(best_cell)
                    c_least.recent = best_cell
                    best_cell.cluster_id = c_least.cluster_id

                else:
                    c_least.completed = True
                    logging.info("ROUND %d: No best cell found. Marking %s completed", r, c_least)

                [c.calculate_tour() for c in self.clusters + [self.hub]]

                # [c.update_anchor() for c in self.clusters]

    def total_cluster_energy(self, c):
        other_segments = [s for s in self.segments if s.cluster != c]
        return c.total_energy(other_segments)

    def optimization(self):

        all_clusters = self.clusters + [self.hub]
        stdev = statistics.pstdev([self.total_cluster_energy(c) for c in all_clusters])

        c_least = min(all_clusters, key=lambda x: self.total_cluster_energy(x))
        c_most = max(all_clusters, key=lambda x: self.total_cluster_energy(x))

        r = 0
        while True:
            if self.hub == c_least:
                _, c_in = cluster.closest_nodes([c_most.anchor], c_most)

                c_most.remove(c_in)
                self.hub.add(c_in)
                c_in.cluster_id = self.hub.cluster_id

                [c.update_anchor() for c in self.clusters]
                [c.calculate_tour() for c in all_clusters]

                # emulate a do ... while loop
                stdev_new = statistics.pstdev([self.total_cluster_energy(c) for c in all_clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)

                # if this round didn't reduce stdev, then revert the changes and exit the loop
                if stdev_new >= stdev:
                    self.hub.remove(c_in)
                    c_most.add(c_in)
                    c_in.cluster_id = c_most.cluster_id

                    [c.update_anchor() for c in self.clusters]
                    [c.calculate_tour() for c in all_clusters]
                    break

            elif self.hub == c_most:
                # shrink c_most
                c_out, _ = cluster.closest_nodes(self.hub, [c_least.anchor])

                self.hub.remove(c_out)

                c_least.add(c_out)
                c_out.cluster_id = c_least.cluster_id

                [c.update_anchor() for c in self.clusters]
                [c.calculate_tour() for c in all_clusters]

                # emulate a do ... while loop
                stdev_new = statistics.pstdev([self.total_cluster_energy(c) for c in all_clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)

                # if this round didn't reduce stdev, then revert the changes and exit the loop
                if stdev_new >= stdev:
                    c_least.remove(c_out)
                    self.hub.add(c_out)
                    c_out.cluster_id = self.hub.cluster_id

                    [c.update_anchor() for c in self.clusters]
                    [c.calculate_tour() for c in all_clusters]
                    break

            else:
                # grow c_least
                c_out, _ = cluster.closest_nodes(self.hub, [c_least.anchor])
                self.hub.remove(c_out)
                c_least.add(c_out)
                c_out.cluster_id = c_least.cluster_id

                # shrink c_most
                _, c_in = cluster.closest_nodes([c_most.anchor], c_most)
                c_most.remove(c_in)
                self.hub.add(c_in)
                c_in.cluster_id = self.hub.cluster_id

                [c.update_anchor() for c in self.clusters]
                [c.calculate_tour() for c in all_clusters]

                # emulate a do ... while loop
                stdev_new = statistics.pstdev([self.total_cluster_energy(c) for c in all_clusters])
                r += 1
                logging.info("Completed %d rounds of 2b", r)

                # if this round didn't reduce stdev, then revert the changes and exit the loop
                if stdev_new >= stdev:
                    c_least.remove(c_out)
                    self.hub.add(c_out)
                    c_out.cluster_id = self.hub.cluster_id

                    self.hub.remove(c_in)
                    c_most.add(c_in)
                    c_in.cluster_id = c_most.cluster_id

                    [c.update_anchor() for c in self.clusters]
                    [c.calculate_tour() for c in all_clusters]
                    break

        [c.update_anchor() for c in self.clusters]
        [c.calculate_tour() for c in all_clusters]


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


def compute_paths():
    sim = FlowerSim()
    sim.init_segments()
    sim.init_cells()

    sim.create_virtual_clusters()
    # sim.show_state()

    sim.greedy_expansion()
    # sim.show_state()

    sim.optimization()
    sim.show_state()

    return sim


def main():
    sim = compute_paths()
    flower_runner.run_sim(sim)


if __name__ == '__main__':
    main()
