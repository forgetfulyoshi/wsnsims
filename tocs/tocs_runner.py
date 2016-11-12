import collections
import logging
import math
import statistics
from collections import defaultdict

from core import data, point
from core.results import Results

# logging.basicConfig(level=logging.DEBUG)

Timestamp = collections.namedtuple('Timestamp', ['segment', 'arrive', 'leave', 'upload', 'download', 'distance'])


class ToCSRunnerError(Exception):
    pass


def trip(src, dst, sim):
    distance = 0

    if src in dst.cluster.tour_nodes():
        tour = list(dst.cluster.tour_nodes())
        tour = point.rotate_to_start(tour, src)
        current = src
        for p in tour[1:]:
            distance += current.distance(p)
            current = p
            if p == dst:
                break

    elif dst in src.cluster.tour_nodes():
        tour = list(src.cluster.tour_nodes())
        tour = point.rotate_to_start(tour, src)
        current = src
        for p in tour[1:]:
            distance += current.distance(p)
            current = p
            if p == dst:
                break

    elif src.cluster == sim.centroid:
        distance = trip(src, dst.cluster.rendezvous_point, sim) + trip(dst.cluster.rendezvous_point, dst, sim)

    elif dst.cluster == sim.centroid:
        distance = trip(src, src.cluster.rendezvous_point, sim) + trip(src.cluster.rendezvous_point, dst, sim)

    else:
        distance = (trip(src, src.cluster.rendezvous_point, sim) +
                    trip(src.cluster.rendezvous_point, dst.cluster.rendezvous_point, sim) +
                    trip(dst.cluster.rendezvous_point, dst, sim))

    logging.debug("Distance from %r to %r is %f", src, dst, distance)
    return distance


def comm_delay(src, dst, sim):
    d_t = trip(src, dst, sim) / sim.mdc_speed

    if src.cluster == dst.cluster:
        multiplier = 1
        d_r = 0
    elif (src.cluster == sim.centroid) or (dst.cluster == sim.centroid):
        multiplier = 2
        d_r = hold_time(src, dst, sim)
    else:
        multiplier = 3
        d_r = hold_time(src, dst, sim)

    d_c = multiplier / sim.transmission_rate * data.data(src, dst)
    delay = d_t + d_c + d_r

    return delay


def segment_cluster(seg, sim=None):
    seg_cluster = seg.cluster
    return seg_cluster


def tour_time(clust, sim):
    cluster_tour = clust.tour_nodes()
    if len(cluster_tour) > 1:

        t_time = clust.communication_energy(sim.clusters + [sim.centroid], sim.segments)
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

    elif src_cluster == sim.centroid:
        return tour_time(dst_cluster, sim)

    elif dst_cluster == sim.centroid:
        return tour_time(sim.centroid, sim)

    else:
        return tour_time(sim.centroid, sim) + tour_time(dst_cluster, sim)


def holding_time(src_segment, dst_segment, sim):
    timestamps = compute_timestamps(sim)

    # Determine if src and dst clusters share an rendezvous
    src_cluster = segment_cluster(src_segment, sim)
    dst_cluster = segment_cluster(dst_segment, sim)

    if src_cluster == sim.centroid:
        dst_rendezvous = dst_cluster.rendezvous_point
        src_rendezvous = dst_rendezvous
    elif dst_cluster == sim.centroid:
        src_rendezvous = src_cluster.rendezvous_point
        dst_rendezvous = src_rendezvous
    else:
        src_rendezvous = segment_cluster(src_segment, sim).rendezvous_point
        dst_rendezvous = segment_cluster(dst_segment, sim).rendezvous_point

    if src_rendezvous == dst_rendezvous:
        src_times = timestamps[src_cluster]
        dst_times = timestamps[dst_cluster]

        src_mdc_ts = next(ts for ts in src_times if ts.segment == src_rendezvous)
        dst_mdc_ts = next(ts for ts in dst_times if ts.segment == dst_rendezvous)

        if dst_mdc_ts.leave < src_mdc_ts.arrive:
            dst_mdc_total = max(dst_times, key=lambda x: x.leave).leave
            holding = (dst_mdc_total + dst_mdc_ts.arrive) - src_mdc_ts.arrive
        else:
            holding = dst_mdc_ts.arrive - src_mdc_ts.arrive

    else:
        src_times = timestamps[src_cluster]
        dst_times = timestamps[dst_cluster]
        centroid_times = timestamps[sim.centroid]

        src_mdc_ts = next(ts for ts in src_times if ts.segment == src_rendezvous)
        dst_mdc_ts = next(ts for ts in dst_times if ts.segment == dst_rendezvous)
        centroid_src_mdc_ts = next(ts for ts in centroid_times if ts.segment == src_rendezvous)
        centroid_dst_mdc_ts = next(ts for ts in centroid_times if ts.segment == dst_rendezvous)

        if dst_mdc_ts.leave < centroid_dst_mdc_ts.arrive:
            dst_mdc_total = max(dst_times, key=lambda x: x.leave).leave
            hold_2 = (dst_mdc_total + dst_mdc_ts.arrive) - centroid_dst_mdc_ts.arrive
        else:
            hold_2 = dst_mdc_ts.arrive - src_mdc_ts.arrive

        if centroid_src_mdc_ts.leave < src_mdc_ts.arrive:
            centroid_src_total = max(centroid_times, key=lambda x: x.leave).leave
            hold_1 = (centroid_src_total + centroid_src_mdc_ts.arrive) - src_mdc_ts.arrive
        else:
            hold_1 = dst_mdc_ts.arrive - src_mdc_ts.arrive

        holding = hold_1 + hold_2

    return holding


