import constants


class MDC(object):
    def __init__(self, cluster):
        self.cluster = cluster
        self._cell = None
        self.moved = False

    @property
    def cell(self):
        return self._cell

    @cell.setter
    def cell(self, value):
        self.moved = True
        self._cell = value

