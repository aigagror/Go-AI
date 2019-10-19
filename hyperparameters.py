BOARD_SIZE = 7

BATCH_SIZE = 32
REPLAY_MEMSIZE = 1024 * (2 * BOARD_SIZE ** 2)
TRAINSAMPLE_MEMSIZE = 1000 * BATCH_SIZE

ITERATIONS = 256
EPISODES_PER_ITER = 256
NUM_EVALGAMES = 256
ITERS_PER_EVAL = 1

INIT_TEMP = 1 / 32
TEMP_DECAY = 3 / 4
MIN_TEMP = 1 / 32

MCT_SEARCHES = 0  # If set to 0, MCTPolicies become simply QVals

WORKERS = 4

CONTINUE_CHECKPOINT = False
EPISODES_DIR = 'episodes/'
CHECKPOINT_PATH = f'checkpoints/checkpoint_{BOARD_SIZE}x{BOARD_SIZE}.pt'
TMP_PATH = 'checkpoints/tmp_{}x{}.pt'.format(BOARD_SIZE, BOARD_SIZE)
DEMO_TRAJPATH = EPISODES_DIR + 'a_traj.pdf'
