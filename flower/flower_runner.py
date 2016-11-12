import collections
import logging
import math
import statistics
from collections import defaultdict

from core import data, point
from core.results import Results
from flower import point

# logging.basicConfig(level=logging.DEBUG)

# (cell, arrive_time, leave_time, upload, download)
Timestamp = collections.namedtuple('Timestamp', ['cell', 'arrive', 'leave', 'upload', 'download', 'distance'])


class FlowerRunnerError(Exception):
    pass


def trip(src, dst, sim):
    distance = 0

    src_cluster = next(c for c in sim.clusters + [sim.hub] if c.cluster_id == src.cluster_id)
    dst_cluster = next(c for c in sim.clusters + [sim.hub] if c.cluster_id == dst.cluster_id)

    # BASE CASE:
    # src and dst are in the same cluster
    if src in dst_cluster.tour_nodes():
        tour = list(dst_cluster.tour_nodes())
        tour = point.rotate_to_start(tour, src)
        current = src
        for p in tour[1:]:
            distance += current.distance(p)
            current = p
            if p == dst:
                break

    elif dst in src_cluster.tour_nodes():
        tour = list(src_cluster.tour_nodes())
        tour = point.rotate_to_start(tour, src)
        current = src
        for p in tour[1:]:
            distance += current.distance(p)
            current = p
            if p == dst:
                break

    # if two clusters share an anchor, don't need to wait for MDCk
    elif src_cluster.anchor == dst_cluster.anchor:
        distance = trip(src, src_cluster.anchor, sim) + trip(dst_cluster.anchor, dst, sim)

    # if src is in the hub, need to involve MDCk
    elif src.cluster_id == sim.hub.cluster_id:
        distance = trip(src, dst_cluster.anchor, sim) + trip(dst_cluster.anchor, dst, sim)

    # if dst is in the hub, need to involve MDCk
    elif dst_cluster.cluster_id == sim.hub.cluster_id:
        distance = trip(src, src_cluster.anchor, sim) + trip(src_cluster.anchor, dst, sim)

    # if src and dst don't share any cells - need to tour around MDCk as well
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
        d_r = hold_time(src_segment, dst_segment, sim)
    else:
        multiplier = 3
        d_r = hold_time(src_segment, dst_segment, sim)

    d_c = multiplier / sim.transmission_rate * data.data(src_segment, dst_segment)

    delay = d_t + d_c + d_r

    return delay


def segment_cluster(seg, sim):
    seg_cluster = next(c for c in sim.clusters + [sim.hub] if c.cluster_id == seg.cell.cluster_id)
    return seg_cluster


def cell_cluster(cell, sim):
    c_cluster = next(c for c in sim.clusters + [sim.hub] if c.cluster_id == cell.cluster_id)
    return c_cluster


def tour_time(clust, sim):
    cluster_tour = clust.tour_nodes()
    if len(cluster_tour) > 1:

        t_time = clust.communication_energy(sim.clusters + [sim.hub], sim.cells)
        t_time /= sim.comms_cost
        t_time /= sim.transmission_rate
        t_time += clust.tour_length / sim.mdc_speed
    else:
        t_time = 0

    return t_time


def hold_time(src_segment, dst_segment, sim):
    src_cluster = segment_cluster(src_segment, sim)
    dst_cluster = segment_cluster(dst_segment, sim)

    if src_cluster == dst_cluster:
        return 0

    if src_cluster.anchor == dst_cluster.anchor:
        return tour_time(dst_cluster, sim)

    if src_cluster == sim.hub:
        return tour_time(dst_cluster, sim)

    if dst_cluster == sim.hub:
        return tour_time(sim.hub, sim)

    if src_cluster.anchor != dst_cluster.anchor:
        return tour_time(sim.hub, sim) + tour_time(dst_cluster, sim)


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
        mdc_energy = c.total_energy(clusters, simulation_data.cells)
        energy.append(mdc_energy)

    energy_balance = statistics.pstdev(energy)
    return energy_balance


