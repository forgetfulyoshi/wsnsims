import numpy as np


class LinalgError(Exception):
    pass


def ccw(p0, p1, p2):
    """
    Determine if the "turn" described by the points is counterclockwise.

    :param p0: The 2D starting point
    :type p0: numpy.array

    :param p1: The 2D turn point
    :type p1: numpy.array

    :param p2: The 2D end point
    :type p2: numpy.array

    :returns True: the turn is counterclockwise
    :returns False: the turn is clockwise or colinear
    """

    if p0.shape != (2,) or p1.shape != (2,) or p2.shape != (2,):
        raise LinalgError("Can only determine turn of 2D points")

    cp = np.cross(p2 - p0, p1 - p0)
    is_ccw = cp < 0.
    return is_ccw


def perpendicular(start, end, p):
    """
    Compute the perpendicular of the vector from start to end starting at p
    Following method from http://stackoverflow.com/a/5227626

    :param start: starting point of the original vector
    :type start: numpy.array

    :param end: ending point of the original vector
    :type end: numpy.array

    :param p: starting point of the perpendicular vector
    :type p: numpy.array

    :return: the vector describing the new perpendicular or an array of np.inf
        if the point is out of range for the line segment
    :rtype: numpy.array
    """
    segment = end - start
    unit_segment = segment / np.linalg.norm(segment)
    scalar_projection = np.dot(p - start, unit_segment)

    if scalar_projection > np.linalg.norm(segment):
        return np.array([np.inf, np.inf])

    perp = scalar_projection * unit_segment
    perp += start

    if np.linalg.norm(end - perp) > np.linalg.norm(segment):
        return np.array([np.inf, np.inf])

    return perp


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