def max_intersegment_comm_delay(simulation_data):
    segments = simulation_data.segments
    segment_pairs = [(s1, s2) for s1 in segments for s2 in segments if s1 != s2]

    delays = [comm_delay(s, d, simulation_data) for s, d in segment_pairs]
    average_delay = statistics.mean(delays)
    maximum_delay = max(delays)
    return maximum_delay, average_delay


def mdc_energy_balance(simulation_data):
    energy = list()
    clusters = simulation_data.clusters + [simulation_data.centroid]
    for c in clusters:
        mdc_energy = c.total_energy(clusters, simulation_data.segments)
        energy.append(mdc_energy)

    energy_balance = statistics.pstdev(energy)
    return energy_balance


def network_lifetime(sim):
    timestamps = compute_timestamps(sim)
    all_clusters = sim.clusters + [sim.centroid]
    lifetimes = []

    for clust in all_clusters:
        lifetime = 0
        remaining_energy = sim.mdc_energy
        clust_tour = timestamps[clust]
        idx = 0
        while remaining_energy > 0:

            segment_ts = clust_tour[idx]
            next_segment_ts = clust_tour[(idx + 1) % len(clust_tour)]

            if (idx + 1) % len(clust_tour) == 0:
                circuit_time = clust_tour[idx].leave
                for entry in clust_tour:
                    updated_arrive = entry.arrive + circuit_time
                    updated_leave = entry.leave + circuit_time
                    clust_tour[clust_tour.index(entry)] = entry._replace(arrive=updated_arrive, leave=updated_leave)

            idx = (idx + 1) % len(clust_tour)

            if segment_ts.distance > 0:
                motion_energy = segment_ts.distance * sim.movement_cost
                if motion_energy < remaining_energy:
                    remaining_energy -= motion_energy
                    lifetime += next_segment_ts.arrive - segment_ts.leave

                else:
                    motion_percentage = remaining_energy / motion_energy
                    survived_time = next_segment_ts.arrive - segment_ts.leave
                    survived_time *= motion_percentage
                    lifetime += survived_time
                    remaining_energy = 0

            if remaining_energy <= 0:
                break

            data_volume = segment_ts.upload + segment_ts.download
            comms_energy = data_volume * sim.comms_cost
            if comms_energy < remaining_energy:
                remaining_energy -= comms_energy
                lifetime += segment_ts.leave - segment_ts.arrive

            else:
                comms_percentage = remaining_energy / comms_energy
                survived_time = segment_ts.leave - segment_ts.arrive
                survived_time *= comms_percentage
                lifetime += survived_time
                remaining_energy = 0

        lifetimes.append((lifetime, clust.cluster_id, clust))

    return lifetimes


def average_total_mdc_energy_consumption(sim):
    all_clusters = sim.clusters + [sim.centroid]
    total_energy = 0
    for clust in all_clusters:
        total_energy += clust.total_energy(all_clusters=all_clusters, all_nodes=sim.segments)

    average_energy = total_energy / len(all_clusters)
    return average_energy


