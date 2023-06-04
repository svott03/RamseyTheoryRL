import igraph as ig
import numpy as np
import tensorflow as tf
import networkx as nx
import random
import timeit
import pickle
import math
import pickle
import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)
from utils.gfeatures import *
from utils.guseful import *
import utils.heuristic.train_heuristic as train
import utils.heuristic.handle_neptune as hn
import utils.heuristic.create_heuristic as ch
from models.heuristic import load_model_by_id
from ramsey_checker_single_thread import RamseyCheckerSingleThread
from ramsey_checker_multi_thread import RamseyCheckerMultiThread
import threading
import cProfile, pstats

PROJECT = "rinzzier/RamseyRL"
MODEL_NAME = "RAM-HEUR"
LOAD_MODEL = False
# Choose from RANDOM, DNN, SCALED_DNN
HEURISTIC_TYPE = "SCALED_DNN"
PARAMS = {'training_epochs': 1, 'epochs': 1, 'batch_size': 32, 'optimizer': 'adam', 'loss': tf.keras.losses.BinaryCrossentropy(
    from_logits=False, label_smoothing=0.2), 'last_activation': 'sigmoid', 'pretrain': True, 'heuristic_type': HEURISTIC_TYPE}
N = 8
S = 3
T = 4
lock = threading.Lock()


def main():
    ramseyChecker = RamseyCheckerMultiThread()
    if LOAD_MODEL:
        MODEL_ID = "RAM-HEUR-85"
        RUN_ID = "RAM-94"
        print(f"Loading {MODEL_ID} and {RUN_ID}.")
        run, model_version, model = load_model_by_id(project=PROJECT,
                                                     model_name=MODEL_NAME,
                                                     model_id=MODEL_ID,
                                                     run_id=RUN_ID)
    else:
        run, model_version = hn.init_neptune(params=PARAMS,
                                             project=PROJECT,
                                             model_name=MODEL_NAME)
        MODEL_ID = model_version["sys/id"].fetch()
        RUN_ID = run["sys/id"].fetch()
        model = ch.create_model(PARAMS)
        if PARAMS['pretrain']:
            TRAIN_PATH = 'data/csv/scaled/'
            # CSV_LIST = ['all_leq9','ramsey_3_4','ramsey_3_5','ramsey_3_6','ramsey_3_7','ramsey_3_9','ramsey_4_4']
            CSV_LIST = ['all_leq6', 'ramsey_3_4']
            TRAIN_CSV_LIST = [f'{TRAIN_PATH}{CSV}.csv' for CSV in CSV_LIST]
            train_X, train_y = train.split_X_y_list(TRAIN_CSV_LIST)
            print(f"Pretraining on {train_X.shape[0]} samples.")
            neptune_cbk = hn.get_neptune_cbk(run=run)
            train.train(model=model, train_X=train_X, train_y=train_y,
                        params=PARAMS, neptune_cbk=neptune_cbk)
        train.save_trained_model(model_version=model_version, model=model)

    if HEURISTIC_TYPE == "RANDOM":
        def heuristic(vectorizations):
            return random.random()
    elif HEURISTIC_TYPE == "DNN":
        def heuristic(vectorizations):
            with lock:
                X = np.array([list(vec.values())[:-1] for vec in vectorizations])
                predictions = model.predict(X, verbose=0)
                return [prediction[0] for prediction in predictions]
    elif HEURISTIC_TYPE == "SCALED_DNN":
        scaler = float(math.comb(N, 4))
        def heuristic(vectorizations):
            with lock:
                X = np.array([list(vec.values())[:-1]
                            for vec in vectorizations]).astype(float)
                X[:11] /= scaler
                predictions = model.predict(X, verbose=0)
                return [prediction[0] for prediction in predictions]

    if HEURISTIC_TYPE == "RANDOM":
        def update_model(*args, **kwargs):
            pass
        PAST, COUNTERS, G = dict(), [], ig.Graph.GRG(N, N/2/(N-1))
    else:
        neptune_cbk = hn.get_neptune_cbk(run)

        def save_past_and_g(past, g):
            np.save
            with open('past.pkl', 'wb') as file:
                pickle.dump(past, file)
            run['running/PAST'].upload('past.pkl')
            if g is not None:
                nx_graph = nx.Graph(g.get_edgelist())
                nx.write_graph6(nx_graph, 'G.g6', header=False)
                run['running/G'].upload('G.g6')
        def load_data():
            run['running/PAST'].download('past.pkl')
            with open('past.pkl', 'rb') as file:
                past = pickle.load(file)

            run['running/G'].download('G.g6')
            g = ig.Graph.from_networkx(nx.read_graph6('G.g6'))

            if run.exists('running/counters'):
                run['running/counters'].download('counters.g6')
                counters = nx.read_graph6('counters.g6')
                counters = [counters] if type(counters) != list else counters
            else:
                counters = []

            oldIterations = run['running/iterations'].fetch_last()
            timeOffset = run['running/time'].fetch_last()
            return past, counters, g, oldIterations, timeOffset
        if LOAD_MODEL:
            PAST, COUNTERS, G, oldIterations, timeOffset = load_data()
        else:
            PAST = dict()
            COUNTERS = []
            G = ig.Graph.GRG(N, N/2/(N-1))
            oldIterations = 0
            timeOffset = 0

        def update_model(training_data, past, g):
            X = np.array([list(vec.values())[:-1] for vec in training_data])
            y = np.array([list(vec.values())[-1] for vec in training_data])
            model.fit(X, y, epochs=PARAMS['epochs'], batch_size=PARAMS['batch_size'], callbacks=[
                      neptune_cbk], verbose=1)
            train.save_trained_model(model_version, model)
            save_past_and_g(past, g)

    run['running/N'] = N
    run['running/S'] = S
    run['running/T'] = T
    ITER_BATCH = 100
    # BATCHES = 5
    BATCHES = None
    counter_path = f'data/found_counters/scaled_dnn'
    unique_path = f'{counter_path}/r{S}_{T}_{N}_isograph.g6'
    if os.path.exists(unique_path):
        os.remove(unique_path)
    PARALLEL = False
    startTime = timeit.default_timer()

    def update_run_data(unique_path, startTime):
        def update_running(iterations, counter_count):
            if os.path.exists(unique_path):
                run['running/counters'].upload(unique_path)
            run['running/counter_count'].append(counter_count)
            run['running/time'].append(timeit.default_timer() -
                                       startTime + timeOffset)
            run['running/iterations'].append(iterations)
        return update_running
    update_running = update_run_data(unique_path, startTime)
    with cProfile.Profile() as profiler:
        ramseyChecker.bfs(g=G, unique_path=unique_path, past=PAST, counters=COUNTERS, s=S, t=T, n=N, iter_batch=ITER_BATCH,
            update_model=update_model, heuristic=heuristic, update_running=update_running, oldIterations=oldIterations, batches=BATCHES)
    stats = pstats.Stats(profiler)
    stats.sort_stats(pstats.SortKey.TIME).print_stats()
    print(
        f"Single Threaded Time Elapsed: {timeit.default_timer() - startTime}")
    # startTime = timeit.default_timer()
    # G2 = ig.Graph(7)
    # bfs(G2, g6path_to_write_to, gEdgePath_to_write_to, PAST_path, s, t, True)
    # print(f"Multi Threaded Time Elapsed: {timeit.default_timer() - startTime}")
    run.stop()
    model_version.stop()


if __name__ == '__main__':
    main()
