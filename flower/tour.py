import logging
import random

import matplotlib.pyplot as plt

import point

logging.basicConfig(level=logging.DEBUG)


def tour_length(points):
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

    return [p1, p2, p1]


def center_of_mass(segments):
    x = 0
    y = 0
    for segment in segments:
        x += segment.x
        y += segment.y

    x /= len(segments)
    y /= len(segments)

    return point.Vec2(x, y)


def perpendicular_to_line(start, end, p):
    """
    Following method from http://stackoverflow.com/a/5227626
    """
    v = end - start
    d = v.normalized()
    a = start
    x = a + d.set_length((p - a) * d)

    perp = x - p
    return perp


def gt_two_body_tour(segments, radius):
    hull, interior = point.graham_scan(segments)
    com = center_of_mass(hull)

    # Compute collection points for segments along
    # the hull.
    collection_points = list()
    for segment in hull:
        v = com - segment
        v.set_length(radius)
        v += segment
        collection_points.append(v)

    # Compute collection points for segments in the interior
    for segment in interior:
        closest = None
        last = hull[0]
        for h in hull[1:]:
            perp = perpendicular_to_line(last, h, segment)
            last = h

            if not closest:
                closest = perp
                continue

            if closest.length() > perp.length():
                closest = perp

        closest.set_length(radius)
        collection_points.append(segment + closest)

    x = [p.x for p in hull]
    y = [p.y for p in hull]
    plt.plot(x, y, 'ro')

    x = [p.x for p in interior]
    y = [p.y for p in interior]
    plt.plot(x, y, 'ro')

    tour = point.sort_polar(collection_points, collection_points[0])
    tour.append(collection_points[0])
    x = [p.x for p in tour]
    y = [p.y for p in tour]
    plt.plot(x, y, 'b-')

    plt.plot([com.x], [com.y], 'go')

    return tour


class TourError(Exception):
    pass


def find_tour(segments, radius):
    if len(segments < 2):
        raise TourError("Must have two or more segments to compute tour")

    if len(segments) == 2:
        return two_body_tour(segments[0], segments[1], radius)

    return gt_two_body_tour(segments, radius)


def main():
    # s1 = point.Vec2(2, 8)
    # s2 = point.Vec2(10, 3)
    radius = 2
    #
    # collection_points = two_body_tour(s1, s2, radius)
    # tl = tour_length(collection_points)
    # logging.info("Tour length: %f", tl)

    t = list()
    for _ in xrange(5):
        v = point.Vec2(random.randint(0, 100), random.randint(0, 100))
        t.append(v)

    tour = gt_two_body_tour(t, radius)
    logging.info("Tour length: %f", tour_length(tour))
    plt.show()


if __name__ == '__main__':
    main()
