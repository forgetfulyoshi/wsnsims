import logging
import random
import statistics

import matplotlib.pyplot as plt

from . import point


class TourError(Exception):
    pass


def tour_length(cells):
    points = [cell.collection_point for cell in cells]
    tour_len = 0
    last = points[0]
    for p in points[1:]:
        tour_len += (last - p).length()
        last = p

    return tour_len


def two_body_tour(s1, s2, radius):
    #
    # Get vectors between the two segments
    #
    p1 = s2 - s1
    p2 = s1 - s2

    # Now set the length of the vectors to the radio range
    p1.set_length(radius)
    p2.set_length(radius)

    # Finally, add the vectors back to their original segments
    p1 += s1
    p2 += s2

    s1.collection_point = p1
    s2.collection_point = p2

    return [s1, s2]


def centroid(segments):
    x = statistics.mean(p.x for p in segments)
    y = statistics.mean(p.y for p in segments)

    return point.Vec2(x, y)


def perpendicular_to_line(start, end, p):
    """
    Following method from http://stackoverflow.com/a/5227626
    """
    v = end - start
    d = v.normalized()
    a = start
    x = a + d.set_length((p - a) * d)

    perp = p - x
    return perp


def find_tour(segments, radius=0, start=None):
    if len(segments) < 1:
        raise TourError("Must have at least one cell to compute tour")

    if len(segments) == 1:
        tour = segments

        # HACK
        segments[0].collection_point = point.Vec2(segments[0].x, segments[0].y)
    elif len(segments) == 2:
        tour = two_body_tour(segments[0], segments[1], radius)
    else:
        tour = gt_two_body_tour(segments, radius)

    if start and len(segments) > 1:
        tour = point.rotate_to_start(tour, start)
        tour.append(start)
    else:
        if len(segments) > 1:
            tour.append(tour[0])

    return tour


def gt_two_body_tour(cells, radius):
    hull, interior = point.graham_scan(cells)
    com = centroid(hull)

    # Compute collection points for segments along
    # the hull.
    for cell in hull:
        v = com - cell
        v.set_length(radius)
        v += cell
        cell.collection_point = v

    # Compute collection points for segments in the interior
    for cell in interior:
        closest = None
        last = hull[0]
        for h in hull[1:]:
            perp = perpendicular_to_line(last, h, cell)
            last = h

            if not closest:
                closest = perp
                continue

            if closest.length() > perp.length():
                closest = perp

        closest.set_length(radius)
        cell.collection_point = cell + closest

    tour = point.sort_polar(cells, field='collection_point')
    return tour


def main():
    logging.basicConfig(level=logging.DEBUG)

    # s1 = point.Vec2(2, 8)
    # s2 = point.Vec2(10, 3)
    radius = 2
    #
    # collection_points = two_body_tour(s1, s2, radius)
    # tl = tour_length(collection_points)
    # logging.info("Tour length: %f", tl)

    t = list()
    for _ in range(5):
        v = point.Vec2(random.randint(0, 100), random.randint(0, 100))
        t.append(v)

    tour = gt_two_body_tour(t, radius)
    logging.info("Tour length: %f", tour_length(tour))
    plt.show()


if __name__ == '__main__':
    main()
