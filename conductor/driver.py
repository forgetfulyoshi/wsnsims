import csv
import datetime
import logging
import multiprocessing
import os
import time
from collections import namedtuple

import numpy as np
import quantities as pq

from conductor import sim_inputs
from core.environment import Environment
from core.results import Results
from flower.flower_sim import FLOWER
from focus.focus_sim import FOCUS
from minds.minds_sim import MINDS
from tocs.tocs_sim import TOCS

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

RUNS = 1

Parameters = namedtuple('Parameters',
                        ['segment_count', 'mdc_count', 'isdva', 'isdvsd',
                         'radio_range'])


def average_results(results):
    mean_max_delay = np.mean([x.max_delay for x in results])
    mean_balance = np.mean([x.balance for x in results])
    mean_lifetime = np.mean([x.lifetime for x in results])
    mean_energy = np.mean([x.ave_energy for x in results])
    mean_buffer = np.mean([x.max_buffer for x in results])

    result = Results(mean_max_delay, mean_balance, mean_lifetime, mean_energy,
                     mean_buffer)
    return result


# logger.debug("Maximum comms delay: {}".format(
#     runner.maximum_communication_delay()))
# logger.debug("Energy balance: {}".format(runner.energy_balance()))
# logger.debug("Average energy: {}".format(runner.average_energy()))
# logger.debug("Max buffer size: {}".format(runner.max_buffer_size()))

def run_tocs(parameters, locs):
    tocs_sim = TOCS(locs)
    logger.debug(
        "Starting ToCS at {}".format(datetime.datetime.now().isoformat()))
    logger.debug("Using {}".format(parameters))
    start = time.time()
    runner = tocs_sim.run()

    results = Results(runner.maximum_communication_delay(),
                      runner.energy_balance(),
                      0.,
                      runner.average_energy(),
                      runner.max_buffer_size())

    logger.debug("Finished ToCS in {} seconds".format(time.time() - start))
    return results


def run_flower(parameters, locs):
    flower_sim = FLOWER(locs)
    logger.debug(
        "Starting FLOWER at {}".format(datetime.datetime.now().isoformat()))
    logger.debug("Using {}".format(parameters))
    start = time.time()
    runner = flower_sim.run()

    results = Results(runner.maximum_communication_delay(),
                      runner.energy_balance(),
                      0.,
                      runner.average_energy(),
                      runner.max_buffer_size())

    logger.debug("Finished FLOWER in {} seconds".format(time.time() - start))
    return results


def run_minds(parameters, locs):
    minds_sim = MINDS(locs)
    logger.debug(
        "Starting MINDS at {}".format(datetime.datetime.now().isoformat()))
    logger.debug("Using {}".format(parameters))
    start = time.time()
    runner = minds_sim.run()

    results = Results(runner.maximum_communication_delay(),
                      runner.energy_balance(),
                      0.,
                      runner.average_energy(),
                      runner.max_buffer_size())

    logger.debug("Finished MINDS in {} seconds".format(time.time() - start))
    return results


def run_focus(parameters, locs):
    focus_sim = FOCUS(locs)
    logger.debug(
        "Starting FOCUS at {}".format(datetime.datetime.now().isoformat()))
    logger.debug("Using {}".format(parameters))
    start = time.time()
    runner = focus_sim.run()

    results = Results(runner.maximum_communication_delay(),
                      runner.energy_balance(),
                      0.,
                      runner.average_energy(),
                      runner.max_buffer_size())

    logger.debug("Finished FOCUS in {} seconds".format(time.time() - start))
    return results


