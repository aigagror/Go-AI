import gym
import numpy as np
import torch

from go_ai import montecarlo
from go_ai.models import pytorch_val_to_numpy, pytorch_ac_to_numpy
from go_ai.montecarlo import temperate_pi, greedy_pi, tree

from scipy import special

GoGame = gym.make('gym_go:go-v0', size=0).gogame


def greedy_val_func(states):
    if len(states) <= 0:
        return np.array([])
    board_area = GoGame.get_action_size(states[0]) - 1

    vals = []
    for state in states:
        black_area, white_area = GoGame.get_areas(state)
        if GoGame.get_game_ended(state):
            if black_area > white_area:
                val = 1
            elif black_area < white_area:
                val = -1
            else:
                val = 0
        else:
            val = (black_area - white_area) / (board_area)
        vals.append(val)
    vals = np.array(vals, dtype=np.float)
    return vals[:, np.newaxis]


def smart_greedy_val_func(states):
    if len(states) <= 0:
        return np.array([])
    board_area = GoGame.get_action_size(states[0]) - 1

    vals = []
    for state in states:
        black_area, white_area = GoGame.get_areas(state)
        blacklibs, whitelibs = GoGame.get_num_liberties(state)
        if GoGame.get_game_ended(state):
            if black_area > white_area:
                val = 1
            elif black_area < white_area:
                val = -1
            else:
                val = 0
        else:
            area_val = (black_area - white_area) / (board_area)
            libs_val = (blacklibs - whitelibs) / (board_area)
            val = (6 * area_val + libs_val) / 7
        vals.append(val)
    vals = np.array(vals, dtype=np.float)
    return vals[:, np.newaxis]


class Policy:
    """
    Interface for all types of policies
    """

    def __init__(self, name, temp=None, temp_steps=None):
        self.name = name
        self.temp = temp
        self.temp_steps = temp_steps
        self.pytorch_model = None

    def __call__(self, go_env, **kwargs):
        """
        :param go_env: Go environment
        :param step: the number of steps taken in the game so far
        :return: Action probabilities
        """
        pass

    def decay_temp(self, decay):
        self.temp *= decay
        if self.temp < 0:
            self.temp = 0

    def set_temp(self, temp):
        self.temp = temp

    def __str__(self):
        return "{} {}".format(self.__class__.__name__, self.name)


class Random(Policy):
    def __init__(self):
        super(Random, self).__init__('Random')

    def __call__(self, go_env, **kwargs):
        """
        :param go_env:
        :param step:
        :return: Action probabilities
        """

        valid_moves = go_env.get_valid_moves()
        return valid_moves / np.sum(valid_moves)


class Human(Policy):
    def __init__(self):
        super(Human, self).__init__('Human')

    def __call__(self, go_env, **kwargs):
        """
        :param go_env:
        :param step:
        :return: Action probabilities
        """
        valid_moves = go_env.get_valid_moves()

        # Human interface
        while True:
            player_action = go_env.render('human')
            state = go_env.get_state()
            player_action = GoGame.action_2d_to_1d(player_action, state)
            if valid_moves[player_action] > 0:
                break

        action_probs = np.zeros(GoGame.get_action_size(state))
        action_probs[player_action] = 1

        return action_probs


