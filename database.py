import json
import os
import requests
import time


baseURL = "https://pokeapi.co/api/v2"

# pokemon = "Infernape"
# r = requests.get(f"{baseURL}/pokemon/{pokemon}")
# d = r.json()
# print(d["name"])


def read_db(filename):
    with open(filename, "r") as f:
        if os.path.getsize(filename) != 0:
            return json.load(f)
    
    return {}


def save_db(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)



def read_pokemon(id):
    db = read_db("pokemondatabase.json")
    if id not in db:
        r = requests.get(f"https://pokeapi.co/api/v2/pokemon/{id}")
        db[id] = r.json()
        save_db("pokemondatabase.json", db)

    return db[id]


def read_move(id):
    db = read_db("movedatabase.json")
    if id not in db:
        r = requests.get(f"https://pokeapi.co/api/v2/move/{id}")
        db[id] = r.json()
        save_db("movedatabase.json", db)

    return db[id]


def read_ability(id):
    db = read_db("abilitydatabase.json")
    if id not in db:
        r = requests.get(f"https://pokeapi.co/api/v2/ability/{id}")
        db[id] = r.json()
        save_db("abilitydatabase.json", db)

    return db[id]

