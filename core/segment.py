
from core import params
from core import point


class Segment(object):
    count = 0

    def __init__(self, nd):
        self.segment_id = Segment.count
        Segment.count += 1

        self.location = point.Vec2(nd)
        self.cluster_id = params.NOT_CLUSTERED

    def __str__(self):
        return "Segment {}".format(self.segment_id)

    def __repr__(self):
        return "SEG {}".format(self.segment_id)


class FlowerSegment(Segment):
    def __init__(self, nd):
        super(FlowerSegment, self).__init__(nd)
        self.cell = None

    def __str__(self):
        return "Flower Segment {}".format(self.segment_id)

    def __repr__(self):
        return "FSEG {}".format(self.segment_id)