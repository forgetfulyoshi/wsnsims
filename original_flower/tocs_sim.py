import logging
import random
import statistics

import matplotlib.pyplot as plt

from original_flower import cluster
from original_flower import grid
from original_flower import params
from original_flower import point
from original_flower import segment
from original_flower import tocs_runner

logger = logging.getLogger(__name__)

MAX_ROUNDS = 100


class ToCS(object):
    def __init__(self):

        self.grid = grid.Grid(2000, 2000)

        self.segments = list()
        self.virtual_center_segment = segment.Segment()
        self.virtual_center_segment.x = self.grid.center().x
        self.virtual_center_segment.y = self.grid.center().y
        self.virtual_center_segment.is_virtual = True

        self.centroid = cluster.ToCSCentroid(self.virtual_center_segment)

        self.isdva = params.ISDVA  # Mb
        self.isdvsd = params.ISDVSD
        self.clusters = list()
        self.mdc_speed = params.MDC_SPEED
        self.transmission_rate = params.TRANSMISSION_RATE

        self.mdc_energy = params.INITIAL_ENERGY
        self.movement_cost = params.MOVEMENT_COST
        self.comms_cost = params.COMMS_COST

    def show_state(self):
        # show all segments
        plot(self.segments, 'bo')

        if self.clusters:
            # show all clusters
            plot(self.clusters, 'bx')

            # show the MDC tours
            for c in self.clusters:
                plot(c.tour_nodes(), 'g')

                if c.rendezvous_point:
                    plot([c.rendezvous_point], 'ro')

            plot([self.centroid], 'ro')
            plot(self.centroid.tour_nodes(), 'r')

        plt.show()

    def set_up(self):

        while len(self.segments) < params.SEGMENT_COUNT:
            x_pos = random.random() * self.grid.width
            y_pos = random.random() * self.grid.hieght

            dist_from_center = (point.Vec2(x_pos, y_pos) - self.virtual_center_segment).length()
            if dist_from_center < params.DAMAGE_RADIUS:
                continue

            seg = segment.Segment(x_pos, y_pos)
            self.segments.append(seg)

            # Initialize the data for each segment
            # segment.initialize_traffic(self.segments, self.ISDVA, self.ISDVSD)

    def create_clusters(self):

        clusters = list()
        for seg in self.segments:
            c = cluster.ToCSCluster()
            c.add(seg)
            c.calculate_tour()
            clusters.append(c)

        while len(clusters) >= params.MDC_COUNT:
            logger.info("Current Clusters: %r", clusters)
            clusters = cluster.combine_clusters(clusters, self.centroid)
            [c.calculate_tour() for c in clusters]

        for i, c in enumerate(clusters, start=1):
            c.cluster_id = i

        self.clusters = clusters

    def find_initial_rendezvous_points(self):

        for c in self.clusters:
            if len(c.segments) == 1:
                rendezvous_point = c.segments[0]

            else:
                decorated = list()
                prev = c.segments[0]
                for i, s in enumerate(c.segments[1:], start=1):
                    dist, pt = point.closest_point(prev, s, self.virtual_center_segment)
                    decorated.append((dist, i, pt))
                    prev = s

                rendezvous_point = min(decorated)[2]

            rendezvous_point -= self.virtual_center_segment
            rendezvous_point.scale(0.5)
            rendezvous_point += self.virtual_center_segment

            # Make sure we can treat this as a "virtual segment"
            rendezvous_point = segment.Segment(rendezvous_point.x, rendezvous_point.y)
            rendezvous_point.is_virtual = True
            rendezvous_point.cluster = self.centroid

            c.rendezvous_point = rendezvous_point
            self.centroid.rendezvous_points[c] = rendezvous_point

        [c.calculate_tour() for c in self.clusters + [self.centroid]]

    def optimize_rendezvous_points(self):

        rounds = 0
        while True:
            rounds += 1
            atl = self.average_tour_length()

            long_clusters = [c for c in self.clusters if c.tour_length > atl + 500.0]
            short_clusters = [c for c in self.clusters if c.tour_length < atl - 500.0]
            if not long_clusters or short_clusters:
                logger.info("All clusters optimized")
                break

            if rounds > MAX_ROUNDS:
                break

            for c in long_clusters:
                while c.tour_length > atl + 500.0:
                    rounds += 1

                    # Move the rendezvous point closer to Ci
                    logger.info("Moving rendezvous point for %r toward %r", c, c)

                    if rounds > MAX_ROUNDS:
                        # self.show_state()
                        # logger.info(long_clusters)
                        break

                    max_length = c.distance(self.virtual_center_segment)
                    rendezvous_vector = c.rendezvous_point - self.virtual_center_segment
                    rendezvous_vector.set_length(min(1.2 * rendezvous_vector.length(), max_length))
                    rendezvous_vector += self.virtual_center_segment

                    # Make sure we can treat this as a "virtual segment"
                    rendezvous_point = segment.Segment(rendezvous_vector.x, rendezvous_vector.y)
                    rendezvous_point.is_virtual = True
                    rendezvous_point.cluster = self.centroid

                    c.rendezvous_point = rendezvous_point
                    self.centroid.rendezvous_points[c] = c.rendezvous_point

                    # Update the tour paths for both Ci and Cn
                    c.calculate_tour()
                    self.centroid.calculate_tour()

                    c_tour = c.tour_nodes()
                    closest, _ = cluster.closest_points(c_tour, [self.virtual_center_segment])
                    closest_index = c_tour.index(closest)
                    if point.direction(c_tour[(closest_index + 1) % len(c_tour)], closest, c.rendezvous_point) > 0:
                        logger.info("Need to move %s into the centroid group!", c)

                        # Move the segment to the centroid cluster
                        c.remove(closest)
                        self.centroid.add(closest)

                        # Update the tours
                        c.calculate_tour()
                        self.centroid.calculate_tour()

                        # Re-calculate the rendezvous point like we did in the initializing step
                        if len(c.segments) == 1:
                            rendezvous_point = c.segments[0]

                        else:
                            decorated = list()
                            prev = c.segments[0]
                            for i, s in enumerate(c.segments[1:], start=1):
                                dist, pt = point.closest_point(prev, s, self.virtual_center_segment)
                                decorated.append((dist, i, pt))
                                prev = s

                            rendezvous_point = min(decorated)[2]

                        rendezvous_vector = rendezvous_point - self.virtual_center_segment
                        rendezvous_vector.scale(0.5)
                        rendezvous_vector += self.virtual_center_segment

                        # Make sure we can treat this as a "virtual segment"
                        rendezvous_point = segment.Segment(rendezvous_vector.x, rendezvous_vector.y)
                        rendezvous_point.is_virtual = True
                        rendezvous_point.cluster = self.centroid

                        c.rendezvous_point = rendezvous_point
                        self.centroid.rendezvous_points[c] = c.rendezvous_point

                        # Update the tours
                        c.calculate_tour()
                        self.centroid.calculate_tour()

            for c in short_clusters:
                while c.tour_length < atl - 500.0:
                    rounds += 1

                    # Move the rendezvous point closer to the centroid
                    logger.info("Moving rendezvous point for %r toward %r", c, self.centroid)

                    if rounds > 100:
                        # self.show_state()
                        break

                    rendezvous_vector = c.rendezvous_point - self.centroid
                    rendezvous_vector.scale(0.8)
                    rendezvous_vector += self.centroid

                    # Make sure we can treat this as a "virtual segment"
                    rendezvous_point = segment.Segment(rendezvous_vector.x, rendezvous_vector.y)
                    rendezvous_point.is_virtual = True
                    rendezvous_point.cluster = self.centroid

                    c.rendezvous_point = rendezvous_point
                    self.centroid.rendezvous_points[c] = c.rendezvous_point

                    # Update the tour paths for both Ci and Cn
                    c.calculate_tour()
                    self.centroid.calculate_tour()

    def average_tour_length(self):

        # For convenience, collect all clusters (including the centroid)
        clusters = self.clusters + [self.centroid]

        # Find the average tour length and return it
        average_tour_length = statistics.mean(c.tour_length for c in clusters)
        return average_tour_length

    def compute_paths(self):
        self.set_up()
        self.create_clusters()
        # sim.show_state()
        self.find_initial_rendezvous_points()
        # logger.info("Average tour length: %f", self.average_tour_length())
        # self.show_state()
        self.optimize_rendezvous_points()
        # self.show_state()
        return self

    def run(self):
        sim = self.compute_paths()
        return tocs_runner.run_sim(sim)


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
    sim = ToCS()
    sim.run()


if __name__ == '__main__':
    main()
