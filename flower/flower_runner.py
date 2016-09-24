import collections
import logging
import statistics
from collections import defaultdict

from flower import constants
from flower import data
from flower import point

logging.basicConfig(level=logging.DEBUG)

# (cell, arrive_time, leave_time, upload, download)
Timestamp = collections.namedtuple('Timestamp', ['cell', 'arrive', 'leave', 'upload', 'download'])


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


def comm_delay(src_segment, dst_segment, sim):
    d_t = trip(src_segment.cell, dst_segment.cell, sim) / sim.mdc_speed

    if src_segment.cell.cluster_id == dst_segment.cell.cluster_id:
        multiplier = 1
        d_r = 0
    elif (src_segment.cell.cluster_id == sim.hub.cluster_id) or (dst_segment.cell.cluster_id == sim.hub.cluster_id):
        multiplier = 2
        d_r = holding_time(src_segment, dst_segment, sim)
    else:
        multiplier = 3
        d_r = holding_time(src_segment, dst_segment, sim)

    d_c = multiplier / sim.transmission_rate * data.data(src_segment, dst_segment)

    delay = d_t + d_c + d_r

    return delay


def segment_cluster(seg, sim):
    seg_cluster = next(c for c in sim.clusters + [sim.hub] if c.cluster_id == seg.cell.cluster_id)
    return seg_cluster


def cell_cluster(cell, sim):
    c_cluster = next(c for c in sim.clusters + [sim.hub] if c.cluster_id == cell.cluster_id)
    return c_cluster


def holding_time(src_segment, dst_segment, sim):
    timestamps = compute_timestamps(sim)

    # Determine if src and dst cells share an anchor
    src_cluster = segment_cluster(src_segment, sim)
    dst_cluster = segment_cluster(dst_segment, sim)

    if src_cluster == sim.hub:
        dst_anchor = dst_cluster.anchor
        src_anchor = dst_anchor
    elif dst_cluster == sim.hub:
        src_anchor = src_cluster.anchor
        dst_anchor = src_anchor
    else:
        src_anchor = segment_cluster(src_segment, sim).anchor
        dst_anchor = segment_cluster(dst_segment, sim).anchor

    if src_anchor == dst_anchor:
        src_times = timestamps[src_cluster]
        dst_times = timestamps[dst_cluster]

        src_mdc_ts = next(ts for ts in src_times if ts.cell == src_anchor)
        dst_mdc_ts = next(ts for ts in dst_times if ts.cell == dst_anchor)

        if dst_mdc_ts.leave < src_mdc_ts.arrive:
            dst_mdc_total = max(dst_times, key=lambda x: x.leave).leave
            holding = (dst_mdc_total + dst_mdc_ts.arrive) - src_mdc_ts.arrive
        else:
            holding = dst_mdc_ts.arrive - src_mdc_ts.arrive

    else:
        src_times = timestamps[src_cluster]
        dst_times = timestamps[dst_cluster]
        hub_times = timestamps[sim.hub]

        src_mdc_ts = next(ts for ts in src_times if ts.cell == src_anchor)
        dst_mdc_ts = next(ts for ts in dst_times if ts.cell == dst_anchor)
        hub_src_mdc_ts = next(ts for ts in hub_times if ts.cell == src_anchor)
        hub_dst_mdc_ts = next(ts for ts in hub_times if ts.cell == dst_anchor)

        if dst_mdc_ts.leave < hub_dst_mdc_ts.arrive:
            dst_mdc_total = max(dst_times, key=lambda x: x.leave).leave
            hold_2 = (dst_mdc_total + dst_mdc_ts.arrive) - hub_dst_mdc_ts.arrive
        else:
            hold_2 = dst_mdc_ts.arrive - src_mdc_ts.arrive

        if hub_src_mdc_ts.leave < src_mdc_ts.arrive:
            hub_src_total = max(hub_times, key=lambda x: x.leave).leave
            hold_1 = (hub_src_total + hub_src_mdc_ts.arrive) - src_mdc_ts.arrive
        else:
            hold_1 = dst_mdc_ts.arrive - src_mdc_ts.arrive

        holding = hold_1 + hold_2

    return holding


