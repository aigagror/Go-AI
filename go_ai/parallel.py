import logging
import math
import os
import time

from mpi4py import MPI

from go_ai import game


def configure_logging(args, comm: MPI.Intracomm):
    if comm.Get_rank() == 0:
        bare_frmtr = logging.Formatter('%(message)s')

        filer = logging.FileHandler(os.path.join(args.savedir, 'stats.txt'), 'w')
        filer.setLevel(logging.INFO)
        filer.setFormatter(bare_frmtr)

        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(bare_frmtr)

        rootlogger = logging.getLogger()
        rootlogger.setLevel(logging.DEBUG)
        rootlogger.addHandler(console)
        rootlogger.addHandler(filer)

    comm.Barrier()


def parallel_play(comm: MPI.Intracomm, go_env, pi1, pi2, gettraj, req_episodes):
    """
    Plays games in parallel
    :param comm:
    :param go_env:
    :param pi1:
    :param pi2:
    :param gettraj:
    :param req_episodes:
    :return:
    """
    world_size = comm.Get_size()

    worker_episodes = int(math.ceil(req_episodes / world_size))
    episodes = worker_episodes * world_size
    single_worker = comm.Get_size() <= 1

    timestart = time.time()
    winrate, steps, traj = game.play_games(go_env, pi1, pi2, gettraj, worker_episodes, progress=single_worker)
    timeend = time.time()

    duration = timeend - timestart
    avg_time = comm.allreduce(duration / worker_episodes, op=MPI.SUM) / world_size
    winrate = comm.allreduce(winrate, op=MPI.SUM) / world_size
    avg_steps = comm.allreduce(sum(steps), op=MPI.SUM) / episodes

    parallel_debug(comm, f'{pi1} V {pi2} | {episodes} GAMES, {avg_time:.1f} SEC/GAME, {avg_steps:.0f} STEPS/GAME, '
                         f'{100 * winrate:.1f}% WIN')
    return winrate, traj


def parallel_info(comm: MPI.Intracomm, s):
    """
    Only the first worker prints stuff
    :param rank:
    :param s:
    :return:
    """
    rank = comm.Get_rank()
    if rank == 0:
        logging.info(s)


def parallel_debug(comm: MPI.Intracomm, s):
    """
    Only the first worker prints stuff
    :param rank:
    :param s:
    :return:
    """
    rank = comm.Get_rank()
    if rank == 0:
        s = f"{time.strftime('%H:%M:%S', time.localtime())}\t{s}"
        logging.debug(s)
