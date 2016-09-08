import logging

import matplotlib.pyplot as plt

from flower import mobile

logging.basicConfig(level=logging.DEBUG)


def max_intersegment_comm_delay(simulation_data):
    pass


def mdc_energy_balance(simulation_data):
    pass


def network_lifetime(simulation_data):
    pass


def average_total_mdc_energy_consumption(simulation_data):
    pass


def buffer_space_required(simulation_data):
    pass


def initialize_mdcs(simulation_data):
    mdcs = [mobile.MDC(c) for c in simulation_data.clusters]
    mdcs.append(mobile.MDC(simulation_data.centroid))
    return mdcs


def run_sim(simulation_data):
    mdcs = initialize_mdcs(simulation_data)

    elapsed_time = 0.0
    while True:
        if not elapsed_time % 100:
            plot(mdcs, 'bo')
            plot(simulation_data.centroid.tour(), 'r')
            plot(simulation_data.segments, 'ro')

            for c in simulation_data.clusters:
                plot(c.tour(), 'g')

            plt.show()

        [mdc.update() for mdc in mdcs]

        if any(mdc.is_dead for mdc in mdcs):
            logging.info("Simulation finished at %f", elapsed_time)
            break

        elapsed_time += 1.0


def plot(points, *args, **kwargs):
    x = [p.x for p in points]
    y = [p.y for p in points]
    plt.plot(x, y, *args, **kwargs)
