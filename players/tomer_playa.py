from game.catan_state import CatanState
from players.expectimax_baseline_player import ExpectimaxBaselinePlayer
from players.expectimax_weighted_probabilities_with_filter_player import *
from players.abstract_player import *
from game.resource import *
from game.board import *
from game.pieces import *
from game.development_cards import *
from math import *
import numpy as np

import copy
from players.random_player import RandomPlayer
from collections import Counter
from players.filters import create_monte_carlo_filter


MAX_ITERATIONS = 10


class ExpecTomer(ExpectimaxBaselinePlayer):

    def __init__(self, player_id, seed=None, timeout_seconds=5):
        super().__init__(id=player_id, seed=seed, timeout_seconds=timeout_seconds, heuristic=self.tomeristic, filter_moves=create_monte_carlo_filter(seed), filter_random_moves=create_monte_carlo_filter(seed, 10))


    def choose_resources_to_drop(self) -> Dict[Resource, int]:
        # if self.tomer_in_first_phase(state):
        #     return self.tomer_drops_mic_in_first_phase(state)
        # return self.tomer_drops_mic_in_final_phase(state)
        if sum(self.resources.values()) < 8:
            return {}
        resources_count = sum(self.resources.values())
        resources_to_drop_count = ceil(resources_count / 2)
        if self.can_settle_city() and resources_count >= sum(ResourceAmounts.city.values()) * 2:
            self.remove_resources_and_piece_for_city()
            resources_to_drop = copy.deepcopy(self.resources)
            self.add_resources_and_piece_for_city()

        elif self.can_settle_settlement() and resources_count >= sum(ResourceAmounts.settlement.values()) * 2:
            self.remove_resources_and_piece_for_settlement()
            resources_to_drop = copy.deepcopy(self.resources)
            self.add_resources_and_piece_for_settlement()

        elif (self.has_resources_for_development_card() and
              resources_count >= sum(ResourceAmounts.development_card.values()) * 2):
            self.remove_resources_for_development_card()
            resources_to_drop = copy.deepcopy(self.resources)
            self.add_resources_for_development_card()

        elif self.can_pave_road() and resources_count >= sum(ResourceAmounts.road.values()) * 2:
            self.remove_resources_and_piece_for_road()
            resources_to_drop = copy.deepcopy(self.resources)
            self.add_resources_and_piece_for_road()

        else:
            return RandomPlayer.choose_resources_to_drop(self)

        resources_to_drop = [resource for resource, count in resources_to_drop.items() for _ in range(count)]
        return Counter(self._random_choice(resources_to_drop, resources_to_drop_count, replace=False))


    def drop_resources_in_first_phase(self, state):
        return None


    def drop_resources_in_final_phase(self, state):
        return None


    def filmer_toves(self, next_moves, state):
        return next_moves


    def filter_moves(self, next_moves, state):
        return []


    def tomeristic(self, state: CatanState):
        # as discussed with Shaul, this isn't zero-sum heuristic, but a max-gain approach where only own player's
        # value is is taken in account
        if state.is_initialisation_phase():
            return self.heuristic_initialisation_phase(state)
        if self.in_first_phase(state):
            return self.heuristic_first_phase(state)
        return self.heuristic_final_phase(state)


    def in_first_phase(self, state):
        my_victory_points = int(state.get_scores_by_player()[self])
        return my_victory_points <= 7


    def heuristic_initialisation_phase(self, state):
        pass


    def heuristic_first_phase(self, state):
        """
        prefer higher expected resource yield, rather than VP.
        also reward having places to build settlements.
        :param state: the current state of the game.
        :param player: our player.
        :return: returns a score for this state.
        """
        board = state.board
        scores_by_players = state.get_scores_by_player()

        # how many cards of each resource we have right now
        brick_count = self.get_resource_count(Resource.Brick)
        lumber_count = self.get_resource_count(Resource.Lumber)
        wool_count = self.get_resource_count(Resource.Wool)
        grain_count = self.get_resource_count(Resource.Grain)
        ore_count = self.get_resource_count(Resource.Ore)

        # what is our trading ratio for each resource
        brick_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Brick)
        lumber_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Lumber)
        wool_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Wool)
        grain_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Grain)
        ore_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Ore)

        resource_expectation = ExpecTomer.get_resource_expectation(self, state)

        # the number of unexposed development cards, except for VP dev cards.
        num_dev_cards = sum(self.unexposed_development_cards) - self.unexposed_development_cards[DevelopmentCard.VictoryPoint]

        avg_vp_diff = ExpecTomer.get_avg_vp_difference(scores_by_players, self)
        max_vp_diff = ExpecTomer.get_max_vp_difference(scores_by_players, self)

        can_build_settlement = 1 if self.can_settle_settlement() else 0
        can_build_city = 1 if self.can_settle_city() else 0
        can_build_dev_card = 1 if self.has_resources_for_development_card() else 0

        num_places_to_build = len(board.get_settleable_locations_by_player())

        values = np.array([brick_count, lumber_count, wool_count, grain_count,
                           ore_count, resource_expectation[Resource.Brick],
                           resource_expectation[Resource.Lumber],
                           resource_expectation[Resource.Wool],
                           resource_expectation[Resource.Grain],
                           resource_expectation[Resource.Ore],
                           resource_expectation[Resource.Brick] * (1 / brick_trade_ratio),
                           resource_expectation[Resource.Lumber] * (1 / lumber_trade_ratio),
                           resource_expectation[Resource.Wool] * (1 / wool_trade_ratio),
                           resource_expectation[Resource.Grain] * (1 / grain_trade_ratio),
                           resource_expectation[Resource.Ore] * (1 / ore_trade_ratio),
                           num_dev_cards, - avg_vp_diff, - max_vp_diff,
                           scores_by_players[self],
                           can_build_settlement, can_build_city,
                           can_build_dev_card, num_places_to_build])

        return np.sum(values)


    def heuristic_first_phase_design2(self, state, weights):
        """
        prefer higher expected resource yield, rather than VP.
        also reward having places to build settlements.
        :param state: the current state of the game.
        :param weights: a np array of weights to each value that the heuristic takes into account.
        :return: returns a score for this state.
        """

        values = np.zeros(20)

        board = state.board
        scores_by_players = state.get_scores_by_player()

        # how many cards of each resource we have right now
        values[0] = self.get_resource_count(Resource.Brick)
        values[1] = self.get_resource_count(Resource.Lumber)
        values[2] = self.get_resource_count(Resource.Wool)
        values[3] = self.get_resource_count(Resource.Grain)
        values[4] = self.get_resource_count(Resource.Ore)

        # what is our trading ratio for each resource
        brick_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Brick)
        lumber_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Lumber)
        wool_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Wool)
        grain_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Grain)
        ore_trade_ratio = ExpecTomer.calc_player_trade_ratio(self, state, Resource.Ore)

        resource_expectation = ExpecTomer.get_resource_expectation(self, state)

        # the number of unexposed development cards, except for VP dev cards.
        num_dev_cards = sum(self.unexposed_development_cards) - self.unexposed_development_cards[DevelopmentCard.VictoryPoint]

        avg_vp_diff = ExpecTomer.get_avg_vp_difference(scores_by_players, self)
        max_vp_diff = ExpecTomer.get_max_vp_difference(scores_by_players, self)

        can_build_settlement = 1 if self.can_settle_settlement() else 0
        can_build_city = 1 if self.can_settle_city() else 0
        can_build_dev_card = 1 if self.has_resources_for_development_card() else 0

        num_places_to_build = len(board.get_settleable_locations_by_player())

        values = np.array([brick_count, lumber_count, wool_count, grain_count,
                           ore_count, resource_expectation[Resource.Brick],
                           resource_expectation[Resource.Lumber],
                           resource_expectation[Resource.Wool],
                           resource_expectation[Resource.Grain],
                           resource_expectation[Resource.Ore],
                           resource_expectation[Resource.Brick] * (1 / brick_trade_ratio),
                           resource_expectation[Resource.Lumber] * (1 / lumber_trade_ratio),
                           resource_expectation[Resource.Wool] * (1 / wool_trade_ratio),
                           resource_expectation[Resource.Grain] * (1 / grain_trade_ratio),
                           resource_expectation[Resource.Ore] * (1 / ore_trade_ratio),
                           num_dev_cards, - avg_vp_diff, - max_vp_diff,
                           scores_by_players[self],
                           can_build_settlement, can_build_city,
                           can_build_dev_card, num_places_to_build])

        return np.sum(values)


    def heuristic_final_phase(self, state):
        scores_by_players = state.get_scores_by_player()
        can_build_dev_card = 1 if self.has_resources_for_development_card() else 0

        resource_expectation = ExpecTomer.get_resource_expectation(self,
                                                                   state)

        return 2 * scores_by_players[self] + 4 * can_build_dev_card + sum([resource_expectation[Resource.Brick],
                                                                           resource_expectation[Resource.Lumber],
                                                                           resource_expectation[Resource.Wool],
                                                                           resource_expectation[Resource.Grain],
                                                                           resource_expectation[Resource.Ore]])


    @staticmethod
    def calc_player_trade_ratio(player, state, source_resource: Resource):
        """
        return 2, 3 or 4 based on the current players harbors status
        :param source_resource: the resource the player will give
        :return: 2, 3 or 4 - the number of resource units the player will give for a single card
        """
        if state.board.is_player_on_harbor(player, Harbor(source_resource.value)):
            return 2
        if state.board.is_player_on_harbor(player, Harbor.HarborGeneric):
            return 3
        return 4


    @staticmethod
    def get_resource_expectation(player, state):
        # TODO: check that this function works properly
        """
        calculates the expected resource yield per one turn per player.
        :return: a dictionary of the resource expectation of the given player.
        each resource is a key, and it's value is that player's expected yield.
        """
        res_yield = {Colony.Settlement: 1, Colony.City: 2}
        resources = {r: 0 for r in Resource}

        for location in state.board.get_locations_colonised_by_player(player):
            colony_yield = res_yield[state.board.get_colony_type_at_location(location)]
            for land in state.board._roads_and_colonies.node[location][Board.lands]:  # the adjacent lands to the location we check
                resources[land.resource] += colony_yield * state.probabilities_by_dice_values[land.dice_value]

        return resources


        # for player, factor in self._players_and_factors:
        #     for location in s.board.get_locations_colonised_by_player(player):
        #         weight = self.weights[s.board.get_colony_type_at_location(location)]
        #         for dice_value in s.board.get_surrounding_dice_values(location):
        #             score += s.probabilities_by_dice_values[dice_value] * weight * factor


        # return [land.resource for land in
        #         self._roads_and_colonies.node[location][Board.lands]
        #         if land.resource is not None]


    @staticmethod
    def get_avg_vp_difference(score_by_players, player):
        """
        :return: the average difference between the player's vp, and other players vp.
        """
        return sum(score_by_players[player] - score_by_players[other] for other in score_by_players.keys if other != player) / len(score_by_players)


    @staticmethod
    def get_max_vp_difference(score_by_player, player):
        """
        :return: the maximal difference between the player's vp, and other players vp.
        """
        return max(score_by_player[player] - score_by_player[other] for other in score_by_player.keys if other != player)
