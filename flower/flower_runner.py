import logging
import statistics

from flower import data
from flower import point

logging.basicConfig(level=logging.DEBUG)


def trip(src, dst, sim):
    distance = 0

    src_cluster = next(c for c in sim.clusters + [sim.hub] if c.cluster_id == src.cluster_id)
    dst_cluster = next(c for c in sim.clusters + [sim.hub] if c.cluster_id == dst.cluster_id)

    if dst in src_cluster.tour_nodes() or src in dst_cluster.tour_nodes():
        tour = list(src_cluster.tour_nodes())
        tour = point.rotate_to_start(tour, src)
        current = src
        for p in tour[1:]:
            distance += current.distance(p)
            current = p
            if p == dst:
                break

    elif src.cluster_id == sim.hub.cluster_id:
        distance = trip(src, dst_cluster.anchor, sim) + trip(dst_cluster.anchor, dst, sim)

    elif dst_cluster.cluster_id == sim.hub.cluster_id:
        distance = trip(src, src_cluster.anchor, sim) + trip(src_cluster.anchor, dst, sim)

    else:
        distance = (trip(src, src_cluster.anchor, sim) +
                    trip(src_cluster.anchor, dst_cluster.anchor, sim) +
                    trip(dst_cluster.anchor, dst, sim))

    # logging.debug("Distance from %r to %r is %f", src, dst, distance)
    return distance


def comm_delay(src, dst, simulation_data):
    d_t = trip(src, dst, simulation_data) / simulation_data.mdc_speed

    if src.cluster == dst.cluster:
        multiplier = 1
    elif (src.cluster == simulation_data.hub) or (dst.cluster == simulation_data.hub):
        multiplier = 2
    else:
        multiplier = 3

    d_c = multiplier / simulation_data.transmission_rate * data.data(src, dst)
    delay = d_t + d_c

    # TODO: How to calculate HT?
    if src.cluster != dst.cluster:
        pass

    return delay


def max_intersegment_comm_delay(simulation_data):
    cells = simulation_data.cells
    segment_pairs = [(c1, c2) for c1 in cells for c2 in cells if c1 != c2]

    delays = [comm_delay(s, d, simulation_data) for s, d in segment_pairs]
    average_delay = statistics.mean(delays)
    maximum_delay = max(delays)
    return maximum_delay, average_delay


def mdc_energy_balance(simulation_data):
    energy = list()
    clusters = simulation_data.clusters + [simulation_data.hub]
    for c in clusters:
        e_m = c.motion_energy()
        e_c = c.communication_energy([segment for segment in simulation_data.segments if segment.cluster != c])

        mdc_energy = e_m + e_c
        energy.append(mdc_energy)

    energy_balance = statistics.pstdev(energy)
    return energy_balance


def network_lifetime(simulation_data):
    pass


def average_total_mdc_energy_consumption(simulation_data):
    pass


def buffer_space_required(simulation_data):
    pass


def run_sim(simulation_data):
    maximum, mean = max_intersegment_comm_delay(simulation_data)
    logging.info("Maximum delay is: %f", maximum)
    logging.info("Average delay is: %f", mean)

    logging.info("Energy balance is: %f", mdc_energy_balance(simulation_data))
