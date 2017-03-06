from typing import List

import numpy as np
import scipy.spatial as sp

from wsnsims.core import linalg

np.seterr(all='raise')


class Tour(object):
    def __init__(self):
        """
        Contains all segment_volume for a tour over a given set of points.
        """

        #: The original set of points for which a tour was calculated
        self.points = None  # type: List[np.ndarray] | None

        #: A list of indexes into points. Taken in order, these indexes
        #: describe the tour path to each point.
        self.vertices = None  # type: List[int]

        #: The set of points which a traveller would use to simply enter the
        #: "radio range" of each of the given points. These points correspond
        #: directly to the original points. In other words the collection point
        #: for points[3] is collection_points[3].
        self.collection_points = None

        #: The list of hull vertices. This is useful for checking if a point is
        #: "inside" a tour.
        self.hull = None

        #: Additional objects that can be stored. This is typically used to
        #: correlate the tour points to their original objects (e.g., segments
        #: or cells).
        self.objects = None

        #: Internal memo of the length of this tour
        self._length = np.inf

    @property
    def length(self):
        if not np.isinf(self._length):
            return self._length

        if len(self.vertices) < 2:
            self._length = 0. # * pq.meter
            return self._length

        total = 0. # * pq.meter
        tail = 0
        head = 1
        while head < len(self.vertices):
            start = self.collection_points[self.vertices[tail]]
            stop = self.collection_points[self.vertices[head]]

            total += np.linalg.norm(stop - start) # * pq.meter

            tail += 1
            head += 1

        self._length = total
        return self._length


def compute_tour(points, radio_range=0.):
    """
    For a given set of points, calculate a tour that covers each point once.
    This implementation of TSP is based on that used by IDM-kMDC, in which
    a convex hull is first found, then interior points are added to the nearest
    segment of the hull path.

    :param points: The set of 2D points over which to find a path.
    :type points: np.array laid out as [[3,4], [9,2], ...]

    :param radio_range:
    :type radio_range: float

    :return: A Tour object containing the original points and a list of indexes
    into those points describing the path between them.
    """

    if len(points) < 2:
        t = Tour()
        t.points = points
        t.vertices = np.array(range(len(points)))
        t.collection_points = points
        return t

    if len(points) == 2:
        vertices = np.array([0, 1])
    else:
        hull = sp.ConvexHull(points, qhull_options='QJ Pp')
        vertices = hull.vertices

    route = Tour()
    route.hull = np.copy(vertices)

    tour = list(vertices)

    collection_points = np.empty_like(points)
    center_of_mass = linalg.centroid(points[vertices])
    for vertex in vertices:
        if np.all(np.isclose(center_of_mass, points[vertex])):
            collection_points[vertex] = np.copy(points[vertex])
            continue

        cp = center_of_mass - points[vertex]
        cp /= np.linalg.norm(cp)
        cp *= radio_range
        cp += points[vertex]
        collection_points[vertex] = cp

    # Determine the set of interior points by starting with the original set of
    # vertices and removing the hull points.
    interior = np.arange(start=0, stop=len(points), step=1)
    interior = np.delete(interior, vertices, 0)

    for point_idx in interior:

        closest_segment = -1
        closest_distance = np.inf
        closest_perp = np.zeros((1, 2))

        p = points[point_idx]

        tail = len(tour) - 1
        head = 0
        while head < len(tour):

            start_idx = tour[tail]
            end_idx = tour[head]
            start = collection_points[start_idx]
            end = collection_points[end_idx]

            perp_len, perp_vec = linalg.closest_point(start, end, p)

            if perp_len < closest_distance:
                closest_segment = head
                closest_distance = perp_len
                closest_perp = perp_vec

            tail = head
            head += 1

        tour.insert(closest_segment, point_idx)

        collect_point = closest_perp - p
        radius = np.linalg.norm(collect_point)

        if radius > radio_range:
            collect_point /= radius
            collect_point *= radio_range

        collect_point += p
        collection_points[point_idx] = collect_point

    tour.append(tour[0])

    route.points = points
    route.vertices = np.array(tour)
    route.collection_points = collection_points

    # TODO: Remove these asserts
    for i in range(len(points)):
        assert i in tour
    assert len(tour) == len(points) + 1
    assert len(route.points) == len(route.collection_points)

    return route
