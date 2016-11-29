import os

from game.catan_state import CatanState
from players.alpha_beta_player import AlphaBetaPlayer
from players.random_player import RandomPlayer
from train_and_test.logger import logger


def scores_changed(state, previous_scores, scores):
    for player in state.players:
        if previous_scores[player] != scores[player]:
            return True
    return False


def clean_previous_images():
    for file_name in os.listdir():
        if file_name.split(sep='_')[0] == 'turn':
            os.remove(file_name)


def execute_game():
    seed = 234
    timeout_seconds = 1

    p1 = AlphaBetaPlayer(seed, timeout_seconds)

    def h(s: CatanState):
        score = 0
        for player, sign in [(p1, 1), (p2, -1)]:
            locations = s.board.get_locations_colonised_by_player(player)
            for location in locations:
                factor = s.board.get_colony_type_at_location(location).value
                for dice_value in s.board.get_surrounding_dice_values(location):
                    score += s.probabilities_by_dice_values[dice_value] * factor * sign
            roads = s.board.get_roads_paved_by_player(player)
            for road in roads:
                factor = 0.5
                for dice_value in s.board.get_adjacent_to_path_dice_values(road):
                    score += s.probabilities_by_dice_values[dice_value] * factor * sign
        return score

    p1.set_heuristic(h)
    # p2 = AlphaBetaPlayer(seed, timeout_seconds)
    p2 = RandomPlayer(seed)
    state = CatanState([p1, p2], seed)

    clean_previous_images()

    turn_count = 0
    previous_scores = state.get_scores_by_player()
    logger.info('| {}| turn: {:3} | game start |'
                .format(''.join('{} '.format(v) for v in previous_scores.values()), turn_count))
    state.board.plot_map('turn_{}_scores_{}.png'
                         .format(turn_count, ''.join('{}_'.format(v) for v in previous_scores.values())))

    while not state.is_final():
        logger.info('-----------------p{}\'s turn-----------------'.format(state._current_player_index))
        turn_count += 1
        robber_placement = state.board.get_robber_land()

        move = state.get_current_player().choose_move(state)
        # --------------------------------------
        # TODO remove
        if __debug__ and scores_changed(state, previous_scores, state.get_scores_by_player()):
            logger.error('~BUG choose move changed score~')
            exit(1)
        # --------------------------------------
        state.make_move(move)
        state.make_random_move()

        current_scores = state.get_scores_by_player()
        score_changed = scores_changed(state, previous_scores, current_scores)
        if score_changed:
            previous_scores = current_scores

        if move.is_doing_anything():
            move_data = {k: v for k, v in move.__dict__.items() if v and k != 'resources_updates' and not
                         (k == 'robber_placement_land' and v == robber_placement) and not
                         (isinstance(v, dict) and sum(v.values()) == 0)}
            logger.info('| {}| turn: {:3} | move:{} |'
                        .format(''.join('{} '.format(v) for v in previous_scores.values()), turn_count, move_data))
            state.board.plot_map('turn_{}_{}.png'
                                 .format(turn_count, ''.join('{}_'.format(v) for v in previous_scores.values())))
        elif __debug__ and score_changed:
            # TODO remove
            logger.error('~BUG. score changed, without movement | p1 {}:p2 {} | turn: {}'
                         .format(current_scores[p1], current_scores[p2], turn_count))
            exit(1)
    logger.info('| {}| turn: {:3} | game end |'.format(''.join('{} '.format(previous_scores.values())), turn_count))


def main():
    for _ in range(1):
        execute_game()

if __name__ == '__main__':
    main()
