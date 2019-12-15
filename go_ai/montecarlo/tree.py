import gym
import numpy as np
from scipy import special

from go_ai import montecarlo, data
from go_ai.montecarlo.node import Node

GoGame = gym.make('gym_go:go-v0', size=0).gogame


def mct_search(go_env, num_searches, val_func, pi_func):
    '''
    Description:
        Select a child node that maximizes Q + U,
    Args:
        num_searches (int): maximum number of searches performed
        temp (number): temperature constant
    Returns:
        pi (1d np array): the search probabilities
        num_search (int): number of search performed
    '''
    root_groupmap = go_env.group_map
    rootstate = go_env.get_canonical_state()

    rootnode = Node(rootstate, root_groupmap)

    for i in range(num_searches):
        curr_node = rootnode
        while curr_node.visits > 0 and not curr_node.terminal:
            ucbs = curr_node.get_ucbs()
            move = np.argmax(ucbs)
            curr_node = curr_node.traverse(move)

        if curr_node.terminal:
            curr_node.backprop(None)

        leaf_state = curr_node.state
        logit = val_func(leaf_state[np.newaxis])[0]
        val = np.tanh(logit)
        invert_val = montecarlo.invert_val(val)

        prior_qs = pi_func(leaf_state[np.newaxis])[0]
        valid_moves = GoGame.get_valid_moves(leaf_state)
        invalid_values = data.batch_invalid_values(leaf_state[np.newaxis])[0]
        prior_pi = special.softmax(prior_qs * valid_moves + invalid_values)

        curr_node.set_prior_pi(prior_pi)
        curr_node.backprop(invert_val)

    return rootnode.get_move_visits()
