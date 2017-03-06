"""Simulation grid definitions"""

import itertools
import logging
import math

import numpy as np

from wsnsims.flower.cell import Cell, side_length

logger = logging.getLogger(__name__)


class Grid(object):
    """ Define the simulation grid """

    def __init__(self, segments, environment):
        """

        :param segments:
        :type segments: np.array
        :param environment:
        :type environment: core.environment.Environment
        """
        self.segments = segments
        self.rows = 0
        self.cols = 0

        self._env = environment
        self.width = self._env.grid_width
        self.height = self._env.grid_height

        self._grid = list()
        self._layout_cells()

    def _layout_cells(self):
        side_len = side_length(self._env)
        logger.debug("Cell side length: %s", side_len)
        logger.debug("Original dimensions: %s x %s", self.width, self.height)

        # First, adjust the physical size of the grid to accommodate whole
        # cells. This keeps us from having partial cells in the simulation.
        # self.width = np.round(self.width / side_len) * side_len
        # self.height = np.round(self.height / side_len) * side_len
        #
        # logger.debug("Adjusted dimensions: %s x %s", self.width, self.height)

        # Now, calculate the number of cells per row and column. This also
        # makes the row and column counts unit-less.
        self.rows = math.ceil(self.height / side_len)
        self.cols = math.ceil(self.width / side_len)

        logger.debug("Grid is %d x %d cells", self.rows, self.cols)

        # Initialize the grid
        self._grid = list()
        for row in range(self.rows):
            new_row = list()
            for col in range(self.cols):
                new_cell = Cell(row, col, self._env)
                new_row.append(new_cell)

            self._grid.append(new_row)

        for row in range(self.rows):
            for col in range(self.cols):
                current_cell = self.cell(row, col)
                current_cell.neighbors = self.cell_neighbors(current_cell)
                current_cell.segments = self.cell_segments(current_cell)

    def closest_cell(self, position):
        """

        :param position:
        :type position: np.array
        :return:
        :rtype: Cell
        """

        closest_cell = None
        closest_distance = np.inf
        for cell in self.cells():
            distance = np.linalg.norm(position - cell.location.nd)
            if distance < closest_distance:
                closest_cell = cell
                closest_distance = distance

        return closest_cell

    def cells(self):
        """
        Get an iterator over all cells in the grid
        :rtype: collections.Iterator(Cell)
        """
        for row in self._grid:
            for cell in row:
                yield cell

    def cell(self, row, col):
        """
        Given a row and col, return the actual Cell object.
        :rtype: Cell
        """

        return self._grid[row][col]

    def cell_segments(self, cell):
        """
        Find all segments within range of the given cell.

        :param cell:
        :type cell: Cell
        :return: The list of segments.
        :rtype: list(core.segment.Segment)
        """

        segments = list()
        radio_range = self._env.comms_range
        for seg in self.segments:
            distance = np.linalg.norm(cell.location.nd - seg.location.nd)
            if distance < radio_range:
                segments.append(seg)

        return segments

    def on_grid(self, coordinates):
        (row, col) = coordinates
        if 0 > row or row >= self.rows:
            return False

        if 0 > col or col >= self.cols:
            return False

        return True

    def cell_neighbors(self, cell, radius=1):

        row = cell.grid_location[0]
        col = cell.grid_location[1]

        #
        # First, generate the set of possible coordinates
        #        
        possible_coords = itertools.product(
            list(range(row - radius, row + radius + 1)),
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


def cell_distance(lhs, rhs):
    """

    :param lhs:
    :type lhs: Cell
    :param rhs:
    :type rhs: Cell
    :return: The cell distance between lhs and rhs
    """

    row_dist = np.abs(lhs.grid_location[0] - rhs.grid_location[0])
    col_dist = np.abs(lhs.grid_location[1] - rhs.grid_location[1])
    distance = np.max([row_dist, col_dist])
    return distance