# def average_total_mdc_energy_consumption(sim):
#     lifetime, _, _ = min(network_lifetime(sim))
#     timestamps = compute_timestamps(sim)
#     all_clusters = sim.clusters + [sim.centroid]
#     energy_data = []
#
#     for clust in all_clusters:
#         total_energy = 0
#         remaining_time = lifetime
#         clust_tour = timestamps[clust]
#         idx = 0
#         while remaining_time > 0:
#
#             seg_ts = clust_tour[idx]
#             next_seg_ts = clust_tour[(idx + 1) % len(clust_tour)]
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
#             if seg_ts.distance > 0:
#                 motion_time = next_seg_ts.arrive - seg_ts.leave
#                 motion_energy = seg_ts.distance * sim.movement_cost
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
#             data_volume = seg_ts.upload + seg_ts.download
#             comms_energy = data_volume * sim.comms_cost
#             comms_time = seg_ts.leave - seg_ts.arrive
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
    centroid_times = list(timestamps[sim.centroid])
    max_centroid_time = centroid_times[-1:][0].arrive

    buffer_sizes = []

    for clust in sim.clusters:

        mdc_times = []
        max_mdc_time = 0
        rounds = 1
        while max_mdc_time < max_centroid_time:
            timestamps = compute_timestamps(sim, rounds=rounds)
            mdc_times = timestamps[clust]
            max_mdc_time = mdc_times[-1:][0].arrive
            rounds += 1

        mdc_centroid_visits = [ts.segment for ts in mdc_times if ts.segment == clust.rendezvous_point]
        arrivals = max(1, len(mdc_centroid_visits))

        segs = clust.segments
        intercluster_outbound = [data.data(src, dst) for src in segs for dst in sim.segments if dst not in segs]
        intercluster_inbound = [data.data(src, dst) for src in sim.segments if src not in segs for dst in segs]

        total_data = sum(intercluster_outbound) * arrivals
        total_data += sum(intercluster_inbound)

        buffer_sizes.append(total_data)

    max_buffer_size = max(buffer_sizes)
    return max_buffer_size


def compute_timestamps(sim, rounds=1):
    timestamps = defaultdict(list)

    for clust in sim.clusters:
        timestamp = 0
        tour = clust.tour_nodes()

        segs = clust.segments

        for _ in range(rounds):
            for idx, seg in enumerate(tour):
                if (timestamp > 0) or (len(tour) == 1):
                    # compute upload / download time
                    upload = [data.data(seg, dst) for dst in sim.segments if dst != seg]
                    download = [data.data(src, seg) for src in sim.segments if src != seg]

                    upload_size = sum(upload)
                    download_size = sum(download)

                    if seg in sim.centroid.segments:
                        outbound = sum(
                            data.data(src, dst) for src in clust.segments for dst in sim.segments if
                            dst not in clust.segments)
                        inbound = sum(
                            data.data(src, dst) for src in sim.segments for dst in clust.segments if
                            src not in clust.segments)

                        upload_size += outbound
                        download_size += inbound

                    total_size = download_size + upload_size
                    comms_time = total_size / sim.transmission_rate

                else:
                    upload_size = 0
                    download_size = 0
                    comms_time = 0

                next_segment = tour[(idx + 1) % len(tour)]

                # compute travel time to next segment
                distance = seg.distance(next_segment)
                travel_time = distance / sim.mdc_speed

                # (next_segment, arrive_time, leave_time, upload, download)
                ts = Timestamp(seg, timestamp, timestamp + comms_time, upload_size, download_size, distance)
                timestamps[clust].append(ts)
                timestamp += comms_time + travel_time

    timestamp = 0
    tour = sim.centroid.tour_nodes()
    for idx, seg in enumerate(tour):

        download_size = 0
        upload_size = 0

        if seg in sim.centroid.rendezvous_points.values():

            if (timestamp > 0) or (len(tour) == 1):
                dl_clusters = [c for c in sim.clusters if c.rendezvous_point == seg]
                ul_clusters = [c for c in sim.clusters if c not in dl_clusters]

                for dl_cluster in dl_clusters:
                    segs = dl_cluster.segments
                    others = [s for s in sim.segments if s not in segs]
                    download_size += sum(
                        data.data(src, dst) for src in segs for dst in others)

                for ul_cluster in ul_clusters:
                    segs = ul_cluster.segments
                    others = [s for s in sim.segments if s not in segs]
                    upload_size += sum(
                        data.data(src, dst) for src in others for dst in segs)

                total_size = download_size + upload_size
                comms_time = total_size / sim.transmission_rate

            else:
                upload_size = 0
                download_size = 0
                comms_time = 0

        else:
            upload = [data.data(seg, dst) for dst in sim.segments if dst != seg]
            download = [data.data(src, seg) for src in sim.segments if src != seg]

            upload_size += sum(upload)
            download_size += sum(download)

        next_segment = tour[(idx + 1) % len(tour)]

        # compute travel time to next segment
        distance = seg.distance(next_segment)
        travel_time = distance / sim.mdc_speed

        # (next_segment, arrive_time, leave_time, upload, download, distance)
        ts = Timestamp(seg, timestamp, timestamp + comms_time, upload_size, download_size, distance)
        timestamps[sim.centroid].append(ts)
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
            raise ToCSRunnerError("Found a nan value")

        if math.isinf(r):
            raise ToCSRunnerError("Found an info value")

    return results