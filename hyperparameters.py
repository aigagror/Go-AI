import os

import torch

BOARD_SIZE = 5

BATCH_SIZE = 32
REPLAY_MEMSIZE = 1000 * (2 * BOARD_SIZE ** 2)
TRAINSTEP_MEMSIZE = 256 * (2 * BOARD_SIZE ** 2)

ITERATIONS = 256
EPISODES_PER_ITER = 32
NUM_EVALGAMES = 128
ITERS_PER_EVAL = 4

INIT_TEMP = 0.1
TEMP_DECAY = 3 / 4
MIN_TEMP = 1 / 32

MCT_SEARCHES = 0  # If set to 0, MCTPolicies become simply QVals

WORKERS = 4

LOAD_SAVEDMODELS = False
EPISODES_DIR = 'episodes/'
CHECKPOINT_PATH = f'checkpoints/checkpoint_{BOARD_SIZE}x{BOARD_SIZE}.pt'
TMP_PATH = 'checkpoints/tmp_{}x{}.pt'.format(BOARD_SIZE, BOARD_SIZE)
DEMO_TRAJPATH = EPISODES_DIR + 'a_traj.png'


def reset_disk_params(model):
    """
    Updates the checkpooint parameters based on the given arguments,
    and syncs the temporary parameters with checkpoint
    :param model:
    :return:
    """
    if LOAD_SAVEDMODELS:
        assert os.path.exists(CHECKPOINT_PATH)
    else:
        torch.save(model.state_dict(), CHECKPOINT_PATH)
    return LOAD_SAVEDMODELS
