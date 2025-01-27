import copy
import multiprocessing
import pickle
import time
from typing import Dict

from algorithms.first_choice_hill_climbing import *
from game.catan_state import CatanState
from players.expectimax_weighted_probabilities_with_filter_player import ExpectimaxWeightedProbabilitiesWithFilterPlayer
from players.random_player import RandomPlayer
from players.winner import Winner
from train_and_test.logger import logger

learned_weights_file_name = 'taught_weights'


class GameRunTask:
    pass


class WeightsSpace(AbstractHillClimbableSpace):
    def __init__(self, pool):
        self._pool = pool
        self._time_seconds = 3
        self.iterations_count = 0
        self._max_iterations = 12
        self._games_per_iteration = 5
        self.delta_unit = 5
        self._epsilon_is_weighting_better = 50

    def evaluate_state(self, weights) -> AbstractHillClimbingStateEvaluation:
        logger.info('| evaluating weights: {}'.format(weights))
        args = GameRunTask()
        args.time_seconds_ = self._time_seconds
        args.weights_ = weights
        args.evaluation_ = 0
        all_args = []

        for i in range(self._games_per_iteration):
            xx = copy.deepcopy(args)
            xx.i_ = i
            all_args.append(xx)

        results = 0
        for i in range(self._games_per_iteration):
            arg = copy.deepcopy(all_args[i])
            result = WeightsSpace.run_game(arg)
            results += result

        self.iterations_count += 1

        return results

    @staticmethod
    def run_game(args):
        logger.info('| process {} spawned'.format(args.i_))
        seed = None
        p0 = Winner(id=0, seed=seed, timeout_seconds=args.time_seconds_, weights=args.weights_)
        p1 = ExpectimaxWeightedProbabilitiesWithFilterPlayer(id=1, seed=seed, timeout_seconds=args.time_seconds_)
        p2 = RandomPlayer(id=2, seed=seed)
        p3 = RandomPlayer(id=3, seed=seed)
        # p3 = ExpectimaxWeightedProbabilitiesWithFilterPlayer(id=3, seed=seed, timeout_seconds=args.time_seconds_)
        state = CatanState([p0, p1, p2, p3], seed)
        count_moves = 0
        while not state.is_final():
            state.make_move(state.get_current_player().choose_move(state))
            state.make_random_move()
            count_moves += 1
        scores = state.get_scores_by_player()
        logger.info('| done iteration {}. scores: {}'
                    .format(args.i_, {'p0  (new weights)': scores[p0], 'p1': scores[p1], 'p2': scores[p2], 'p3': scores[p3]}))

        # TODO: change this block
        count_moves_factor = 1 * count_moves
        p0_factor = 10000 if (scores[p0] >= 10) else 0
        p_others_factor = (sum(scores.values()) - scores[p0]) * 0.2
        res = p0_factor - (p_others_factor * count_moves_factor)

        logger.info('| process {} done. res: {}'.format(args.i_, res))
        return res

    def get_neighbors(self, weights):
        self.iterations_count += 1
        next_weights = copy.deepcopy(weights)
        unit_fraction = self.delta_unit / len(weights)
        next_weights -= unit_fraction
        yield next_weights

        for i in range(len(next_weights)):
            weight_modification = self.delta_unit
            next_weights[i] += weight_modification
            yield next_weights
            next_weights[i] -= weight_modification

    def is_better(self, first_score: int, second_score: int) -> bool:
        is_better = first_score > second_score + self._epsilon_is_weighting_better
        logger.info('| is weight better: {} > {} + {} --> {}'
                    .format(first_score, second_score, self._epsilon_is_weighting_better, is_better))
        return is_better

    def enough_iterations(self) -> bool:
        return self.iterations_count >= self._max_iterations


def dump_weights(weights):
    f = open(learned_weights_file_name + str(time.time()), 'wb+')
    pickle.dump(weights, f)


def load_weights(file_name) -> Dict[Any, float]:
    f = open(file_name, 'rb+')
    return pickle.load(f)


def main():
    pool = 5
    space = WeightsSpace(pool)
    previous_result, result = (Winner.default_winning_weights, Winner.default_winning_weights)
    for i in range(5):
        space.iterations_count = 0
        result = first_choice_hill_climbing(space, result)
        filey = open('/cs/usr/ethan.tempel/Documents/AI/finalproject/train_and_test/weights/TOMERKING' + str(i), 'w+')
        filey.write(repr(result))
        if result == previous_result:
            break
        previous_result = result
        space.delta_unit /= 2
        dump_weights(result)


if __name__ == '__main__':
    main()
