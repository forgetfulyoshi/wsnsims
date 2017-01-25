from wsnsims.core.segment import Segment


class FlowerSegment(Segment):
    def __init__(self, nd):
        super(FlowerSegment, self).__init__(nd)
        self.cell_id = -1

    def __str__(self):
        return "FLOWER Segment {}".format(self.segment_id)

    def __repr__(self):
        return "FSEG {}".format(self.segment_id)
