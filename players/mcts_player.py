
from game.catan_state import CatanState

from players.expectimax_baseline_player import ExpectimaxBaselinePlayer
from algorithms.mcts import MCTS, MCTSNode


class MCTSPlayer(ExpectimaxBaselinePlayer):
    """
    This class defines a player that chooses best move by using the MCTS algorithm
    """
    def __init__(self, id, seed=None, iterations=10000, exploration_param=1.4):
        assert seed is None or (isinstance(seed, int) and seed > 0)
        super().__init__(id, seed)

        self.iterations = iterations
        self.exploration_param = exploration_param

    def choose_move(self, state: CatanState):
        mcts = MCTS(MCTSNode(state), self.exploration_param)
        mcts.do_n_rollouts(self.iterations)
        return mcts.choose().move


