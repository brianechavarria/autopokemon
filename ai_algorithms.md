# AI Algorithm Options for Pokemon Battle Recommendation

This document compares three approaches for recommending moves in a Pokemon battle.
The implemented algorithm is **Expectiminimax with alpha-beta pruning**.

---

## 1. Greedy (Pick Highest Expected Damage)

### How it works
For each of the player's moves, compute `damage_calc()` against the opponent using the
expected random factor (92.5%, the midpoint of 85–100%). Pick the move with the highest
expected damage output.

### Pseudocode
```python
def recommend_move(player, opponent, battle):
    return max(range(4), key=lambda i:
        battle.damage_calc(player, player.moves[i], opponent, True, False))
```

### Pros
- **O(1) per turn** — four calls to `damage_calc()` regardless of game state
- Trivial to implement correctly
- Works well when the goal is simply maximizing raw damage output
- Good enough for straightforward "hit hard" situations (e.g. choice item users)

### Cons
- **Ignores the opponent's next move entirely.** Cannot reason about being knocked out before
  getting to attack.
- **Never sets up.** Will never use Dragon Dance or Swords Dance, even if doing so leads to
  a guaranteed KO on the next turn.
- **Doesn't reason about type immunities.** If the opponent is immune to the highest-damage
  move, greedy wastes the turn rather than switching to a coverage move.
- **Context-blind.** Makes the exact same recommendation in every situation with the same
  active Pokemon, regardless of HP, stat changes, or field conditions.

### Verdict
Useful as a baseline to validate that the damage formula is working, but not suitable as a
final recommendation engine.

---

## 2. Expectiminimax with Alpha-Beta Pruning *(Implemented)*

### How it works
Builds a game tree alternating between:
- **Max nodes** — the player picks a move to maximize their score
- **Min nodes** — the opponent picks a move to minimize the player's score (assumes optimal play)
- **Chance nodes** — random damage rolls are handled by using expected values rather than
  sampling, which keeps the tree deterministic

Alpha-beta pruning cuts branches of the tree that cannot affect the final result, reducing
the effective branching factor from 4×4=16 to roughly 4–6 nodes per ply in practice.

**Depth 4** = 2 full turns of lookahead:
```
Player picks move  →  Opponent picks move  →  Execute turn  →  [repeat once more]  →  Evaluate
```

### Pseudocode
```python
def expectiminimax(battle, depth, maximizing, alpha, beta):
    if depth == 0 or battle_over(battle):
        return evaluate(battle)

    if maximizing:
        best = -inf
        for each player_move:
            score = expectiminimax(copy(battle), depth-1, False, alpha, beta)
            best = max(best, score)
            alpha = max(alpha, best)
            if beta <= alpha: break  # prune
        return best
    else:
        worst = +inf
        for each opponent_move:
            execute_turn(battle, player_move, opponent_move)
            score = expectiminimax(copy(battle), depth-1, True, alpha, beta)
            worst = min(worst, score)
            beta = min(beta, worst)
            if beta <= alpha: break  # prune
        return worst
```

### Evaluation heuristic
```
score = (player_hp / player_max_hp) * 100
      - (opponent_hp / opponent_max_hp) * 100
      + player_alive_party_count * 10
      - status_penalties
```

### Pros
- **Captures multi-turn reasoning.** "I should use Swords Dance now because I outspeed and
  will KO next turn" is a decision depth-4 finds naturally.
- **Handles priority moves correctly.** Quick Attack going before a faster opponent's attack
  is modeled in `_turn_order()`.
- **Type coverage.** Naturally prefers a 2× effective move over a higher-BP resisted move
  when the former leads to a KO.
- **Fast enough in Python.** Worst case at depth 4: 4^4 = 256 leaf nodes per recommendation.
  Each leaf is a few arithmetic operations. Well under 1ms per call.
- **Alpha-beta pruning** typically cuts this to ~20–50 nodes evaluated in practice.

### Cons
- **Assumes optimal opponent play.** Will be pessimistic against NPC AI that uses moves
  randomly or sub-optimally. Can lead to unnecessarily conservative recommendations.
- **State explosion at depth > 6.** 4^6 = 4096 nodes without pruning. Acceptable at depth
  6 but starts to matter at depth 8+ for large parties.
- **Partial information.** In a real battle, the opponent's moves may be unknown. The simulator
  evaluates all possible opponent moves, which is correct but may over-weight unlikely choices.
- **No switching logic yet.** Only evaluates using the active Pokemon; doesn't reason about
  whether to switch to a better matchup.

### Verdict
The right choice for this project. Handles Gen 4 battle complexity well at depth 4, is fast
enough for real-time use alongside a DeSmuME session, and the implementation is straightforward.

---

## 3. Monte Carlo Tree Search (MCTS)

### How it works
Rather than exhaustively building a game tree, MCTS runs many **simulations** (rollouts)
from the current state and uses statistics from those simulations to estimate which move is best.

Each iteration consists of four steps:
1. **Selection** — traverse the existing tree using UCB1 to balance exploration vs. exploitation
2. **Expansion** — add a new node to the tree for an unvisited move
3. **Simulation (rollout)** — play out the game randomly (or with a heuristic policy) until a terminal state
4. **Backpropagation** — update win/score statistics for all nodes on the path

UCB1 formula for node selection:
```
UCB1 = avg_score + C * sqrt(ln(parent_visits) / node_visits)
```
where C controls the exploration-exploitation tradeoff.

### Pros
- **No hand-crafted heuristic needed.** The evaluation comes from the rollout outcomes rather
  than a manually tuned formula.
- **Anytime algorithm.** More computation time → better recommendations. Works under any
  time budget.
- **Handles large branching factors.** Scales better than minimax for games with 10+ choices
  per turn (not relevant for 4-move Pokemon, but useful for future extensions).
- **More naturally handles partial information.** Can sample from a distribution of possible
  opponent moves rather than assuming perfect play.
- **Can discover non-obvious strategies** that a hand-coded heuristic might undervalue (e.g.
  stall strategies that win through poison + leftovers).

### Cons
- **Noisy rollouts.** Random Pokemon battles are very noisy — a single critical hit can
  completely change the outcome of a rollout, requiring many more iterations to converge.
  Typically needs 1000–5000 rollouts for reliable recommendations.
- **Requires a rollout policy.** Pure random rollouts in Pokemon converge slowly. A good
  rollout policy (e.g. "always pick the highest damage move during rollout") is needed, which
  partially defeats the advantage of not needing a heuristic.
- **Much more complex to implement correctly.** UCB1 tree management, backpropagation,
  and rollout policy add ~300–500 lines of carefully tested code vs. ~100 for expectiminimax.
- **Overkill for 4-move 1v1.** The branching factor is only 4, making exhaustive minimax
  faster and more accurate than sampling-based MCTS for the depth levels we need.

### Verdict
Not recommended for this project in its current scope. Worth revisiting if the simulator is
extended to include full-party switching decisions, where the branching factor becomes large
enough that exhaustive search is infeasible.

---

## Summary

| Criterion | Greedy | Expectiminimax (implemented) | MCTS |
|-----------|--------|------------------------------|------|
| Implementation complexity | Low | Medium | High |
| Multi-turn reasoning | No | Yes | Yes |
| Optimality guarantee | No | Yes (at given depth) | Approximate |
| Speed (4 moves, depth 4) | <0.1ms | <1ms | ~100ms (1000 rollouts) |
| Handles unknown opponent moves | No | Assumes optimal | Can sample distribution |
| Switching decisions | No | Not yet | Yes (with work) |
| Recommended | Baseline only | **Yes** | Future extension |
