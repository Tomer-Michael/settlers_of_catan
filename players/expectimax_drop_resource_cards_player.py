from players.expectimax_baseline_player import ExpectimaxBaselinePlayer


class ExpectimaxDropResourceCardsPlayer(ExpectimaxBaselinePlayer):
    def __init__(self, id, seed=None, timeout_seconds=5):
        super().__init__(id, seed, timeout_seconds, self.drop_resource_cards_heuristic)

    def drop_resource_cards_heuristic(self, s):
        return -sum(self.resources.values())
