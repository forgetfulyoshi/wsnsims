import numpy as np

from wsnsims.core import point


def side_length(environment):
    """

    :param environment:
    :type environment: core.environment.Environment
    :return: pq.meter
    """

    return environment.comms_range / np.sqrt(2)


class Cell(object):
    """ Defines a cell in the grid """

    count = 0

    def __init__(self, row, column, environment):
        """

        :param row:
        :param column:
        :param environment:
        :type environment: core.environment.Environment
        """

        self.cell_id = Cell.count
        Cell.count += 1

        # Maintain the grid position.
        self.grid_location = np.array([row, column])

        # Calculate the physical location of the center of this cell.
        side_len = side_length(environment)
        x_pos = column * side_len + (side_len / 2.)
        y_pos = row * side_len + (side_len / 2.)
        self.location = point.Vec2(np.array([x_pos, y_pos]))  # * pq.meter

        # The segments within radio range of this cell.
        self.segments = list()

        # The (maximum eight) cells immediately adjacent to this cell.
        self.neighbors = list()

        # The number of segments within radio range of any neighbor cell
        self.signal_hop_count = 0

        # The cell distance between this cell and the centroid cell, G.
        self.proximity = 0

        # The numeric identifier of the virtual cluster this cell belongs to.
        self.virtual_cluster_id = -1

        # The numeric identifier of the cluster this cell belongs to.
        self._cluster_id = -1

    @property
    def cluster_id(self):
        return self._cluster_id

    @cluster_id.setter
    def cluster_id(self, value):
        self._cluster_id = value

    @property
    def access(self):
        """
        The number of segments within radio range of this cell.
        """
        return len(self.segments)

    def __str__(self):
        return "Cell {}".format(self.cell_id)

    def __repr__(self):
        return "C {}".format(self.cell_id)
