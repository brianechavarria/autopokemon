from dataclasses import dataclass, field
from typing import List, Optional
from pokemon import Pokemon


@dataclass
class BattleState:
    """Snapshot of a battle as read from the emulator or constructed manually.
    This is the contract between the DeSmuME integration and the battle simulator."""
    player_active: Pokemon
    opponent_active: Pokemon
    player_party: List[Pokemon] = field(default_factory=list)
    opponent_party_count: int = 1  # only count is reliably knowable from ROM
    weather: str = "clear"
    turn_number: int = 0
