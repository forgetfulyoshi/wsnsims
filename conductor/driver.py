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

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

MAX_PROCESSES = 8
RUNS = 30

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


def run_tocs(parameters):
    """

    :param parameters:
    :type parameters: Parameters
    :return:
    """

    env = Environment()
    env.segment_count = parameters.segment_count
    env.mdc_count = parameters.mdc_count
    env.isdva = parameters.isdva * pq.mebi * pq.bit
    env.isdvsd = parameters.isdvsd
    env.comms_range = parameters.radio_range * env.comms_range.units
    tocs_sim = TOCS(env)

    print(
        "Starting ToCS at {}".format(datetime.datetime.now().isoformat()))
    print("Using {}".format(parameters))
    start = time.time()
    runner = tocs_sim.run()

    results = Results(runner.maximum_communication_delay(),
                      runner.energy_balance(),
                      0.,
                      runner.average_energy(),
                      runner.max_buffer_size())

    print("Finished ToCS in {} seconds".format(time.time() - start))
    return results


def run_flower(parameters):
    """

     :param parameters:
     :type parameters: Parameters
     :return:
     """

    env = Environment()
    env.segment_count = parameters.segment_count
    env.mdc_count = parameters.mdc_count
    env.isdva = parameters.isdva * pq.mebi * pq.bit
    env.isdvsd = parameters.isdvsd
    env.comms_range = parameters.radio_range * env.comms_range.units

    flower_sim = FLOWER(env)
    print(
        "Starting FLOWER at {}".format(datetime.datetime.now().isoformat()))
    print("Using {}".format(parameters))
    start = time.time()
    runner = flower_sim.run()

    results = Results(runner.maximum_communication_delay(),
                      runner.energy_balance(),
                      0.,
                      runner.average_energy(),
                      runner.max_buffer_size())

    print("Finished FLOWER in {} seconds".format(time.time() - start))
    return results


def run_minds(parameters):
    """

     :param parameters:
     :type parameters: Parameters
     :return:
     """

    env = Environment()
    env.segment_count = parameters.segment_count
    env.mdc_count = parameters.mdc_count
    env.isdva = parameters.isdva * pq.mebi * pq.bit
    env.isdvsd = parameters.isdvsd
    env.comms_range = parameters.radio_range * env.comms_range.units

    minds_sim = MINDS(env)
    print(
        "Starting MINDS at {}".format(datetime.datetime.now().isoformat()))
    print("Using {}".format(parameters))
    start = time.time()
    runner = minds_sim.run()

    results = Results(runner.maximum_communication_delay(),
                      runner.energy_balance(),
                      0.,
                      runner.average_energy(),
                      runner.max_buffer_size())

    print("Finished MINDS in {} seconds".format(time.time() - start))
    return results


def run_focus(parameters):
    """

     :param parameters:
     :type parameters: Parameters
     :return:
     """

    env = Environment()
    env.segment_count = parameters.segment_count
    env.mdc_count = parameters.mdc_count
    env.isdva = parameters.isdva * pq.mebi * pq.bit
    env.isdvsd = parameters.isdvsd
    env.comms_range = parameters.radio_range * env.comms_range.units

    focus_sim = FOCUS(env)
    print(
        "Starting FOCUS at {}".format(datetime.datetime.now().isoformat()))
    print("Using {}".format(parameters))
    start = time.time()
    runner = focus_sim.run()

    results = Results(runner.maximum_communication_delay(),
                      runner.energy_balance(),
                      0.,
                      runner.average_energy(),
                      runner.max_buffer_size())

    print("Finished FOCUS in {} seconds".format(time.time() - start))
    return results


def run(parameters):
    tocs_results = []
    flower_results = []
    minds_results = []
    focus_results = []

    with multiprocessing.Pool(processes=MAX_PROCESSES) as pool:

        while len(tocs_results) < RUNS or \
                len(flower_results) < RUNS or \
                        len(minds_results) < RUNS or \
                        len(focus_results) < RUNS:

            # tocs_runners = MAX_PROCESSES // 4
            # flower_runners = MAX_PROCESSES // 4
            # minds_runners = MAX_PROCESSES // 4
            # focus_runners = MAX_PROCESSES // 4

            tocs_workers = []
            flower_workers = []
            minds_workers = []
            focus_workers = []

            if len(tocs_results) < RUNS:
                tocs_workers = [pool.apply_async(run_tocs, (parameters,))
                                for
                                _ in range(RUNS - len(tocs_results))]

            if len(flower_results) < RUNS:
                flower_workers = [
                    pool.apply_async(run_flower, (parameters,))
                    for _ in range(RUNS - len(flower_results))]

            if len(minds_results) < RUNS:
                minds_workers = [
                    pool.apply_async(run_minds, (parameters,))
                    for _ in range(RUNS - len(minds_results))]

            if len(focus_results) < RUNS:
                focus_workers = [
                    pool.apply_async(run_focus, (parameters,))
                    for _ in range(RUNS - len(focus_results))]

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
    print("Random seed is %s", seed)
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
            tocs_csv.flush()

            # noinspection PyProtectedMember,PyProtectedMember
            flower_writer.writerow(
                {**flower_res._asdict(), **parameter._asdict()})
            flower_csv.flush()

            # noinspection PyProtectedMember,PyProtectedMember
            minds_writer.writerow(
                {**minds_res._asdict(), **parameter._asdict()})
            minds_csv.flush()

            # noinspection PyProtectedMember,PyProtectedMember
            focus_writer.writerow(
                {**focus_res._asdict(), **parameter._asdict()})
            focus_csv.flush()


if __name__ == '__main__':
    main()
