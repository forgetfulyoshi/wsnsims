from collections import namedtuple

Packet = namedtuple('Packet', ['dst_cluster', 'dst_sensor', 'size'])


class MDCRadioMixin(object):
    """ Add communication capabilities to a node. Node must define a buffer attribute"""

    def __init__(self):
        self.buffer = []


        self.transmission_rate = 0.1  # Mbps

    def communicate_sensor(self, other):
        """ MDC <-> Sensor communication """

        to_tx = [packet for packet in self.buffer if packet.dst_sensor == other]
        to_rx = [packet for packet in other.buffer if packet.dst_sensor == self]

        # Calculate the total size, time, and energy requirements for the
        # transmit operation.
        tx_size = sum(packet.size for packet in to_tx)
        tx_energy = tx_size * self.comms_energy_cost
        tx_time = tx_size / self.transmission_rate

        # Calculate the total size, time, and energy requirements for the
        # receive operation.
        rx_size = sum(packet.size for packet in to_rx)
        rx_energy = rx_size * self.comms_energy_cost
        rx_time = rx_size / self.transmission_rate

        # Update the source and destination buffers as needed
        other.buffer += to_tx
        [self.buffer.remove(packet) for packet in to_rx]

        return tx_energy, tx_time, rx_energy, rx_time

    def communicate_relay(self, relay):
        """ MDC <-> Relay communication """

        to_tx = [packet for packet in self.buffer if packet.dst_cluster in relay.clusters]
        to_rx = [packet for packet in relay.buffer if packet.dst_cluster == self.cluster]

        # Calculate the total size, time, and energy requirements for the
        # transmit operation.
        tx_size = sum(packet.size for packet in to_tx)
        tx_energy = tx_size * self.comms_energy_cost
        tx_time = tx_size / self.transmission_rate

        # Calculate the total size, time, and energy requirements for the
        # receive operation.
        rx_size = sum(packet.size for packet in to_rx)
        rx_energy = rx_size * self.comms_energy_cost
        rx_time = rx_size / self.transmission_rate

        # Update the source and destination buffers as needed
        relay.buffer += to_tx
        [self.buffer.remove(packet) for packet in to_rx]

        return tx_energy, tx_time, rx_energy, rx_time
