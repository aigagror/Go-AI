import gym
import torch

import utils
from go_ai import policies, game
from go_ai.models import value, actorcritic

args = utils.hyperparameters()

# Environment
go_env = gym.make('gym_go:go-v0', size=args.boardsize)

# Policies
if args.agent == 'mcts':
    checkpoint_model = value.ValueNet(args.boardsize)
    checkpoint_model.load_state_dict(torch.load(args.checkpath))
    checkpoint_pi = policies.MCTS('Checkpoint', checkpoint_model, 82, 0)
elif args.agent == 'ac':
    checkpoint_model = actorcritic.ActorCriticNet(args.boardsize)
    checkpoint_model.load_state_dict(torch.load(args.checkpath))
    checkpoint_pi = policies.ActorCritic('Checkpoint', checkpoint_model)
print("Loaded model")

# Play
go_env.reset()
game.pit(go_env, policies.HUMAN_PI, checkpoint_pi, False)
