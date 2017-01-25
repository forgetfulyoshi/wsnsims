import logging

from wsnsims.core.cluster import BaseCluster

logger = logging.getLogger(__name__)


class FlowerCluster(BaseCluster):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """
        super(FlowerCluster, self).__init__(environment)

        self.completed = False
        self.recent = None

    @property
    def cluster_id(self):
        return super(FlowerCluster, self).cluster_id

    @cluster_id.setter
    def cluster_id(self, value):
        self._cluster_id = value
        for cell in self.cells:
            cell.cluster_id = self.cluster_id

    @property
    def cells(self):
        return self.nodes

    @cells.setter
    def cells(self, value):
        self.nodes = value

    @property
    def segments(self):
        cluster_segments = list()
        for cell in self.cells:
            cluster_segments.extend(cell.segments)

        cluster_segments = list(set(cluster_segments))
        return cluster_segments

    @property
    def anchor(self):
        return self.relay_node

    @anchor.setter
    def anchor(self, value):
        self.relay_node = value

    def add(self, cell):
        """

        :param cell:
        :type cell: flower.cell.Cell
        :return:
        """
        super(FlowerCluster, self).add(cell)
        self.recent = cell

    def remove(self, cell):
        """

        :param cell:
        :type cell: flower.cell.Cell
        :return:
        """
        super(FlowerCluster, self).remove(cell)
        if cell == self.recent:
            self.recent = None

    def __str__(self):
        return "Flower Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "FC{}".format(self.cluster_id)


class FlowerVirtualCluster(FlowerCluster):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """
        super(FlowerVirtualCluster, self).__init__(environment)

    def __str__(self):
        return "Flower Virtual Cluster {}".format(self.cluster_id)

    def __repr__(self):
        return "FVC{}".format(self.cluster_id)

    @property
    def cluster_id(self):
        return super(FlowerVirtualCluster, self).cluster_id

    @cluster_id.setter
    def cluster_id(self, value):
        self._cluster_id = value
        for cell in self.cells:
            cell.virtual_cluster_id = self.cluster_id


class FlowerHub(FlowerCluster):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """
        super(FlowerHub, self).__init__(environment)

    def __str__(self):
        return "Flower Hub Cluster"

    def __repr__(self):
        return "FH"


class FlowerVirtualHub(FlowerVirtualCluster):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """
        super(FlowerVirtualHub, self).__init__(environment)

    def __str__(self):
        return "Flower Virtual Hub Cluster"

    def __repr__(self):
        return "FVH"
