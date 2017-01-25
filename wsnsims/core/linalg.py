import numpy as np


def centroid(points):
    """
    Calculate the center of mass over a collection of points

    :param points: The points, expressed as numpy.array
    :type points: numpy.array

    :return: The center of mass for the given points
    :rtype: numpy.array
    """
    com = np.mean(points, 0)
    return com


def closest_point(v, w, p):
    """
    Find the point closest to p on the line between v and w
    Modified from StackOverflow at http://stackoverflow.com/a/1501725

    Returns the distance and the point on the line segment between v and w
    """
    vw = w - v
    len_squared = np.dot(vw, vw)
    if 0. == len_squared:
        # Handles the case when v == w
        projection = v
    else:
        t = max(0., min(1., np.dot((p - v), vw) / len_squared))
        projection = v + t * vw
    return np.linalg.norm(projection - p), projection
