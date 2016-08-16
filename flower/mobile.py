import constants


class MDC(object):
    def __init__(self, cluster):

        self.cluster = cluster

    def motion_energy(self):
        cost = constants.MOVEMENT_COST * self.cluster.tour_length
        return cost

    def communication_energy(self):

        data_volume = 0
        for cell in self.cluster.cells:
            for s in cell.segments:
                data_volume += s.total_data_volume()

        pcr = constants.ALPHA + constants.BETA * pow(constants.COMMUNICATION_RANGE, constants.DELTA)
        energy = data_volume * pcr
        return energy
