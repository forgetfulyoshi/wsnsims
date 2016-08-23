import random

from flower import grid


class Segment(grid.WorldPositionMixin):
    count = 0

    def __init__(self, x=0.0, y=0.0):
        grid.WorldPositionMixin.__init__(self, x, y)

        self.segment_id = Segment.count
        Segment.count += 1

        self.data = {}

    def data_volume(self, segment):

        if segment not in self.data:
            return 0

        return self.data[segment]

    def total_data_volume(self):
        volume = 0
        for v in list(self.data.values()):
            volume += v

        return volume

    def __str__(self):
        return "SEGMENT %d: (%f, %f)" % (self.segment_id, self.x, self.y)

    def __repr__(self):
        return "SEG %d" % self.segment_id


def initialize_traffic(segments, volume, standard_deviation):

    assert(volume > 0.0)
    assert(0.0 <= standard_deviation <= 3.0)

    for source in segments:
        for destination in segments:

            if destination == source:
                continue

            source.data[destination] = random.gauss(volume, standard_deviation)
