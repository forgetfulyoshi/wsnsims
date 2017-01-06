"""Simulation grid definitions"""

import itertools
import logging
import math

from original_flower import point, params
from original_flower.point import WorldPositionMixin


class GridPositionMixin(object):
    """Describes a position on the grid"""

    def __init__(self, row=0, col=0):
        self._row = int(row)
        self._col = int(col)

    def __eq__(self, other):
        return [self.row, self.col] == [other.row, other.col]

    def __hash__(self):
        return hash((self.row, self.col))

    @property
    def row(self):
        """ Get the row coordinate """
        return self._row

    @row.setter
    def row(self, value):
        self._row = int(value)

    @property
    def col(self):
        """ Get the column coordinate """
        return self._col

    @col.setter
    def col(self, value):
        """ Set the column coordinate """
        self._col = int(value)

    def cell_distance(self, other):
        """ Calculate cell distance as per the FLOWER paper """
        dist = max(abs(self.row - other.row), abs(self.col - other.col))
        return dist


class Grid(object):
    """ Define the simulation grid """

    def __init__(self, width, hieght):
        self.width = width
        self.hieght = hieght
        self.rows = 0
        self.cols = 0

        self._grid = list()
        self._layout_cells()

    def _layout_cells(self):
        logging.info("Cell side length: %s", Cell.side_len)
        logging.info("Original dimensions: %s x %s", self.width, self.hieght)

        #
        # First, adjust the physical size of the grid to accomodate whole
        # cells. This keeps us from having partial cells in the simulation.
        #
        self.width = round(self.width / Cell.side_len) * Cell.side_len
        self.hieght = round(self.hieght / Cell.side_len) * Cell.side_len

        logging.info("Adjusted dimensions: %s x %s", self.width, self.hieght)

        #
        # Now, calculate the number of cells per row and column
        #
        self.rows = int((self.hieght / Cell.side_len))
        self.cols = int((self.width / Cell.side_len))

        #
        # Initialize the grid with empty cells
        #
        self._grid = [[Cell() for _ in range(self.cols)] for _ in range(self.rows)]

        #
        # Now go back over the grid and do basic cell initialization
        #
        for row_num, row in enumerate(self._grid):
            for col_num, cell in enumerate(row):
                cell.row = row_num
                cell.col = col_num

                physical_pos = self.cell_position(row_num, col_num)
                cell.x = physical_pos.x
                cell.y = physical_pos.y

                cell.neighbors = self.cell_neighbors(row_num, col_num)

    def cells(self):
        for row in self._grid:
            for cell in row:
                yield cell

    def cell(self, row, col):
        """ Given a row and col, return the actual Cell object """
        return self._grid[row][col]

    @staticmethod
    def cell_position(row, col):
        """ Given a row and col, calculate the physical position of a cell """

        x_coord = col * Cell.side_len + (Cell.side_len / 2.0)
        y_coord = row * Cell.side_len + (Cell.side_len / 2.0)
        return point.Vec2(x_coord, y_coord)

    def on_grid(self, coordinates):
        (row, col) = coordinates
        if 0 > row or row >= self.rows:
            return False

        if 0 > col or col >= self.cols:
            return False

        return True

    def cell_neighbors(self, row, col, radius=1):

        #
        # First, generate the set of possible coordinates
        #        
        possible_coords = itertools.product(list(range(row - radius, row + radius + 1)),
                                            list(range(col - radius, col + radius + 1)))

        #
        # Now, filter out all coordinates not on the grid
        #
        neighbors = filter(self.on_grid, possible_coords)

        #
        # Remove the original point from the list of neighbors.
        # A cell cannot be its own neighbor.
        #
        neighbors = list(neighbors)
        neighbors.remove((row, col))

        #
        # Convert the coordinates into the actual cells
        #
        neighbors = [self.cell(row, col) for row, col in neighbors]
        return neighbors

    def center(self):
        return self.cell(self.rows // 2, self.cols // 2)


class Cell(WorldPositionMixin, GridPositionMixin):
    """ Defines a cell in the grid """

    side_len = params.COMMUNICATION_RANGE / math.sqrt(2)
    count = 1

    def __init__(self, x=0.0, y=0.0):
        WorldPositionMixin.__init__(self, x, y)
        GridPositionMixin.__init__(self)

        self.neighbors = list()
        self.access = 0
        self.signal_hop_count = 0
        self.proximity = 0
        self.segments = list()
        self.collection_point = None

        self.virtual_cluster_id = params.NOT_CLUSTERED
        self.cluster_id = params.NOT_CLUSTERED
        self.cluster = None

        self._cell_id = Cell.count
        Cell.count += 1

    def __str__(self):
        return "Cell %d (Cluster %d)" % (self._cell_id, self.cluster_id)

    def __repr__(self):
        return "Cell %d" % (self._cell_id,)
