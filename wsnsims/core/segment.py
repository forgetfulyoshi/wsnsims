from wsnsims.core import point


class Segment(object):
    count = 0

    def __init__(self, nd):
        self.segment_id = Segment.count
        Segment.count += 1

        self.location = point.Vec2(nd)
        self.cluster_id = -1

    def __str__(self):
        return "Segment {}".format(self.segment_id)

    def __repr__(self):
        return "SEG {}".format(self.segment_id)