def max_intersegment_comm_delay(sim):
    cells = sim.segments
    segment_pairs = [(s1, s2) for s1 in cells for s2 in cells if s1 != s2]

    delays = [comm_delay(s, d, sim) for s, d in segment_pairs]
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
    lifetimes = list()
    clusters = simulation_data.clusters + [simulation_data.hub]
    for c in clusters:

        e_m = c.motion_energy()
        e_c = c.communication_energy([segment for segment in simulation_data.segments if segment.cluster != c])

        if len(c.cells) == 1:
            # Given mdc_energy Joules, how many bits can this MDC transmit?
            total_energy = simulation_data.mdc_energy
            one_bit_energy = (constants.ALPHA + constants.BETA * pow(constants.COMMUNICATION_RANGE, constants.DELTA))
            total_bits = total_energy / one_bit_energy

            # How long will that take?
            transmission_rate = simulation_data.transmission_rate
            transmission_rate *= 1024 * 1024  # Convert from Mbps to bits-per-second
            transmission_time = total_bits / transmission_rate

            lifetimes.append((transmission_time, c))

        else:
            mdc_energy_per_cycle = e_m + e_c
            total_cycle_count = simulation_data.mdc_energy / mdc_energy_per_cycle
            mdc_travel_distance = c.tour_length * total_cycle_count
            mdc_tour_time = mdc_travel_distance / simulation_data.mdc_speed
            lifetimes.append((mdc_tour_time, c))

    return lifetimes


def average_total_mdc_energy_consumption(simulation_data):
    lifetimes = network_lifetime(simulation_data)
    shortest_lifetime, _ = min(lifetimes)

    cell_lifetimes = {cell: lifetime for lifetime, cell in lifetimes}
    energies = list()
    clusters = simulation_data.clusters + [simulation_data.hub]
    for c in clusters:
        total_energy = simulation_data.mdc_energy
        lifetime = cell_lifetimes[c]

        percent_completed = shortest_lifetime / lifetime
        percent_energy = total_energy * percent_completed
        energies.append(percent_energy)

    average_energy = statistics.mean(energies)
    return average_energy


def buffer_space_required(sim):
    timestamps = compute_timestamps(sim)
    hub_times = list(timestamps[sim.hub])
    max_hub_time = hub_times[-1:][0].arrive

    buffer_sizes = []

    for clust in sim.clusters:

        mdc_times = []
        max_mdc_time = 0
        rounds = 1
        while max_mdc_time < max_hub_time:
            timestamps = compute_timestamps(sim, rounds=rounds)
            mdc_times = timestamps[clust]
            max_mdc_time = mdc_times[-1:][0].arrive
            rounds += 1

        mdc_hub_visits = [ts.cell for ts in mdc_times if ts.cell == clust.anchor]
        arrivals = max(1, len(mdc_hub_visits))

        segs = []
        for c in clust.cells:
            segs.extend(c.segments)

        intercluster_outbound = [data.data(src, dst) for src in segs for dst in sim.segments if dst not in segs]
        intercluster_inbound = [data.data(src, dst) for src in sim.segments if src not in segs for dst in segs]

        total_data = sum(intercluster_outbound) * arrivals
        total_data += sum(intercluster_inbound)
        total_data /= len(clust.anchor.segments)

        buffer_sizes.append(total_data)

    max_buffer_size = max(buffer_sizes)
    return max_buffer_size


def compute_timestamps(sim, rounds=1):
    timestamps = defaultdict(list)

    for c in sim.clusters + [sim.hub]:
        tour = c.tour_nodes()

        timestamp = 0
        for _ in range(rounds):
            current_segment = tour[0]
            for cell in tour[1:]:
                # compute upload / download time
                download_size = sum(
                    data.data(seg, dst) for seg in cell.segments for dst in sim.segments if dst not in cell.segments)
                upload_size = sum(
                    data.data(src, seg) for src in sim.segments for seg in cell.segments if src not in cell.segments)

                total_size = download_size + upload_size
                comms_time = total_size / sim.transmission_rate

                # compute travel time to next segment
                distance = current_segment.distance(cell)
                travel_time = distance / sim.mdc_speed

                # (cell, arrive_time, leave_time, upload, download)
                ts = Timestamp(current_segment, timestamp, timestamp + comms_time, upload_size, download_size)
                timestamps[c].append(ts)
                timestamp += comms_time + travel_time
                current_segment = cell

    return timestamps


def run_sim(simulation_data):
    timestamps = compute_timestamps(simulation_data, 1)
    logging.info("Timestamps:\n%s", timestamps)

    maximum, mean = max_intersegment_comm_delay(simulation_data)
    logging.info("Maximum delay is: %f", maximum)
    # logging.info("Average delay is: %f", mean)

    logging.info("Energy balance is: %f", mdc_energy_balance(simulation_data))

    shortest, _ = min(network_lifetime(simulation_data))
    logging.info("Network lifetime is: %f", shortest)
    logging.info("Average MDC energy consumption: %f", average_total_mdc_energy_consumption(simulation_data))

    max_buffer_size = buffer_space_required(simulation_data)
    logging.info("Maximum buffer size: %f", max_buffer_size)
