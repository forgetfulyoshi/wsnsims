import collections
import logging
import multiprocessing as mp
import time

import quantities as pq
from wsnsims.conductor import sim_inputs
from wsnsims.core import environment
from wsnsims.flower.flower_sim import FLOWER
from wsnsims.minds.minds_sim import MINDS
from wsnsims.tocs.tocs_sim import TOCS
from wsnsims.focus.focus_sim import FOCUS

logger = logging.getLogger(__name__)


def run_sim(kwargs):
    algorithm = kwargs['algorithm']

    env = environment.Environment()
    env.segment_count = kwargs['segment_count']
    env.mdc_count = kwargs['mdc_count']
    env.isdva = kwargs['isdva']
    env.isdvsd = kwargs['isdvsd']
    env.comms_range = kwargs['comms_range']

    ordered_args = collections.OrderedDict(sorted(kwargs.items()))

    print("Running {} with {}".format(str(algorithm.__name__), ordered_args))
    logging.disable(logging.DEBUG)
    logging.disable(logging.INFO)

    results = {}
    complete = False
    start = time.time()
    while not complete:
        try:
            start = time.time()
            simulator = algorithm(env)
            runner = simulator.run()
            results = {
                'max_delay': runner.maximum_communication_delay(),
                'average_energy': runner.average_energy(),
                'energy_balance': runner.energy_balance(),
                'max_buffer_size': runner.max_buffer_size(),
            }

            complete = True
        except Exception:
            logger.exception("%s crashed", algorithm.__name__)
            pass

    finish = time.time()
    results['algorithm'] = algorithm.__name__
    results['segment_count'] = kwargs['segment_count']
    results['mdc_count'] = kwargs['mdc_count']
    results['isdva'] = kwargs['isdva']
    results['isdvsd'] = kwargs['isdvsd']
    results['comms_range'] = kwargs['comms_range']
    results['group_id'] = kwargs['group_id']

    results_queue = kwargs['queue']
    results_queue.put(results)

    delta = finish - start
    print("Finished {} in {} seconds with {}".format(str(algorithm.__name__),
                                                     delta,
                                                     ordered_args))


def generate_tasks(results_queue):
    tasks = list()
    # algorithms = [FLOWER, TOCS, MINDS, FOCUS]
    algorithms = [FLOWER]
    group_id = 0
    for param in sim_inputs.conductor_params:
        for algorithm in algorithms:
            task = {
                'algorithm': algorithm,
                'segment_count': param[0],
                'mdc_count': param[1],
                'isdva': param[2] * pq.mebi * pq.bit,
                'isdvsd': param[3],
                'comms_range': param[4] * pq.meter,
                'group_id': group_id,
                'queue': results_queue,
            }

            for _ in range(3):
                tasks.append(task)

            group_id += 1

    return tasks


import sqlite3


def create_database():
    conn = sqlite3.connect(r'C:\results\results.db')
    c = conn.cursor()

    # Create the intermediate results table
    c.execute("""
    CREATE TABLE IF NOT EXISTS intermediate
    (group_id INTEGER,
     algorithm TEXT,
     segment_count INTEGER,
     mdc_count INTEGER,
     isdva FLOAT,
     isdvsd FLOAT,
     comms_range FLOAT,
     max_delay FLOAT,
     average_energy FLOAT,
     energy_balance FLOAT,
     max_buffer_size FLOAT)
     """)

    # Create the final results table
    c.execute("""
        CREATE TABLE IF NOT EXISTS final
        (group_id INTEGER,
         algorithm TEXT,
         segment_count INTEGER,
         mdc_count INTEGER,
         isdva FLOAT,
         isdvsd FLOAT,
         comms_range FLOAT,
         max_delay FLOAT,
         average_energy FLOAT,
         energy_balance FLOAT,
         max_buffer_size FLOAT)
         """)

    conn.commit()
    return conn, c


def write_intermediate_result(conn, cursor, result):
    values = [
        result['group_id'],
        result['algorithm'],
        result['segment_count'],
        result['mdc_count'],
        float(result['isdva']),
        result['isdvsd'],
        float(result['comms_range']),
        float(result['max_delay']),
        float(result['average_energy']),
        float(result['energy_balance']),
        float(result['max_buffer_size']),
    ]
    cursor.execute("""
    INSERT INTO intermediate VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, values)
    conn.commit()


def run_db(queue):
    # Establish the database connection
    conn, cursor = create_database()

    while True:
        result = queue.get()
        if result == GeneratorExit:
            break

        write_intermediate_result(conn, cursor, result)

    # Tear down the database
    conn.close()


def main():
    m = mp.Manager()
    q = m.Queue()
    db_worker = mp.Process(target=run_db, args=(q,))
    db_worker.start()

    tasks = generate_tasks(q)
    worker_pool = mp.Pool()
    logger.debug("Starting %d tasks ...", len(tasks))

    start = time.time()
    results = list()
    for task in tasks:
        result = worker_pool.apply_async(run_sim, (task,))
        results.append(result)

    for result in results:
        result.get()

    worker_pool.close()
    worker_pool.join()
    finish = time.time()
    delta = finish - start

    print("Total time: {}".format(delta))

    logger.debug("All workers have returned")

    # Put the sentinel object on the queue to close the database worker
    q.put(GeneratorExit)
    db_worker.join()


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    # logger = logging.getLogger('driver')
    main()
