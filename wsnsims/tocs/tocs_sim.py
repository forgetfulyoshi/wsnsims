import logging
import typing

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import path as mp

from wsnsims.core import linalg
from wsnsims.core import segment
from wsnsims.core.comparisons import much_greater_than
from wsnsims.core.environment import Environment
from wsnsims.tocs.cluster import ToCSCluster, ToCSCentroid, RelayNode
from wsnsims.tocs.cluster import combine_clusters
from wsnsims.tocs.tocs_runner import ToCSRunner

logger = logging.getLogger(__name__)


class TOCS(object):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """

        self.env = environment
        locs = np.random.rand(self.env.segment_count, 2) * self.env.grid_height
        self.segments = [segment.Segment(nd) for nd in locs]
        self._center = linalg.centroid(locs)

        # Create the centroid cluster
        self.centroid = ToCSCentroid(self.env)

        self.clusters = list()  # type: typing.List[ToCSCluster]

        self._length_threshold = 0.5

    @property
    def center(self):
        if len(self.centroid.nodes) == 0:
            return self._center

        return self.centroid.location.nd

    def show_state(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)

        # Show the location of all segments
        segment_points = [seg.location.nd for seg in self.segments]
        segment_points = np.array(segment_points)
        ax.plot(segment_points[:, 0], segment_points[:, 1], 'bo')

        # Show the outline of the clusters
        for clust in self.clusters:
            route = clust.tour
            points = route.points
            ax.plot(points[route.vertices, 0], points[route.vertices, 1],
                    'b--', lw=2)

        # Show the centroid points
        route = self.centroid.tour
        points = route.collection_points
        ax.plot(points[:, 0], points[:, 1], 'ro')
        ax.plot(points[route.vertices, 0], points[route.vertices, 1],
                'r--', lw=2)

        # Show the path using the collection points
        for clust in self.clusters:
            route = clust.tour
            cps = route.collection_points
            ax.plot(cps[:, 0], cps[:, 1], 'go')
            ax.plot(cps[route.vertices, 0], cps[route.vertices, 1],
                    'g--', lw=2)

        # Annotate the segments for easier debugging
        for seg in self.segments:
            xy = seg.location.nd
            xy_text = xy + 1.

            ax.annotate(seg, xy=xy, xytext=xy_text)

        plt.show()

    def create_clusters(self):

        for seg in self.segments:
            clust = ToCSCluster(self.env)
            clust.add(seg)
            self.clusters.append(clust)

        while len(self.clusters) >= self.env.mdc_count:
            self.clusters = combine_clusters(self.clusters, self.centroid)

    def find_initial_rendezvous_points(self):
        """
        Determine and assign the RPs for each of the initial clusters.

        :return: None
        """

        for clust in self.clusters:
            self._calculate_rp(clust)

    def _unbalanced(self):
        """
        Determine if any clusters have tours which are dramatically smaller or
        larger than the average tour length over all clusters.

        :return: True if the clusters are unbalanced and need adjustment
        :return: False if the clusters are all close to even tour lengths
        :rtype: bool
        """
        average_length = self.average_tour_length()
        logger.debug("Average tour length: %s", average_length)
        for clust in self.clusters:
            logger.debug("%s tour length: %s", clust, clust.tour_length)

            max_tour = clust.tour_length
            max_tour += np.linalg.norm(
                clust.rendezvous_point.location.nd - self.center)

            if max_tour < average_length:
                logger.debug("Cannot optimize %s in this round", clust)
                continue

            if much_greater_than(average_length, clust.tour_length,
                                 r=self._length_threshold):
                return True

            elif much_greater_than(clust.tour_length, average_length,
                                   r=self._length_threshold):
                return True

        return False

    def _grow_cluster(self, clust, average_length):
        """
        Update a cluster's rendezvous point so as to bring it "closer" to the
        centroid cluster. This effectively grows the cluster's tour. The
        process of moving the RP is repeated until the cluster's tour length
        is no longer "much larger" than the average tour length.

        :param clust: Cluster to consider
        :type clust: ToCSCluster
        :param average_length: Average tour length of all clusters
        :type average_length: pq.quantity.Quantity
        :return: None
        """

        while much_greater_than(average_length, clust.tour_length,
                                r=self._length_threshold):
            current_rp_loc = clust.rendezvous_point.location.nd

            # Calculate the vector between the current RP and the center of the
            # centroid cluster. Then just scale it down.
            new_rp_loc = current_rp_loc - self.center
            new_rp_loc *= 0.75
            new_rp_loc += self.center

            if np.allclose(current_rp_loc, new_rp_loc):
                break

            # Now assign the new location to the existing RP object (just saves
            # us object creation).
            self._update_rp_pos(clust, new_rp_loc)

            # Now reassign segments if the cluster's RP is closer to the
            # centroid than an actual segment within the central cluster.
            self._reassign_segments_to_cluster(clust)

    def _shrink_cluster(self, clust, average_length):
        """
        Update a cluster's rendezvous point so as to bring it "further" from
        the centroid cluster. This effectively shrinks the cluster's tour. The
        process of moving the RP is repeated until the cluster's tour length
        is no longer "much smaller" than the average tour length.

        :param clust: Cluster to consider
        :type clust: ToCSCluster
        :param average_length: Average tour length of all clusters
        :type average_length: pq.quantity.Quantity
        :return: None
        """

        while much_greater_than(clust.tour_length, average_length,
                                r=self._length_threshold):
            current_rp_loc = clust.rendezvous_point.location.nd

            # Calculate the vector between the current RP and the center of the
            # centroid cluster. Then just scale it up.
            new_rp_loc = current_rp_loc - self.center
            new_rp_loc *= 1.25
            new_rp_loc += self.center

            # Handle the case where a cluster's tour cannot be optimized any
            # further.
            if np.allclose(new_rp_loc, current_rp_loc):
                break

            # Now assign the new location to the existing RP object (just saves
            # us object creation).
            self._update_rp_pos(clust, new_rp_loc)

            # Now reassign segments if needed
            self._reassign_segments_to_central(clust)

    def _closest_to_center(self, clust):
        """
        Find the segment in a cluster that is closest to the centroid.

        :param clust: Cluster to examine
        :type clust: ToCSCluster
        :return: The closest segment and it's distance (in meters) from the
                 centroid.
        :rtype: (core.segment.Segment, pq.quantity.Quantity)
        """

        closest = None
        min_distance = np.inf
        for seg in clust.segments:
            distance = np.linalg.norm(seg.location.nd - self.center)

            if min_distance > distance:
                min_distance = distance
                closest = seg

        return closest, min_distance

    def _reassign_segments_to_cluster(self, clust):
        """
        Check for and handle the condition described as a cluster, Ci, having
        its rendezvous point, Ri, "on" the convex hull of G. Detecting if Ri is
        "on" the convex hull of G is problematic as we can step over it while
        adjusting the Ri position quite easily. This could lead to a situation
        where Ri steps from the exterior of G to the interior without ever
        being "on" the hull. To compensate for this, we could either limit the
        amount Ri could be moved in any one step, or directly check for Ri
        breaching the hull of G. The matplotlib library has a built-in ability
        to check for points inside a polygon, so we'll be using the interior-
        check approach.

        If Ri is inside the hull of G, then we will check to see if G has a
        segment that should be added to the Ci. We do this by first checking to
        see if G has any segments, as it typically does not. If it does though,
        we find the segment closest to the centroid of Ci, remove it from G,
        and then recalculate the position of Ri.

        :param clust: The cluster to examine and modify if needed.
        :type clust: ToCSCluster
        :return: None
        """

        # If G has no segments, then we can't do anything.
        if not self.centroid.segments:
            return

        # Determine if Ri is within the hull of Ci. Return without doing
        # anything if it is not.
        points = self.centroid.tour.points
        hull_verts = self.centroid.tour.hull
        path = mp.Path(points[hull_verts])

        if not path.contains_point(clust.rendezvous_point.location.nd):
            return

        # Find the segment in G that is closest to the centroid of Ci
        closest = None
        min_distance = 0.
        for seg in self.centroid.segments:
            distance = np.linalg.norm(seg.location.nd - clust.location.nd)
            if min_distance > distance:
                closest = seg

        # Move the segment from G to Ci
        self.centroid.remove_segment(closest)
        clust.add(closest)

        # Now recalculate Ri
        self._calculate_rp(clust)

    def _reassign_segments_to_central(self, clust):
        """
        Check for and handle the condition described as a cluster having its
        RP on its convex hull. Rather than actually checking the convex hull,
        this implementation will check for any segment that is closer to the
        centroid than the cluster's RP.

        If this is the case, the identified segment will be removed from the
        cluster and added to the central cluster, G. The old RP will then be
        eliminated, and a new one assigned to the cluster.

        :param clust: The cluster to examine and modify if needed.
        :type clust: ToCSCluster
        :return: None
        """

        closest, distance = self._closest_to_center(clust)
        rp_distance = np.linalg.norm(
            self.center - clust.rendezvous_point.location.nd)

        # If the distance between the centroid and the closest segment is
        # longer than the distance between the centroid and RP, we don't need
        # to do anything further.
        if distance > rp_distance:
            return

        # Remove the closest node and add it to the central cluster, G.
        clust.remove(closest)
        self.centroid.add_segment(closest)

        # Remove the existing RP from the central cluster
        # rp = clust.rendezvous_point
        # self.centroid.remove(rp)

        # Calculate the new RP
        self._calculate_rp(clust)

    def _calculate_rp(self, clust):
        """
        As described in the ToCS paper, this routine will use the actual
        positions of the cluster segments to determine the location of the
        rendezvous point, and assign it to the cluster.

        :param clust: The cluster to calculate an RP for.
        :type clust: ToCSCluster
        :return: None
        """

        c_tour = clust.tour
        if len(c_tour.points) == 1:
            rendezvous_point = np.copy(c_tour.points[0])

        else:
            decorated = list()
            prev = c_tour.vertices[0]
            for i, s in enumerate(c_tour.vertices[1:], start=1):
                dist, pt = linalg.closest_point(c_tour.points[prev],
                                                c_tour.points[s], self.center)
                decorated.append((dist, i, pt))
                prev = s

            rendezvous_point = min(decorated)[2]

        rendezvous_point += self.center
        rendezvous_point *= 0.5

        self._update_rp_pos(clust, rendezvous_point)

    def _update_rp_pos(self, clust, nd):
        """
        Update or assign a rendezvous point for a cluster.

        :param clust: The cluster to update
        :type clust: ToCSCluster
        :param nd: The 2D position for the rendezvous point
        :type nd: np.array
        :return: None
        """
        if clust.rendezvous_point:
            old_rp = clust.rendezvous_point
            self.centroid.remove(old_rp)

        new_rp = RelayNode(nd)
        clust.rendezvous_point = new_rp
        self.centroid.add(new_rp)

    def optimize_rendezvous_points(self):
        # self.show_state()
        round_count = 1
        while self._unbalanced():
            logger.debug("Running optimization round %d", round_count)
            round_count += 1

            if round_count > 100:
                raise TimeoutError("TOCS optimization got lost")

            average_length = self.average_tour_length()

            for clust in self.clusters:
                logger.debug("Examining %s", clust)
                if much_greater_than(average_length, clust.tour_length,
                                     r=self._length_threshold):
                    # Handle the case where we need to move the cluster's RP
                    # closer to the centroid.
                    self._grow_cluster(clust, average_length)

                elif much_greater_than(clust.tour_length, average_length,
                                       r=self._length_threshold):
                    # Handle the case where we need to move the cluster's RP
                    # closer to the cluster itself.
                    self._shrink_cluster(clust, average_length)

                else:
                    continue

                    # self.show_state()

    def average_tour_length(self):
        """
        Calculate the average length of the tour for each cluster.

        :return: The average tour length, in meters.
        :rtype: pq.quantity.Quantity
        """

        # For convenience, collect all clusters (including the centroid)
        clusters = self.clusters + [self.centroid]

        # Find the average tour length and return it
        lengths = np.array([c.tour_length for c in clusters])
        average_tour_length = float(np.mean(lengths))
        return average_tour_length

    def compute_paths(self):
        self.create_clusters()
        # self.show_state()
        self.find_initial_rendezvous_points()
        # logger.debug("Average tour length: %s", self.average_tour_length())
        # self.show_state()
        self.optimize_rendezvous_points()
        # self.show_state()
        return self

    def run(self):
        """

        :return:
        :rtype: tocs.tocs_runner.ToCSRunner
        """
        sim = self.compute_paths()
        runner = ToCSRunner(sim, self.env)
        logger.debug("Maximum comms delay: {}".format(
            runner.maximum_communication_delay()))
        logger.debug("Energy balance: {}".format(runner.energy_balance()))
        logger.debug("Average energy: {}".format(runner.average_energy()))
        logger.debug("Max buffer size: {}".format(runner.max_buffer_size()))
        return runner


def main():
    env = Environment()
    # seed = int(time.time())

    # General testing ...
    seed = 1487736569
    env.isdva = 10.
    # env.mdc_count = 5

    logger.debug("Random seed is %s", seed)
    np.random.seed(seed)
    sim = TOCS(env)
    sim.run()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('tocs_sim')
    main()
