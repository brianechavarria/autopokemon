from pokemon import *

class Battle:

    def __init__(self, player_party, AI_party, double_battle=False):

        #each party should be a list of objects of the pokemon class
        self.player_party = player_party
        self.AI_party = AI_party
        self.weather = "clear"
        self.player_effect = 0 #implement this TODO
        self.AI_effect = 0 #implement this TODO
        self.double_battle = double_battle #implement double battle logic TODO

    
    def AImove(self):
         return 1
    

    #player_check is True if the player is attacking and False if the AI is
    def damage_calc(self, attacker, attack_move, defender, player_check, multi_target):
        #capture edge case for the move beat up
        if attack_move.name == "beat up":
            level = defender.level
        else:
            level = attacker.level

        #a and d depend on whether the attack is physical or special
        if attack_move.damage_class == "physical":
            a = attacker.attack
            d = defender.defense
        else:
            a = attacker.spattack
            d = defender.spdefense

        #determine burn modifier
        if (attacker.status == "burned") and (attacker.ability != "guts") and (attack_move.damage_class == "physical"):
            burn = .5
        else:
            burn = 1

        #check for screen effect
        if player_check:
            if ((attack_move.damage_class == "physical") and (self.AI_effect == "reflect")) or ((attack_move.damage_class == "special") and (self.AI_effect == "light screen")):
                if self.double_battle == True:
                    screen = 2/3
                else:
                    screen = 1/2
            else:
                screen = 1
        else:
            if ((attack_move.damage_class == "physical") and (self.player_effect == "reflect")) or ((attack_move.damage_class == "special") and (self.player_effect == "light screen")):
                if self.double_battle == True:
                    screen = 2/3
                else:
                    screen = .5
            else:
                screen = 1

        #adjust based on number of targets
        #TODO when we do the battle sim remember that damage will be done on multiple targets in certain cases
        if multi_target:
            targets = .75
        else:
            targets = 1

        #adjust for weather dependent moves
        if (attacker.ability == "cloud nine") or (attacker.ability == "air lock") or (defender.ability == "cloud nine") or (defender.ability == "air lock"):
            weather_effect = 1
        elif self.weather == "harsh sunlight":
            if attack_move.move_type == "fire":
                weather_effect = 1.5
            elif attack_move.move_type == "water":
                weather_effect = .5
        elif self.weather == "rain":
            if attack_move.move_type == "fire":
                weather_effect = .5
            elif attack_move.move_type == "water":
                weather_effect = 1.5
        elif (self.weather != "clear") and (attack_move.name == "solar beam"):
            weather_effect = .5
        else:
            weather_effect = 1
        
        #check for flash fire
        if (attack_move.move_type == "fire") and attacker.flash_fire:
            flash_fire_effect = 1.5
        else:
            flash_fire_effect = 1
        


        
        return ((((2*level)/5)*attack_move.power*(a/d)/50)*burn*screen*targets*weather_effect*flash_fire_effect+2)
    
        