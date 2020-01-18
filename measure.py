import gym
import os
from mpi4py import MPI

from go_ai import measurements, utils, policies

args = utils.hyperparameters(MPI.COMM_WORLD)

# Environment
go_env = gym.make('gym_go:go-v0', size=args.boardsize)

# Policies
modeldir = 'bin/baselines/'
model, policy = utils.create_model(args, 'Model', modeldir=modeldir)
print(f"Loaded model {policy} from {modeldir}")

# Directories and files
basedir = os.path.join(modeldir, f'{args.model}{args.boardsize}_plots/')
if not os.path.exists(basedir):
    os.mkdir(basedir)

stats_path = os.path.join(modeldir, f'{args.model}{args.boardsize}_stats.txt')

# Plot stats
if os.path.exists(stats_path):
    measurements.plot_stats(stats_path, basedir)
    print("Plotted ELOs, win rates, losses, and accuracies")

# Plot tree if applicable
if isinstance(policy, policies.ActorCritic) or isinstance(policy, policies.Value):
    go_env.reset()
    measurements.plot_tree(go_env, policy, basedir)
    print(f'Plotted tree')

# Sample trajectory and plot prior qvals
traj_path = os.path.join(basedir, f'heat{policy.temp:.2f}.pdf')
measurements.plot_traj_fig(go_env, policy, traj_path)
print(f"Plotted sample trajectory with temp {args.temp}")