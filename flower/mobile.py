import enum
import logging

from flower import grid

logging.basicConfig(level=logging.DEBUG)


class State(enum.Enum):
    START = 0
    MOVE = 1
    COMMUNICATE = 2
    STOP = 4


class MDC(grid.WorldPositionMixin):
    def __init__(self, cluster):
        grid.WorldPositionMixin.__init__(self)
        self.cluster = cluster
        self.x = cluster.tour()[0].x
        self.y = cluster.tour()[0].y

        self.destination = cluster.tour()[1 % len(cluster.tour())]

        self.speed = 0.1  # meters / second
        self.transmission_rate = 0.1  # Mbps
        self.initial_energy = 1000  # Joule
        self.comms_energy_cost = 2.0  # Joule / Mbit
        self.motion_energy_cost = 1.0  # Joule / meter
        self.radio_range = 100  # meters

        self._time_slice = 1.0  # seconds
        self._energy_remaining = self.initial_energy
        self._state = State.START

    @property
    def is_dead(self):
        out_of_energy = self._energy_remaining <= 0.0
        return out_of_energy

    def has_arrived(self, point):
        arrived = self.distance(point) <= 1.0
        return arrived

    def update(self):

        if self.is_dead:
            self._state = State.STOP

        state_machine = {
            State.START: self.on_start,
            State.MOVE: self.on_move,
            State.COMMUNICATE: self.on_communicate,
            State.STOP: self.on_stop,
        }

        logging.info("%s is in state %s", self, self._state)

        state_machine[self._state]()

    def on_start(self):
        if any(self.has_arrived(s) for s in self.cluster.segments):
            self._state = State.COMMUNICATE
        else:
            self._state = State.MOVE

        self.update()

    def on_move(self):
        direction = self.destination - self
        travel_length = self.speed / self._time_slice
        direction.set_length(travel_length)

        self.x += direction.x
        self.y += direction.y

        self._energy_remaining -= self.motion_energy_cost * travel_length

        if self.has_arrived(self.destination):
            self._state = State.COMMUNICATE

    def on_communicate(self):

        # transmit and receive

        # If we're done communicating, update the destination and set the state back to MOVE
        tour = self.cluster.tour()
        destination_index = tour.index(self.destination)
        self.destination = tour[destination_index + 1 % len(tour)]
        self._state = State.MOVE

    def on_stop(self):
        pass
