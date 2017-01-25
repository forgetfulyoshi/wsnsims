import logging
from multiprocessing import Pool

import quantities as pq
from wsnsims.conductor import sim_inputs
from wsnsims.core import environment
from wsnsims.flower.flower_sim import FLOWER
from wsnsims.minds.minds_sim import MINDS
from wsnsims.tocs.tocs_sim import TOCS

from wsnsims.focus.focus_sim import FOCUS

logger = logging.getLogger(__name__)


def run_worker(kwargs):
    algorithm = kwargs['algorithm']

    env = environment.Environment()
    env.segment_count = kwargs['segment_count']
    env.mdc_count = kwargs['mdc_count']
    env.isdva = kwargs['isdva']
    env.isdvsd = kwargs['isdvsd']
    env.comms_range = kwargs['comms_range']

    if algorithm == 'flower':
        simulator = FLOWER(env)
    elif algorithm == 'tocs':
        simulator = TOCS(env)
    elif algorithm == 'minds':
        simulator = MINDS(env)
    elif algorithm == 'focus':
        simulator = FOCUS(env)
    else:
        raise NotImplementedError("Invalid algorithm provided: %s", algorithm)

    results = {}

    complete = False
    while not complete:
        try:
            runner = simulator.run()

            results = {
                'max_delay': runner.maximum_communication_delay(),
                'average_energy': runner.average_energy(),
                'energy_balance': runner.energy_balance(),
                'max_buffer_size': runner.max_buffer_size(),
            }

            complete = True
        except Exception as e:
            logger.exception("%s crashed", algorithm)
            pass

    full_output = {**results, **kwargs}

    return full_output


def generate_tasks():
    tasks = list()
    algorithms = ['flower', 'tocs', 'minds', 'focus']
    algorithms = ['flower']

    for param in sim_inputs.conductor_params:
        for algorithm in algorithms:
            task = {
                'algorithm': algorithm,
                'segment_count': param[0],
                'mdc_count': param[1],
                'isdva': param[2] * pq.mebi * pq.bit,
                'isdvsd': param[3],
                'comms_range': param[4] * pq.meter,
            }
            tasks.append(task)

    return tasks


def main():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('driver')

    tasks = generate_tasks()
    pool = Pool()
    results = pool.map(run_worker, tasks[:4])
    logger.debug(results)


if __name__ == '__main__':
    main()
