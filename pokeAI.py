from pokemon import *
from type_chart import get_type_effectiveness
from gen4_data import HIGH_CRIT_MOVES
import random
import copy
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TurnResult:
    player_damage: int = 0
    ai_damage: int = 0
    log: List[str] = None

    def __post_init__(self):
        if self.log is None:
            self.log = []


class Battle:

    def __init__(self, player_party, AI_party, double_battle=False):
        # each party should be a list of objects of the pokemon class
        self.player_party = player_party
        self.AI_party = AI_party
        self.weather = "clear"
        self.player_effect = 0
        self.AI_effect = 0
        self.double_battle = double_battle
        self.trick_room = False
        self.player_metronome = {"count": 0, "last_move": None}
        self.ai_metronome = {"count": 0, "last_move": None}


    def AImove(self):
        return 1


    # player_check is True if the player is attacking and False if the AI is
    def damage_calc(self, attacker, attack_move, defender, player_check, multi_target):
        # capture edge case for the move beat up
        if attack_move.name == "beat-up":
            level = defender.level
        else:
            level = attacker.level

        # a and d depend on whether the attack is physical or special
        if attack_move.damage_class == "physical":
            a = attacker.attack
            d = defender.defense
            atk_stage = attacker.stat_stages["attack"]
            def_stage = defender.stat_stages["defense"]
        else:
            a = attacker.spattack
            d = defender.spdefense
            atk_stage = attacker.stat_stages["spattack"]
            def_stage = defender.stat_stages["spdefense"]

        # check for critical early so we can handle stage interactions
        critical_check = self.critical_calc(attack_move, attacker, defender)
        if critical_check:
            # on a crit, ignore negative attacker stages and positive defender stages
            atk_stage = max(atk_stage, 0)
            def_stage = min(def_stage, 0)

        a = int(a * Pokemon.get_stage_modifier(atk_stage))
        d = int(d * Pokemon.get_stage_modifier(def_stage))

        # determine burn modifier
        if (attacker.status == "burned") and (attacker.ability.name != "guts") and (attack_move.damage_class == "physical"):
            burn = 0.5
        else:
            burn = 1

        # check for screen effect
        if player_check:
            if ((attack_move.damage_class == "physical") and (self.AI_effect == "reflect")) or \
               ((attack_move.damage_class == "special") and (self.AI_effect == "light screen")):
                screen = 2/3 if self.double_battle else 0.5
            else:
                screen = 1
        else:
            if ((attack_move.damage_class == "physical") and (self.player_effect == "reflect")) or \
               ((attack_move.damage_class == "special") and (self.player_effect == "light screen")):
                screen = 2/3 if self.double_battle else 0.5
            else:
                screen = 1

        # on a critical hit, screens are bypassed
        if critical_check:
            screen = 1

        # adjust based on number of targets in doubles
        targets = 0.75 if multi_target else 1

        # adjust for weather dependent moves
        if (attacker.ability.name in ("cloud-nine", "air-lock")) or \
           (defender.ability.name in ("cloud-nine", "air-lock")):
            weather_effect = 1
        elif self.weather == "harsh sunlight":
            if attack_move.move_type == "fire":
                weather_effect = 1.5
            elif attack_move.move_type == "water":
                weather_effect = 0.5
            elif attack_move.name == "solar-beam":
                weather_effect = 1  # charges instantly, no penalty
            else:
                weather_effect = 1
        elif self.weather == "rain":
            if attack_move.move_type == "water":
                weather_effect = 1.5
            elif attack_move.move_type == "fire":
                weather_effect = 0.5
            else:
                weather_effect = 1
        elif self.weather in ("sandstorm", "hail"):
            if attack_move.name == "solar-beam":
                weather_effect = 0.5
            else:
                weather_effect = 1
        else:
            weather_effect = 1

        # check for flash fire
        flash_fire_effect = 1.5 if (attack_move.move_type == "fire") and attacker.flash_fire else 1

        # critical hit multiplier
        if critical_check:
            critical = 3 if attacker.ability.name == "sniper" else 2
        else:
            critical = 1

        # item effects
        if attacker.item == "life-orb":
            item_effect = 1.3
        elif attacker.item == "metronome":
            n = self.metronome_check(player_check, attack_move.name)
            item_effect = 1 + n / 10
        elif attacker.item == "expert-belt":
            type_eff = get_type_effectiveness(attack_move.move_type, defender.type1, defender.type2)
            item_effect = 1.2 if type_eff > 1 else 1
        elif attacker.item in ("choice-band", "muscle-band") and attack_move.damage_class == "physical":
            item_effect = 1.5 if attacker.item == "choice-band" else 1.1
        elif attacker.item in ("choice-specs", "wise-glasses") and attack_move.damage_class == "special":
            item_effect = 1.5 if attacker.item == "choice-specs" else 1.1
        else:
            item_effect = 1

        # thick fat halves fire and ice damage against defender
        if defender.ability.name == "thick-fat" and attack_move.move_type in ("fire", "ice"):
            thick_fat = 0.5
        else:
            thick_fat = 1

        # me first (TODO: implement properly; placeholder)
        me_first = 1

        # random factor (spit up always rolls 100%)
        random_factor = 1 if attack_move.name == "spit-up" else random.randint(85, 100) / 100

        # STAB factor
        if attack_move.move_type in (attacker.type1, attacker.type2):
            stab = 2 if attacker.ability.name == "adaptability" else 1.5
        else:
            stab = 1

        # type effectiveness
        type_eff = get_type_effectiveness(attack_move.move_type, defender.type1, defender.type2)

        # ability-based type immunities (override type chart where needed)
        if defender.ability.name == "levitate" and attack_move.move_type == "ground":
            type_eff = 0
        if defender.ability.name in ("water-absorb", "dry-skin") and attack_move.move_type == "water":
            type_eff = 0
        if defender.ability.name == "volt-absorb" and attack_move.move_type == "electric":
            type_eff = 0
        if defender.ability.name == "flash-fire" and attack_move.move_type == "fire":
            type_eff = 0
        if defender.ability.name == "wonder-guard" and type_eff <= 1:
            type_eff = 0

        base = int((2 * level / 5 + 2) * attack_move.power * a / d / 50) + 2
        return int(base * burn * screen * targets * weather_effect * flash_fire_effect
                   * critical * item_effect * thick_fat * me_first * random_factor * stab * type_eff)


    def critical_calc(self, move, attacker, defender) -> bool:
        if move.name in ("future-sight", "doom-desire"):
            return False
        if defender.ability.name in ("battle-armor", "shell-armor"):
            return False
        if defender.effect == "lucky chant":
            return False

        stage = 0
        if move.name in HIGH_CRIT_MOVES:
            stage += 1
        if attacker.item in ("scope-lens", "razor-claw"):
            stage += 1
        if attacker.ability.name == "super-luck":
            stage += 1
        if getattr(attacker, "focus_energy", False):
            stage += 2

        rates = {0: 1/16, 1: 1/8, 2: 1/4, 3: 1/3, 4: 1/2}
        return random.random() < rates[min(stage, 4)]


    def metronome_check(self, is_player: bool, move_name: str) -> int:
        """Track consecutive use of the same move for the Metronome held item.
        Returns n (0-10), where item_effect = 1 + n/10."""
        tracker = self.player_metronome if is_player else self.ai_metronome
        if tracker["last_move"] == move_name:
            tracker["count"] = min(tracker["count"] + 1, 10)
        else:
            tracker["count"] = 0
            tracker["last_move"] = move_name
        return tracker["count"]


    def execute_turn(self, player_move_idx: int, ai_move_idx: int) -> TurnResult:
        """Resolve one full turn of battle. Mutates HP and status on both active Pokemon."""
        player = self.player_party[0]
        ai = self.AI_party[0]
        player_move = player.moves[player_move_idx]
        ai_move = ai.moves[ai_move_idx]

        result = TurnResult()
        ordered = self._turn_order(player, player_move, ai, ai_move)

        for attacker, move, defender, is_player in ordered:
            if attacker.hpcurr <= 0 or defender.hpcurr <= 0:
                continue
            if not self._accuracy_check(move, attacker, defender):
                result.log.append(f"{attacker.species} used {move.name} but missed!")
                continue

            dmg = self.damage_calc(attacker, move, defender, is_player, move.multitarget)
            defender.hpcurr = max(0, defender.hpcurr - dmg)
            result.log.append(f"{attacker.species} used {move.name} for {dmg} damage.")

            if is_player:
                result.player_damage += dmg
            else:
                result.ai_damage += dmg

            self._apply_move_effects(move, attacker, defender)

        self._apply_end_of_turn(player)
        self._apply_end_of_turn(ai)
        return result


    def _turn_order(self, player, player_move, ai, ai_move):
        """Return [(attacker, move, defender, is_player), ...] in execution order."""
        if player_move.priority != ai_move.priority:
            if player_move.priority > ai_move.priority:
                return [(player, player_move, ai, True), (ai, ai_move, player, False)]
            else:
                return [(ai, ai_move, player, False), (player, player_move, ai, True)]

        # same priority: compare effective speed
        player_spd = self._effective_speed(player)
        ai_spd = self._effective_speed(ai)

        # Trick Room inverts speed order
        if self.trick_room:
            player_spd, ai_spd = ai_spd, player_spd

        if player_spd > ai_spd:
            return [(player, player_move, ai, True), (ai, ai_move, player, False)]
        elif ai_spd > player_spd:
            return [(ai, ai_move, player, False), (player, player_move, ai, True)]
        else:
            # speed tie: random 50/50
            if random.random() < 0.5:
                return [(player, player_move, ai, True), (ai, ai_move, player, False)]
            else:
                return [(ai, ai_move, player, False), (player, player_move, ai, True)]


    def _effective_speed(self, pokemon) -> float:
        spd = pokemon.speed * Pokemon.get_stage_modifier(pokemon.stat_stages["speed"])
        if pokemon.status == "paralyzed":
            spd *= 0.25
        return spd


    def _accuracy_check(self, move, attacker, defender) -> bool:
        if move.accuracy is None:
            return True  # moves like Swift always hit
        acc_stage = attacker.stat_stages["accuracy"] - defender.stat_stages["evasion"]
        acc_modifier = Pokemon.get_stage_modifier(max(-6, min(6, acc_stage)))
        return random.random() < (move.accuracy / 100) * acc_modifier


    def _apply_move_effects(self, move, attacker, defender):
        """Apply stat changes and status conditions from a move's secondary effects."""
        for change in move.stat_changes:
            stat = change["stat"]["name"].replace("-", "_")
            # normalize PokéAPI stat names to our attribute names
            stat = stat.replace("special_attack", "spattack").replace("special_defense", "spdefense")
            delta = change["change"]
            # determine target of the stat change (self or opponent)
            if move.target in ("user", "user-and-allies"):
                target_pokemon = attacker
            else:
                target_pokemon = defender
            if stat in target_pokemon.stat_stages:
                target_pokemon.stat_stages[stat] = max(-6, min(6, target_pokemon.stat_stages[stat] + delta))


    def _apply_end_of_turn(self, pokemon):
        """Apply end-of-turn damage from weather, burn, and poison."""
        if pokemon.hpcurr <= 0:
            return

        if pokemon.status == "burned":
            if pokemon.ability.name != "magic-guard":
                pokemon.hpcurr = max(0, pokemon.hpcurr - max(1, pokemon.hpmax // 8))
        elif pokemon.status == "poisoned":
            if pokemon.ability.name != "magic-guard":
                pokemon.hpcurr = max(0, pokemon.hpcurr - max(1, pokemon.hpmax // 8))
        elif pokemon.status == "badly_poisoned":
            # TODO: track badly poisoned turn counter for increasing damage
            if pokemon.ability.name != "magic-guard":
                pokemon.hpcurr = max(0, pokemon.hpcurr - max(1, pokemon.hpmax // 8))

        if self.weather == "sandstorm":
            if pokemon.type1 not in ("rock", "ground", "steel") and \
               pokemon.type2 not in ("rock", "ground", "steel") and \
               pokemon.ability.name not in ("sand-veil", "sand-rush", "magic-guard", "overcoat"):
                pokemon.hpcurr = max(0, pokemon.hpcurr - max(1, pokemon.hpmax // 16))
        elif self.weather == "hail":
            if pokemon.type1 != "ice" and pokemon.type2 != "ice" and \
               pokemon.ability.name not in ("ice-body", "snow-cloak", "magic-guard", "overcoat"):
                pokemon.hpcurr = max(0, pokemon.hpcurr - max(1, pokemon.hpmax // 16))

        # speed boost
        if pokemon.ability.name == "speed-boost":
            pokemon.stat_stages["speed"] = min(6, pokemon.stat_stages["speed"] + 1)