class MCTS(Policy):
    def __init__(self, name, val_func, num_searches, temp=0, temp_steps=0):
        super(MCTS, self).__init__(name, temp, temp_steps)
        if isinstance(val_func, torch.nn.Module):
            self.pytorch_model = val_func
            val_func = pytorch_val_to_numpy(val_func)

        self.val_func = val_func
        self.num_searches = num_searches

    def __call__(self, go_env, **kwargs):
        """
        :param state: Unused variable since we already have the state stored in the tree
        :param step: Parameter used for getting the temperature
        :return:
        """

        prior_qs, post_qs = self.mcts_qvals(go_env)

        valid_indicators = go_env.get_valid_moves()
        if 'get_qs' in kwargs:
            get_qs = kwargs['get_qs']
        else:
            get_qs = False

        step = kwargs['step']
        assert step is not None
        if step < self.temp_steps:
            pi = temperate_pi(post_qs, self.temp, valid_indicators)
        else:
            pi = temperate_pi(post_qs, 0.01, valid_indicators)

        if get_qs:
            return pi, prior_qs, post_qs
        else:
            return pi

    def mcts_qvals(self, go_env):
        canonical_children, child_groupmaps = go_env.get_children(canonical=True)
        child_vals = self.val_func(np.array(canonical_children))
        canonical_state = go_env.get_canonical_state()
        valid_indicators = go_env.get_valid_moves()

        prior_qs = montecarlo.vals_to_qs(child_vals, canonical_state)
        post_qs = np.copy(prior_qs)

        # Search on grandchildren layer
        if self.num_searches > 0:
            valid_moves = np.argwhere(valid_indicators).flatten()
            assert len(valid_moves) == len(child_vals)
            ordered_child_idcs = np.argsort(child_vals.flatten())
            best_child_idcs = ordered_child_idcs[:self.num_searches]
            remaining_child_idcs = ordered_child_idcs[self.num_searches:]
            for child_idx in best_child_idcs:
                action_to_child = valid_moves[child_idx]
                child = canonical_children[child_idx]
                if GoGame.get_game_ended(child):
                    continue
                child_groupmap = child_groupmaps[child_idx]
                grandchildren, _ = GoGame.get_children(child, child_groupmap, canonical=True)
                grand_vals = self.val_func(np.array(grandchildren))
                # Assume opponent would take action that minimizes our value
                new_childval = np.min(grand_vals)
                curr_qval = prior_qs[action_to_child]
                new_qval = np.mean([curr_qval, new_childval])
                post_qs[action_to_child] = new_qval

            changes = np.sum(post_qs != prior_qs)
            if changes > 0:
                bias_correction = np.min(post_qs - prior_qs)

                for child_idx in remaining_child_idcs:
                    action_to_child = valid_moves[child_idx]
                    child = canonical_children[child_idx]
                    if GoGame.get_game_ended(child):
                        continue
                    post_qs[action_to_child] += bias_correction

        return prior_qs, post_qs

    def __str__(self):
        return f"{self.__class__.__name__}[{self.num_searches}S {self.temp:.2f}T]-{self.name}"


class MCTSActorCritic(Policy):
    def __init__(self, name, model, mcts, temp, tempsteps):
        """
        :param branches: The number of actions explored by actor at each node.
        :param depth: The number of steps to explore with actor. Includes opponent,
        i.e. even depth means the last step explores the opponent's
        """
        super(MCTSActorCritic, self).__init__(name, temp=temp, temp_steps=tempsteps)
        self.pytorch_model = model
        self.pi_func, self.val_func = pytorch_ac_to_numpy(model)
        self.num_searches=mcts

    def __call__(self, go_env, **kwargs):
        """
        :param state: Unused variable since we already have the state stored in the tree
        :param step: Parameter used for getting the temperature
        :return:
        """

        visits = tree.mct_search(go_env, self.num_searches, self.val_func, self.pi_func)

        step = kwargs['step']
        assert step is not None
        if step < self.temp_steps:
            max_visit = np.max(visits)
            pi = visits == max_visit
        else:
            pi = visits * (1 / self.temp)

        pi = pi / np.sum(pi)

        return pi

    def __str__(self):
        return f"{self.__class__.__name__}[{self.num_searches}S {self.temp:.2f}T]-{self.name}"


class ActorCritic(Policy):
    def __init__(self, name, network):
        super(ActorCritic, self).__init__(name, temp=0)
        self.pi_func, self.val_func = pytorch_ac_to_numpy(network)
        self.pytorch_model = network

    def __call__(self, go_env, **kwargs):
        """
        :param go_env:
        :param step: Parameter used for getting the temperature
        :return: Action probabilities
        """
        state = go_env.get_canonical_state()
        pi = self.pi_func(state[np.newaxis])[0]
        pi = special.softmax(pi)
        return pi


RAND_PI = Random()
GREEDY_PI = MCTS('Greedy', greedy_val_func, num_searches=0)
SMART_GREEDY_PI = MCTS('Smart Greedy', smart_greedy_val_func, num_searches=0)
HUMAN_PI = Human()
