from database import *
from gen4_data import NATURE_MODIFIERS

#Pokemon class, move class

class Pokemon:
    def __init__(self, species, moves, item, nature, ability, level, hp, stats, evs, ivs, friendship, exp):
        #lowkey kind of gross but there's a lot of paramaters that we have to keep in mind
        pokemon_data = read_pokemon(species)

        self.species = pokemon_data["name"]
        self.moves = self.move_builder(moves)
        self.item = item
        self.nature = nature
        self.level = level
        self.hpcurr = hp[0]
        self.hpmax = hp[1]
        self.attack = stats[0]
        self.defense = stats[1]
        self.speed = stats[2]
        self.spattack = stats[3]
        self.spdefense = stats[4]
        self.ev_hp  = evs[0]
        self.ev_atk = evs[1]
        self.ev_def = evs[2]
        self.ev_spe = evs[3]
        self.ev_spa = evs[4]
        self.ev_spd = evs[5]
        self.iv_hp  = ivs[0]
        self.iv_atk = ivs[1]
        self.iv_def = ivs[2]
        self.iv_spe = ivs[3]
        self.iv_spa = ivs[4]
        self.iv_spd = ivs[5]
        self.friendship = friendship
        self.exp = exp
        self.status = None
        self.flash_fire = False
        self.focus_energy = False
        self.trick_room = False  # True when Trick Room is active on the field
        self.stat_stages = {
            "attack": 0, "defense": 0, "speed": 0,
            "spattack": 0, "spdefense": 0,
            "accuracy": 0, "evasion": 0,
        }
        self.effect = None  # field effects targeting this Pokemon (e.g. "lucky chant")
        self.ability = self.ability_builder(pokemon_data, ability)
        self.type1 = pokemon_data["types"][0]["type"]["name"]
        if len(pokemon_data["types"]) > 1:
            self.type2 = pokemon_data["types"][1]["type"]["name"]
        else:
            self.type2 = ""
        self._apply_nature()
        


    def _apply_nature(self):
        mod = NATURE_MODIFIERS.get(self.nature, {})
        if "boost" in mod:
            setattr(self, mod["boost"], int(getattr(self, mod["boost"]) * 1.1))
            setattr(self, mod["reduce"], int(getattr(self, mod["reduce"]) * 0.9))

    @staticmethod
    def get_stage_modifier(stage: int) -> float:
        """Return the Gen 4 stat multiplier for a given stage (-6 to +6)."""
        stage = max(-6, min(6, stage))
        if stage >= 0:
            return (2 + stage) / 2
        else:
            return 2 / (2 - stage)

    #TODO
    def how_close_to_evolve(self):

        if self.exp == 1:
            return 1
    
    @staticmethod
    def move_builder(moves):
        #of course iterating through every object in an array isn't efficient but this is max n=4 so not bad
        move_objects = []
        for move in moves:
            m = read_move(move)
            move_name = m["name"]
            move_power = m["power"]
            move_accuracy = m["accuracy"]
            move_effect_chance = m["effect_chance"]
            move_pp = m["pp"]
            move_priority = m["priority"]
            move_damage_class = m["damage_class"]["name"]
            move_type = m["type"]["name"]
            move_stat_changes = m["stat_changes"]
            move_target = m["target"]["name"]
            move_objects.append(Move(move_name, move_power, move_accuracy, move_effect_chance, move_pp, move_priority, move_damage_class, move_type, move_stat_changes, move_target))

        return move_objects
    
    @staticmethod
    #input the name of the ability from reading the pokemon information #TODO reimplement
    def ability_builder(data, slot):
        for a in data["abilities"]:
            if a["slot"] == slot+1:
                pokemon_ability = Ability(a["ability"]["name"])
        return pokemon_ability
    
    #helper function to use in game class, will either be True or False based on conditions
    def set_flash_fire(self, value):
        self.flash_fire = value


        


class Move:

    def __init__(self, name, power, accuracy, effect_chance, pp, priority, damage_class, move_type, stat_changes, target):
        self.name = name
        self.power = power
        self.accuracy = accuracy
        self.effect_chance = effect_chance
        self.pp = pp
        self.priority = priority
        self.damage_class = damage_class
        self.move_type = move_type
        self.stat_changes = stat_changes
        self.target = target
        self.multitarget = 0 #TODO implement how to get get this value and use it
        self.cooldown = False #TODO implement this functionality


class Ability:

    def __init__(self, name):
        ability_data = read_ability(name)
        self.name = name
        self.effect = ability_data["effect_entries"][0]["short_effect"]

