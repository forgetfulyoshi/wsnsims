import csv
import datetime
import logging
import multiprocessing
import os
import statistics
import time
from collections import namedtuple

from original_flower import params
from original_flower import sim_inputs
from original_flower.flower_sim import FlowerSim
from original_flower.results import Results
from original_flower.tocs_sim import ToCS

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

RUNS = 30

Parameters = namedtuple('Parameters', ['segment_count', 'mdc_count', 'isdva', 'isdvsd', 'radio_range'])


def average_results(results):

    mean_max_delay = statistics.mean([x.max_delay for x in results])
    mean_balance = statistics.mean([x.balance for x in results])
    mean_lifetime = statistics.mean([x.lifetime for x in results])
    mean_energy = statistics.mean([x.ave_energy for x in results])
    mean_buffer = statistics.mean([x.max_buffer for x in results])

    result = Results(mean_max_delay, mean_balance, mean_lifetime, mean_energy, mean_buffer)
    return result

def run_tocs(parameters):
    tocs_sim = ToCS()
    print("Starting ToCS at {}".format(datetime.datetime.now().isoformat()))
    print("Using {}".format(parameters))
    start = time.time()
    results = tocs_sim.run()
    print("Finished ToCS in {} seconds".format(time.time() - start))
    return results

def run_flower(parameters):
    flower_sim = FlowerSim()
    print("Starting FLOWER at {}".format(datetime.datetime.now().isoformat()))
    print("Using {}".format(parameters))
    start = time.time()
    results = flower_sim.run()
    print("Finished FLOWER in {} seconds".format(time.time() - start))
    return results

def run(parameters):
    tocs_results = []
    flower_results = []

    params.SEGMENT_COUNT = parameters.segment_count
    params.MDC_COUNT = parameters.mdc_count
    params.ISDVA = parameters.isdva
    params.ISDVSD = parameters.isdvsd
    params.COMMUNICATION_RANGE = parameters.radio_range

    MAX_PROCESSES = 64
    with multiprocessing.Pool(processes=MAX_PROCESSES) as pool:

        while len(tocs_results) <= RUNS or len(flower_results) <= RUNS:

            # tocs_runners = RUNS - len(tocs_results)
            # flower_runners = RUNS - len(flower_results)

            tocs_runners = MAX_PROCESSES // 2
            flower_runners = MAX_PROCESSES // 2

            tocs_workers = [pool.apply_async(run_tocs, (parameters,)) for _ in range(tocs_runners)]
            flower_workers = [pool.apply_async(run_flower, (parameters,)) for _ in range(flower_runners)]

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

    mean_tocs_results = average_results(tocs_results[:RUNS])
    mean_flower_results = average_results(flower_results[:RUNS])

    return mean_tocs_results, mean_flower_results


def main():
    # segment_counts = [12, 15, 18, 21, 24, 30]
    # mdc_counts = [3, 5, 7, 9]
    # isdvas = [45]
    # radio_ranges = [50, 70, 100, 150, 200]
    # isdvsds = [3.0]
    # parameters = list(itertools.product(segment_counts, mdc_counts, isdvas, isdvsds, radio_ranges))
    # parameters = [Parameters._make(p) for p in parameters]

    # with open('C:\\results\\inputs.txt', 'w') as inputs:
    #     inputs.write("conductor_params = [\n")
    #     for p in parameters:
    #         inputs.write('    ' + str(p) + ',\n')
    #
    #     inputs.write(']\n')

    parameters = [Parameters._make(p) for p in sim_inputs.conductor_params]

    fieldnames = ['max_delay', 'balance', 'lifetime', 'ave_energy', 'max_buffer'] + list(parameters[0]._fields)

    if not (os.path.isfile('C:\\results\\tocs.csv') and os.path.isfile('C:\\results\\original_flower.csv')):
        with open('C:\\results\\tocs.csv', 'w', newline='') as tocs_csv, open('C:\\results\\original_flower.csv', 'w', newline='') as flower_csv:

            tocs_writer = csv.DictWriter(tocs_csv, fieldnames=fieldnames)
            flower_writer = csv.DictWriter(flower_csv, fieldnames=fieldnames)

            tocs_writer.writeheader()
            flower_writer.writeheader()

    for p in parameters:
        with open('C:\\results\\tocs.csv', 'a', newline='') as tocs_csv, open('C:\\results\\original_flower.csv', 'a', newline='') as flower_csv:
            tocs_writer = csv.DictWriter(tocs_csv, fieldnames=fieldnames)
            flower_writer = csv.DictWriter(flower_csv, fieldnames=fieldnames)

            tocs_results, flower_results = run(p)
            tocs_writer.writerow({**tocs_results._asdict(), **p._asdict()})
            flower_writer.writerow({**flower_results._asdict(), **p._asdict()})


if __name__ == '__main__':
    main()
