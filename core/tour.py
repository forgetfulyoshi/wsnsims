import numpy as np
import scipy.spatial as sp

from core import linalg


class Tour(object):
    def __init__(self):
        """
        Contains all data for a tour over a given set of points.
        """

        #: The original set of points for which a tour was calculated
        self.points = None

        #: A list of indexes into points. Taken in order, these indexes
        #: describe the tour path to each point.
        self.vertices = None

        #: The set of points which a traveller would use to simply enter the
        #: "radio range" of each of the given points. These points correspond
        #: directly to the original points. In other words the collection point
        #: for points[3] is collection_points[3].
        self.collection_points = None


def compute_tour(points, radio_range=0.):
    """
    For a given set of points, calculate a tour that covers each point once.
    This implementation of TSP is based on that used by IDM-kMDC, in which
    a convex hull is first found, then interior points are added to the nearest
    segment of the hull path.

    :param points: The set of 2D points over which to find a path.
    :type points: np.array laid out as [[3,4], [9,2], ...]

    :return: A Tour object containing the original points and a list of indexes
    into those points describing the path between them.
    """
    hull = sp.ConvexHull(points)
    tour = hull.vertices.tolist()
    tour.append(tour[0])

    collection_points = np.zeros(points.shape, dtype=points.dtype)
    center_of_mass = linalg.centroid(points[hull.vertices])
    for vertex in hull.vertices:
        cp = center_of_mass - points[vertex]
        cp /= np.linalg.norm(cp)
        cp *= radio_range
        cp += points[vertex]
        collection_points[vertex] = cp

    # Determine the set of interior points by starting with the original set of
    # vertices and removing the hull points.
    interior = np.arange(start=0, stop=len(points), step=1)
    interior = np.delete(interior, hull.vertices, 0)

    for point_idx in interior:

        closest_segment = -1
        closest_distance = np.inf
        closest_perp = np.zeros((1, 2))

        p = points[point_idx]

        tail = 0
        head = 1
        while head < len(tour):

            start_idx = tour[tail]
            end_idx = tour[head]
            start = collection_points[start_idx]
            end = collection_points[end_idx]

            perp = linalg.perpendicular(start, end, p)
            if np.all(perp == np.array([np.inf, np.inf])):
                tail = head
                head += 1
                continue

            perp_vec = perp - p
            perp_len = np.linalg.norm(perp_vec)

            if perp_len < closest_distance:
                closest_segment = head
                closest_distance = perp_len
                closest_perp = perp_vec

            tail = head
            head += 1

        tour.insert(closest_segment, point_idx)
        collect_point = closest_perp / np.linalg.norm(closest_perp)
        collect_point *= radio_range
        collect_point += points[point_idx]
        collection_points[point_idx] = collect_point

    route = Tour()
    route.points = points
    route.vertices = np.array(tour)
    route.collection_points = collection_points
    return route
