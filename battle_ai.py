import copy
from typing import Tuple
from pokeAI import Battle


class BattleAI:
    """
    Recommends the best move for the player at the current battle state.

    Uses expectiminimax with alpha-beta pruning at the specified depth.
    Depth 4 = 2 full turns of lookahead (player pick -> opponent pick -> execute, repeated).
    """

    def __init__(self, battle: Battle, depth: int = 4):
        self.battle = battle
        self.depth = depth

    def recommend_move(self) -> Tuple[int, float]:
        """
        Evaluate all legal player moves and return (best_move_index, expected_score).
        Score is from the player's perspective: higher is better for the player.
        """
        player = self.battle.player_party[0]
        best_score = float("-inf")
        best_idx = 0

        for i, move in enumerate(player.moves):
            if move.pp is not None and move.pp <= 0:
                continue
            if move.power is None or move.power == 0:
                # skip status moves at the top level for now; they're evaluated recursively
                continue
            state_copy = self._copy_battle(self.battle)
            score = self._expectiminimax(state_copy, self.depth - 1, False, float("-inf"), float("inf"), i)
            if score > best_score:
                best_score = score
                best_idx = i

        return best_idx, best_score

    def _expectiminimax(self, battle: Battle, depth: int, maximizing: bool,
                        alpha: float, beta: float, player_move_idx: int = 0) -> float:
        """
        Expectiminimax with alpha-beta pruning.

        maximizing=True  -> player is choosing their move (maximize score)
        maximizing=False -> opponent is choosing their move (minimize score)

        When depth reaches 0 or the battle is over, evaluate the position.
        """
        player = battle.player_party[0]
        ai = battle.AI_party[0]

        if depth == 0 or player.hpcurr <= 0 or ai.hpcurr <= 0:
            return self._evaluate(battle)

        if maximizing:
            # Player chooses a move to maximize their score
            best = float("-inf")
            for i, move in enumerate(player.moves):
                if move.pp is not None and move.pp <= 0:
                    continue
                state_copy = self._copy_battle(battle)
                val = self._expectiminimax(state_copy, depth - 1, False, alpha, beta, i)
                best = max(best, val)
                alpha = max(alpha, best)
                if beta <= alpha:
                    break  # beta cut-off
            return best
        else:
            # Opponent chooses a move to minimize the player's score
            worst = float("inf")
            for j, move in enumerate(ai.moves):
                if move.pp is not None and move.pp <= 0:
                    continue
                state_copy = self._copy_battle(battle)
                # Execute this (player_move_idx, j) pair and recurse
                state_copy.execute_turn(player_move_idx, j)
                val = self._expectiminimax(state_copy, depth - 1, True, alpha, beta)
                worst = min(worst, val)
                beta = min(beta, worst)
                if beta <= alpha:
                    break  # alpha cut-off
            return worst

    def _evaluate(self, battle: Battle) -> float:
        """
        Heuristic evaluation from the player's perspective.
        Returns a score where higher values favor the player.
        """
        player = battle.player_party[0]
        ai = battle.AI_party[0]

        player_hp_ratio = player.hpcurr / player.hpmax if player.hpmax > 0 else 0
        ai_hp_ratio = ai.hpcurr / ai.hpmax if ai.hpmax > 0 else 0

        # Count living party members
        player_alive = sum(1 for p in battle.player_party if p.hpcurr > 0)
        ai_alive = battle.AI_party  # only active Pokemon tracked for AI

        score = (player_hp_ratio * 100) - (ai_hp_ratio * 100)
        score += player_alive * 10

        # Bonus/penalty for status conditions
        if player.status in ("burned", "poisoned", "badly_poisoned", "paralyzed"):
            score -= 5
        if ai.status in ("burned", "poisoned", "badly_poisoned", "paralyzed"):
            score += 5

        return score

    @staticmethod
    def _copy_battle(battle: Battle) -> Battle:
        """Return a deep copy of the battle state for simulation."""
        return copy.deepcopy(battle)
