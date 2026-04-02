from romDecoder import RomDecoder
from pokeAI import Battle
from battle_ai import BattleAI
from battle_state import BattleState


def on_battle_state(state: BattleState) -> None:
    """Called whenever a new battle state is received from DeSmuME."""
    battle = Battle(
        player_party=[state.player_active],
        AI_party=[state.opponent_active],
    )
    battle.weather = state.weather

    ai = BattleAI(battle, depth=4)
    move_idx, score = ai.recommend_move()

    player = state.player_active
    if move_idx < len(player.moves):
        move = player.moves[move_idx]
        print(f"\nTurn {state.turn_number} | {player.species} vs {state.opponent_active.species}")
        print(f"  Recommended: {move.name}  (score: {score:.1f})")
        for i, m in enumerate(player.moves):
            marker = " <--" if i == move_idx else ""
            print(f"    [{i+1}] {m.name}{marker}")
    else:
        print(f"Turn {state.turn_number}: no valid move found (all PP exhausted?)")


def main():
    decoder = RomDecoder()
    try:
        decoder.start_server()
        decoder.run_loop(on_battle_state)
    except KeyboardInterrupt:
        print("\n[main] Shutting down.")
    finally:
        decoder.close()


if __name__ == "__main__":
    main()
