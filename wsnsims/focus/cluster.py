from wsnsims.core.cluster import BaseCluster


class FOCUSCluster(BaseCluster):
    def __init__(self, environment):
        """

        :param environment:
        :type environment: core.environment.Environment
        """
        super(FOCUSCluster, self).__init__(environment)
        self.intersections = list()
        self.mdc_speed = 0.  # * (pq.meter / pq.second)
        self.move_cost = 0.  # * (pq.J / pq.meter)