def run(parameters):
    tocs_results = []
    flower_results = []
    minds_results = [Results(0, 0, 0, 0, 0)]
    focus_results = [Results(0, 0, 0, 0, 0)]

    env = Environment()
    env.segment_count = parameters.segment_count
    env.mdc_count = parameters.mdc_count
    env.isdva = parameters.isdva * pq.mebi * pq.bit
    env.isdvsd = parameters.isdvsd
    env.comms_range = parameters.radio_range * pq.m

    # MAX_PROCESSES = 64
    MAX_PROCESSES = 4
    with multiprocessing.Pool(processes=MAX_PROCESSES) as pool:

        while len(tocs_results) <= RUNS or \
                        len(flower_results) <= RUNS:
            # len(minds_results) <= RUNS or \
            # len(focus_results) <= RUNS:

            tocs_runners = MAX_PROCESSES // 4
            flower_runners = MAX_PROCESSES // 4
            minds_runners = 0  # MAX_PROCESSES // 4
            focus_runners = 0  # MAX_PROCESSES // 4

            locs = np.random.rand(env.segment_count, 2) * env.grid_height

            tocs_workers = []
            flower_workers = []
            minds_workers = []
            focus_workers = []

            if len(tocs_results) <= RUNS:
                tocs_workers = [pool.apply_async(run_tocs, (parameters, locs))
                                for
                                _ in range(tocs_runners)]

            if len(flower_results) <= RUNS:
                flower_workers = [
                    pool.apply_async(run_flower, (parameters, locs))
                    for _ in range(flower_runners)]

            if len(minds_results) <= RUNS:
                minds_workers = [
                    pool.apply_async(run_minds, (parameters, locs))
                    for _ in range(minds_runners)]

            if len(focus_results) <= RUNS:
                focus_workers = [
                    pool.apply_async(run_focus, (parameters, locs))
                    for _ in range(focus_runners)]

            for result in tocs_workers:
                try:
                    tocs_results.append(result.get(timeout=100))
                except Exception:
                    logger.exception('ToCS Exception')
                    continue

            for result in flower_workers:
                try:
                    flower_results.append(result.get(timeout=100))
                except Exception:
                    logger.exception('FLOWER Exception')
                    continue

            for result in minds_workers:
                try:
                    minds_results.append(result.get(timeout=100))
                except Exception:
                    logger.exception('MIDNS Exception')
                    continue

            for result in focus_workers:
                try:
                    focus_results.append(result.get(timeout=100))
                except Exception:
                    logger.exception('FOCUS Exception')
                    continue

    mean_tocs_results = average_results(tocs_results[:RUNS])
    mean_flower_results = average_results(flower_results[:RUNS])
    mean_minds_results = average_results(minds_results[:RUNS])
    mean_focus_results = average_results(focus_results[:RUNS])

    return (mean_tocs_results, mean_flower_results, mean_minds_results,
            mean_focus_results)


def main():
    seed = int(time.time())
    logger.debug("Random seed is %s", seed)
    np.random.seed(seed)

    parameters = [Parameters._make(p) for p in sim_inputs.conductor_params]

    headers = ['max_delay', 'balance', 'lifetime', 'ave_energy', 'max_buffer']
    # noinspection PyProtectedMember
    headers += parameters[0]._fields

    results_dir = os.path.join('C:', os.sep, 'results')
    if not os.path.isdir(results_dir):
        os.makedirs(results_dir)

    flower_filepath = os.path.join(results_dir, 'flower.csv')
    tocs_filepath = os.path.join(results_dir, 'tocs.csv')
    minds_filepath = os.path.join(results_dir, 'minds.csv')
    focus_filepath = os.path.join(results_dir, 'focus.csv')

    flower_exists = os.path.isfile(flower_filepath)
    tocs_exists = os.path.isfile(tocs_filepath)
    minds_exists = os.path.isfile(minds_filepath)
    focus_exists = os.path.isfile(focus_filepath)

    with open(tocs_filepath, 'w', newline='') as tocs_csv, \
            open(flower_filepath, 'w', newline='') as flower_csv, \
            open(minds_filepath, 'w', newline='') as minds_csv, \
            open(focus_filepath, 'w', newline='') as focus_csv:

        tocs_writer = csv.DictWriter(tocs_csv, fieldnames=headers)
        flower_writer = csv.DictWriter(flower_csv, fieldnames=headers)
        minds_writer = csv.DictWriter(minds_csv, fieldnames=headers)
        focus_writer = csv.DictWriter(focus_csv, fieldnames=headers)

        if not flower_exists:
            flower_writer.writeheader()
        if not tocs_exists:
            tocs_writer.writeheader()
        if not minds_exists:
            minds_writer.writeheader()
        if not focus_exists:
            focus_writer.writeheader()

        for parameter in parameters:
            tocs_res, flower_res, minds_res, focus_res = run(parameter)

            # noinspection PyProtectedMember,PyProtectedMember
            tocs_writer.writerow(
                {**tocs_res._asdict(), **parameter._asdict()})

            # noinspection PyProtectedMember,PyProtectedMember
            flower_writer.writerow(
                {**flower_res._asdict(), **parameter._asdict()})

            # noinspection PyProtectedMember,PyProtectedMember
            minds_writer.writerow(
                {**minds_res._asdict(), **parameter._asdict()})

            # noinspection PyProtectedMember,PyProtectedMember
            focus_writer.writerow(
                {**focus_res._asdict(), **parameter._asdict()})


if __name__ == '__main__':
    main()