def network_lifetime(sim):
    timestamps = compute_timestamps(sim)
    lifetimes = []

    # Handle Em >> Ec special case
    if sim.em_is_large:
        all_clusters = sim.clusters

    # Handle Ec >> Em special case
    elif sim.ec_is_large or len(sim.hub.cells) == 1:
        all_clusters = sim.clusters

    else:
        all_clusters = sim.clusters + [sim.hub]

    total_tour_length = sum(c.tour_length for c in all_clusters)
    total_energy_usage = sum(sim.total_cluster_energy(c) for c in sim.clusters + [sim.hub])

    for clust in all_clusters:

        lifetime = 0

        additional_energy = 0
        if sim.em_is_large:
            part = clust.tour_length / total_tour_length
            additional_energy = sim.mdc_energy * part

        elif sim.ec_is_large or len(sim.hub.cells) == 1:
            part = sim.total_cluster_energy(clust) / total_energy_usage
            additional_energy = sim.mdc_energy * part

        remaining_energy = sim.mdc_energy + additional_energy

        clust_tour = timestamps[clust]
        idx = 0
        while remaining_energy > 0:

            cell_ts = clust_tour[idx]
            next_cell_ts = clust_tour[(idx + 1) % len(clust_tour)]

            if (idx + 1) % len(clust_tour) == 0:
                circuit_time = clust_tour[idx].leave
                for entry in clust_tour:
                    updated_arrive = entry.arrive + circuit_time
                    updated_leave = entry.leave + circuit_time
                    clust_tour[clust_tour.index(entry)] = entry._replace(arrive=updated_arrive, leave=updated_leave)

            idx = (idx + 1) % len(clust_tour)

            if math.floor(cell_ts.distance) > 0:

                motion_energy = cell_ts.distance * sim.movement_cost
                if motion_energy < remaining_energy:
                    remaining_energy -= motion_energy
                    lifetime += next_cell_ts.arrive - cell_ts.leave

                else:
                    motion_percentage = remaining_energy / motion_energy
                    survived_time = next_cell_ts.arrive - cell_ts.leave
                    survived_time *= motion_percentage
                    lifetime += survived_time
                    remaining_energy = 0

            if remaining_energy <= 0:
                break

            data_volume = cell_ts.upload + cell_ts.download
            comms_energy = data_volume * sim.comms_cost
            if comms_energy < remaining_energy:
                remaining_energy -= comms_energy
                lifetime += cell_ts.leave - cell_ts.arrive

            else:
                comms_percentage = remaining_energy / comms_energy
                survived_time = cell_ts.leave - cell_ts.arrive
                survived_time *= comms_percentage
                lifetime += survived_time
                remaining_energy = 0

        lifetimes.append((lifetime, clust.cluster_id, clust))

    return lifetimes


def average_total_mdc_energy_consumption(sim):
    all_clusters = sim.clusters + [sim.hub]
    total_energy = 0
    for clust in all_clusters:
        total_energy += clust.total_energy(all_clusters=all_clusters, all_nodes=sim.cells)

    average_energy = total_energy / len(all_clusters)
    return average_energy


# def average_total_mdc_energy_consumption(sim):
#     lifetime, _, _ = min(network_lifetime(sim))
#     timestamps = compute_timestamps(sim)
#     all_clusters = sim.clusters + [sim.hub]
#     energy_data = []
#
#     for clust in all_clusters:
#         total_energy = 0
#         remaining_time = lifetime
#         clust_tour = timestamps[clust]
#         idx = 0
#         while remaining_time > 0:
#
#             cell_ts = clust_tour[idx]
#             next_cell_ts = clust_tour[(idx + 1) % len(clust_tour)]
#
#             if (idx + 1) % len(clust_tour) == 0:
#                 circuit_time = clust_tour[idx].leave
#                 for entry in clust_tour:
#                     updated_arrive = entry.arrive + circuit_time
#                     updated_leave = entry.leave + circuit_time
#                     clust_tour[clust_tour.index(entry)] = entry._replace(arrive=updated_arrive, leave=updated_leave)
#
#             idx = (idx + 1) % len(clust_tour)
#
#             if math.floor(cell_ts.distance) > 0:
#                 motion_time = next_cell_ts.arrive - cell_ts.leave
#                 motion_energy = cell_ts.distance * sim.movement_cost
#                 if motion_time < remaining_time:
#                     remaining_time -= motion_time
#                     total_energy += motion_energy
#
#                 else:
#                     motion_percentage = remaining_time / motion_time
#                     total_energy += motion_energy * motion_percentage
#                     remaining_time = 0
#
#             if remaining_time <= 0:
#                 break
#
#             data_volume = cell_ts.upload + cell_ts.download
#             comms_energy = data_volume * sim.comms_cost
#             comms_time = cell_ts.leave - cell_ts.arrive
#
#             if comms_time < remaining_time:
#                 total_energy += comms_energy
#                 remaining_time -= comms_time
#
#             else:
#                 comms_percentage = remaining_time / comms_time
#                 total_energy += comms_energy * comms_percentage
#                 remaining_time = 0
#
#         energy_data.append((total_energy, clust.cluster_id, clust))
#
#     energies = [e for e, _, _ in energy_data]
#     mean = statistics.mean(energies)
#     return mean


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
        if clust.anchor.segments:
            total_data /= len(clust.anchor.segments)

        buffer_sizes.append(total_data)

    max_buffer_size = max(buffer_sizes)
    return max_buffer_size


