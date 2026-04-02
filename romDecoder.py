import socket
import json
from typing import Optional, Callable
from pokemon import Pokemon
from battle_state import BattleState
from gen4_data import NATURE_ID_TO_NAME, parse_status_byte, ITEM_IDS
from database import read_pokemon, read_move

HOST = "127.0.0.1"
PORT = 6000


class RomDecoder:
    """
    TCP server that accepts a connection from the DeSmuME Lua script (battle_reader.lua)
    and converts raw memory reads into BattleState objects.

    Protocol: one JSON object per line, newline-terminated.
    The Lua script is the client; Python is the server.

    Example JSON frame:
    {
        "player": {
            "species": 392, "hp_curr": 156, "hp_max": 301, "level": 55,
            "status": 0, "moves": [394, 396, 370, 179], "pp": [8, 8, 8, 8],
            "attack": 159, "defense": 104, "speed": 145,
            "spattack": 159, "spdefense": 104,
            "ability": 0, "nature": 3, "item": 247
        },
        "opponent": { ... },
        "weather": 0,
        "turn": 1
    }
    """

    # Weather byte values in Platinum
    WEATHER_MAP = {
        0: "clear",
        1: "harsh sunlight",
        2: "rain",
        3: "sandstorm",
        4: "hail",
    }

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self._server_sock: Optional[socket.socket] = None
        self._conn: Optional[socket.socket] = None
        self._buf = ""

    def start_server(self) -> None:
        """Open the listening socket and wait for the Lua client to connect."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(1)
        print(f"[RomDecoder] Waiting for DeSmuME connection on {self.host}:{self.port}...")
        self._conn, addr = self._server_sock.accept()
        print(f"[RomDecoder] Connected: {addr}")

    def receive_battle_state(self) -> Optional[BattleState]:
        """
        Block until a complete JSON line arrives and parse it into a BattleState.
        Returns None if the connection is closed.
        """
        while "\n" not in self._buf:
            chunk = self._conn.recv(4096)
            if not chunk:
                return None
            self._buf += chunk.decode("utf-8")

        line, self._buf = self._buf.split("\n", 1)
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"[RomDecoder] JSON parse error: {e}")
            return None

        return self._parse_frame(data)

    def run_loop(self, on_state: Callable[[BattleState], None]) -> None:
        """Receive loop. Calls on_state(state) for every new battle state received."""
        while True:
            state = self.receive_battle_state()
            if state is None:
                print("[RomDecoder] Connection closed.")
                break
            on_state(state)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
        if self._server_sock:
            self._server_sock.close()

    # -------------------------------------------------------------------------
    # Parsing helpers
    # -------------------------------------------------------------------------

    def _parse_frame(self, data: dict) -> BattleState:
        player_pokemon = self._parse_slot(data["player"])
        opponent_pokemon = self._parse_slot(data["opponent"])
        weather = self.WEATHER_MAP.get(data.get("weather", 0), "clear")
        turn = data.get("turn", 0)
        return BattleState(
            player_active=player_pokemon,
            opponent_active=opponent_pokemon,
            player_party=[player_pokemon],
            opponent_party_count=data.get("opponent_party_count", 1),
            weather=weather,
            turn_number=turn,
        )

    def _parse_slot(self, slot: dict) -> Pokemon:
        species_id = slot["species"]
        level = slot["level"]
        hp_curr = slot["hp_curr"]
        hp_max = slot["hp_max"]
        status_byte = slot.get("status", 0)
        move_ids = slot.get("moves", [])
        pps = slot.get("pp", [None, None, None, None])
        ability_slot = slot.get("ability", 0)
        item_id = slot.get("item", 0)

        item_name = ITEM_IDS.get(item_id, "")
        status_str = parse_status_byte(status_byte)

        # Resolve species name via PokéAPI cache
        species_data = read_pokemon(species_id)
        species_name = species_data["name"]

        # Resolve move names via PokéAPI cache; filter out empty slots (id=0)
        move_names = []
        for mid in move_ids:
            if mid and mid != 0:
                move_data = read_move(mid)
                move_names.append(move_data["name"])

        # Stats from ROM (already calculated battle stats, not base stats)
        stats = [
            slot.get("attack", 1),
            slot.get("defense", 1),
            slot.get("speed", 1),
            slot.get("spattack", 1),
            slot.get("spdefense", 1),
        ]

        # EVs and IVs are not directly readable from battle RAM; use 0 as defaults.
        # Nature modifiers are already baked into the ROM stats, so we pass
        # "hardy" (neutral) to avoid double-applying the modifier in Pokemon.__init__.
        evs = [0, 0, 0, 0, 0, 0]
        ivs = [0, 0, 0, 0, 0, 0]

        p = Pokemon(
            species=species_name,
            moves=move_names,
            item=item_name,
            nature="hardy",  # stats already include nature; don't double-apply
            ability=ability_slot,
            level=level,
            hp=(hp_curr, hp_max),
            stats=stats,
            evs=evs,
            ivs=ivs,
            friendship=0,
            exp=0,
        )
        p.status = status_str
        # Sync PP from ROM onto the Move objects
        for i, move in enumerate(p.moves):
            if i < len(pps) and pps[i] is not None:
                move.pp = pps[i]
        return p
