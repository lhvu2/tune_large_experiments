import ray
from ray import tune
from ray.tune import Stopper
from ray.tune.suggest.basic_variant import BasicVariantGenerator

import argparse
import random
import threading
import time


class CustomStopper(Stopper):
    def __init__(self):
        pass

    def __call__(self, trial_id, result):
        # termiate the trial only when 'terminate' exists in the result dictionary
        if 'terminate' in result:
            return True

        return False

    def stop_all(self):
        return False


def worker(config):
    # perform the work and keep the outcome of the experiment in variable "outcomes"
    # call tune.report to write the the log file, look for "result.json" in ray log directory,
    # you will find the key 'experiment_output' in the dictionary

    outcomes = None
    try:
        # for example, we can calcuate the value of outcomes as follows
        outcomes = random.random() * config['input_arg1'] + config['input_arg2']
        print(f"outcomes={outcomes}")
        # sleep for a random period (in seconds) to test that some threads are terminated due to timeout
        s = random.randint(0, 20)
        print(f"Going to sleep for {s} seconds")
        time.sleep(s)
    except Exception as e:
        print(f"ERROR in worker thread, exception: {e}")

    tune.report(experiment_output=outcomes)


def trial_evaluator(config):
    """
    This method is called for each individual trial
    :param config: dict
    This dictionary includes input_arg1, input_arg2, timeout
    :return:
    None

    """
    th = threading.Thread(target=worker, args=(config,))  # create a new thread for the worker
    th.start()  # start the worker thread
    th.join(config['timeout'])  # wait until timeout
    if th.is_alive():  # if the worker thread is alive, terminate the trial
        tune.report(terminate=1)  # the __call__ method of the CustomStopper will handle the 'terminate' key


def create_points_to_evaluate():
    """
    Saple function that create a short list of points for the Scheduler.
    Each point is a dictionary of two keys: input_arg1 and input_arg2, which match with the config in tune.run()

    :return:
    list of points

    """
    points_to_evaluate = list()
    for i in range(2):
        for j in range(2):
            points_to_evaluate.append({'input_arg1': i, 'input_arg2': j})

    return points_to_evaluate


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", type=int, help="Timeout for each experiment (in seconds)", default=10)
    parser.add_argument("-r", type=int, help="Random seed to reproduce the run", default=42)
    parser.add_argument("-n", type=str, help="Experiment folder name", default="sample_experiment")
    parser.add_argument("-l", type=str, help="Ray log path", default="/tmp")
    args = parser.parse_args()

    random.seed(args.r)
    points_to_evaluate = create_points_to_evaluate()

    analysis = tune.run(
        trial_evaluator,
        search_alg=BasicVariantGenerator(points_to_evaluate=points_to_evaluate),
        stop=CustomStopper(),
        name=args.n,  # name of the experiment, it will be a folder created under log_dir below
        config={
            "input_arg1": None, # this is supplied by points_to_evaluate
            "input_arg2": None, # this is supplied by points_to_evaluate
            "timeout": args.t
        },
        local_dir=args.l
    )

    print("Done")
