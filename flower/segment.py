import random

import flower.point
from flower.sensor import Packet
from flower import params

class Segment(flower.point.WorldPositionMixin):
    count = 0

    def __init__(self, x=0.0, y=0.0):
        flower.point.WorldPositionMixin.__init__(self, x, y)

        self.segment_id = Segment.count
        Segment.count += 1

        self.cluster = None
        self.cluster_id = params.NOT_CLUSTERED

        self.is_virtual = False
        self.buffer = []

    def total_data_volume(self):
        volume = 0
        for v in list(self.buffer.values()):
            volume += v

        return volume

    def __str__(self):
        return "SEGMENT %d: (%f, %f)" % (self.segment_id, self.x, self.y)

    def __repr__(self):
        return "SEG %d" % self.segment_id


class FlowerSegment(Segment):
    def __init__(self, x=0.0, y=0.0):
        super(FlowerSegment, self).__init__(x, y)

        self.cell = None


def __str__(self):
    return "Flower Segment %d: (%f, %f)" % (self.segment_id, self.x, self.y)


def __repr__(self):
    return "FSEG %d" % self.segment_id

def initialize_traffic(segments, volume, standard_deviation):
    assert (volume > 0.0)
    assert (0.0 <= standard_deviation <= 3.0)

    for source in segments:
        for destination in segments:

            if destination == source:
                continue

            packet_size = random.gauss(volume, standard_deviation)
            new_packet = Packet(destination.cluster, destination, packet_size)
            source.buffer.append(new_packet)
