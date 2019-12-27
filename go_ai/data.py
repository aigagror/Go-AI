import os
import pickle
import random

import gym
import numpy as np
from mpi4py import MPI

go_env = gym.make('gym_go:go-v0', size=0)
GoVars = go_env.govars
GoGame = go_env.gogame


def batch_invalid_moves(states):
    """
    Returns 1's where moves are invalid and 0's where moves are valid
    """
    assert len(states.shape) == 4
    batchsize = states.shape[0]
    board_size = states.shape[2]
    invalid_moves = states[:, GoVars.INVD_CHNL].reshape((batchsize, -1))
    invalid_moves = np.insert(invalid_moves, board_size ** 2, 0, axis=1)
    return invalid_moves


def batch_valid_moves(states):
    return 1 - batch_invalid_moves(states)


def batch_invalid_values(states):
    """
    Returns the action values of the states where invalid moves have -infinity value (minimum value of float32)
    and valid moves have 0 value
    """
    invalid_moves = batch_invalid_moves(states)
    invalid_values = np.finfo(np.float32).min * invalid_moves
    return invalid_values


def batch_random_symmetries(states):
    assert len(states.shape) == 4
    processed_states = []
    for state in states:
        processed_states.append(GoGame.random_symmetry(state))
    return np.array(processed_states)

def replays_to_trans_trajs(replay_data):
    trans_trajs = []
    for traj in replay_data:
        trans_trajs.extend(traj.transpose())
    return trans_trajs

def trans_trajs_to_numpy(trans_trajs):
    transposed = list(zip(*trans_trajs))

    states = np.array(list(transposed[0]), dtype=np.float32)
    actions = np.array(list(transposed[1]), dtype=np.int)
    rewards = np.array(list(transposed[2]), dtype=np.float32).reshape((-1,))
    next_states = np.array(list(transposed[3]), dtype=np.float32)
    terminals = np.array(list(transposed[4]), dtype=np.uint8)
    wins = np.array(list(transposed[5]), dtype=np.int)
    pis = np.array(list(transposed[6]), dtype=np.float32)

    return states, actions, rewards, next_states, terminals, wins, pis


def load_replaydata(episodesdir, worker_rank=None):
    """
    Loads replay data from a directory.
    :param episodesdir:
    :param worker_rank: If specified, loads only that specific worker's data. Otherwise it loads all data from all workers
    :return:
    """
    all_data = []
    files = os.listdir(episodesdir)
    for file in files:
        if '.pickle' in file:
            if worker_rank is not None and str(worker_rank) not in file:
                continue
            with open(episodesdir + file, 'rb') as f:
                worker_data = pickle.load(f)
                all_data.extend(worker_data)
    return all_data


def sample_replaydata(comm: MPI.Intracomm, episodesdir, request_size, batchsize):
    """
    :param episodesdir:
    :param request_size:
    :param batchsize:
    :return: Batches of sample data, len of total data that was sampled
    """
    # Workers sample data one at a time to avoid memory issues
    rank = comm.Get_rank()
    world_size = comm.Get_size()
    sample_data = None
    replay_len = None
    for worker in range(world_size):
        if rank == worker:
            all_data = load_replaydata(episodesdir)
            replay_len = len(all_data)
            sample_data = random.sample(all_data, min(request_size, replay_len))
            del all_data
        comm.Barrier()

    concat_trajs = replays_to_trans_trajs(sample_data)
    random.shuffle(concat_trajs)

    sample_data = trans_trajs_to_numpy(concat_trajs)

    sample_size = len(sample_data[0])
    for component in sample_data:
        assert len(component) == sample_size

    splits = max(sample_size // batchsize, 1)
    batched_sampledata = [np.array_split(component, splits) for component in sample_data]
    batched_sampledata = list(zip(*batched_sampledata))

    return batched_sampledata, replay_len


def save_replaydata(comm: MPI.Intracomm, replay_data, episodesdir):
    rank = comm.Get_rank()
    outpath = os.path.join(episodesdir, "worker_{}.pickle".format(rank))
    with open(outpath, 'wb') as f:
        success = False
        while not success:
            try:
                pickle.dump(replay_data, f)
                success = True
            except:
                pass


def clear_episodesdir(episodesdir):
    episode_files = os.listdir(episodesdir)
    for item in episode_files:
        if item.endswith(".pickle"):
            os.remove(os.path.join(episodesdir, item))