def compute_timestamps(sim, rounds=1):
    timestamps = defaultdict(list)

    for clust in sim.clusters:
        timestamp = 0
        tour = clust.tour_nodes()
        local_segs = [seg for segs in [c.segments for c in clust.cells] for seg in segs]

        for _ in range(rounds):
            for idx, cell in enumerate(tour):
                if (timestamp > 0) or (len(tour) == 1):
                    # compute upload / download time
                    upload = [data.data(src, dst) for src in cell.segments for dst in sim.segments if dst != src]
                    download = [data.data(src, dst) for dst in cell.segments for src in sim.segments if dst != src]

                    upload_size = sum(upload)
                    download_size = sum(download)

                    if cell in sim.hub.cells:
                        outbound = sum(
                            data.data(src, dst) for src in local_segs for dst in sim.segments if dst not in local_segs)
                        inbound = sum(
                            data.data(src, dst) for src in sim.segments for dst in local_segs if src not in local_segs)

                        upload_size += outbound
                        download_size += inbound

                    total_size = download_size + upload_size
                    comms_time = total_size / sim.transmission_rate
                else:
                    upload_size = 0
                    download_size = 0
                    comms_time = 0

                next_cell = tour[(idx + 1) % len(tour)]

                # compute travel time to next segment
                distance = cell.distance(next_cell)
                travel_time = distance / sim.mdc_speed

                # (next_cell, arrive_time, leave_time, upload, download)
                ts = Timestamp(cell, timestamp, timestamp + comms_time, upload_size, download_size, distance)
                timestamps[clust].append(ts)
                timestamp += comms_time + travel_time

    timestamp = 0
    tour = sim.hub.tour_nodes()
    for idx, cell in enumerate(tour):

        download_size = 0
        upload_size = 0
        if cell in [c.anchor for c in sim.clusters]:

            if (timestamp > 0) or (len(tour) == 1):
                dl_clusters = [c for c in sim.clusters if c.anchor == cell]
                ul_clusters = [c for c in sim.clusters if c not in dl_clusters]

                for dl_cluster in dl_clusters:
                    local_segs = []
                    for c in dl_cluster.cells:
                        local_segs.extend(c.segments)

                    others = [s for s in sim.segments if s not in local_segs]
                    download_size += sum(
                        data.data(src, dst) for src in local_segs for dst in others)

                for ul_cluster in ul_clusters:
                    local_segs = []
                    for c in ul_cluster.cells:
                        local_segs.extend(c.segments)

                    others = [s for s in sim.segments if s not in local_segs]
                    upload_size += sum(
                        data.data(src, dst) for src in others for dst in local_segs)

                total_size = download_size + upload_size
                comms_time = total_size / sim.transmission_rate
            else:
                upload_size = 0
                download_size = 0
                comms_time = 0

        else:
            upload = [data.data(src, dst) for src in cell.segments for dst in sim.segments if dst != src]
            download = [data.data(src, dst) for dst in cell.segments for src in sim.segments if dst != src]

            upload_size += sum(upload)
            download_size += sum(download)

        next_cell = tour[(idx + 1) % len(tour)]

        # compute travel time to next segment
        distance = cell.distance(next_cell)
        travel_time = distance / sim.mdc_speed

        # (next_cell, arrive_time, leave_time, upload, download, distance)
        ts = Timestamp(cell, timestamp, timestamp + comms_time, upload_size, download_size, distance)
        timestamps[sim.hub].append(ts)
        timestamp += comms_time + travel_time

    return timestamps


def run_sim(simulation_data):
    # timestamps = compute_timestamps(simulation_data, 1)
    # for k, v in timestamps.items():
    #     logging.info(str(k) + '\n' + '\n'.join([str(ts) for ts in v]) + '\n')

    max_delay, mean = max_intersegment_comm_delay(simulation_data)
    logging.info("Maximum delay is: %f", max_delay)
    # logging.info("Average delay is: %f", mean)

    energy_balance = mdc_energy_balance(simulation_data)
    logging.info("Energy balance is: %f", energy_balance)

    # lifetime, _, _ = min(network_lifetime(simulation_data))
    # logging.info("Network lifetime is: %f", lifetime)

    average_energy = average_total_mdc_energy_consumption(simulation_data)
    logging.info("Average MDC energy consumption: %f", average_energy)

    # max_buffer_size = buffer_space_required(simulation_data)
    # logging.info("Maximum buffer size: %f", max_buffer_size)

    # results = Results(max_delay, energy_balance, lifetime, average_energy, max_buffer_size)
    results = Results(max_delay, energy_balance, 0, average_energy, 0)

    for r in results:
        if math.isnan(r):
            raise FlowerRunnerError("Found a nan value")

        if math.isinf(r):
            raise FlowerRunnerError("Found an info value")

    return results
