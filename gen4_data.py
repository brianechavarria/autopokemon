NATURE_ID_TO_NAME = {
    0:  "hardy",
    1:  "lonely",
    2:  "brave",
    3:  "adamant",
    4:  "naughty",
    5:  "bold",
    6:  "docile",
    7:  "relaxed",
    8:  "impish",
    9:  "lax",
    10: "timid",
    11: "hasty",
    12: "serious",
    13: "jolly",
    14: "naive",
    15: "modest",
    16: "mild",
    17: "quiet",
    18: "bashful",
    19: "rash",
    20: "calm",
    21: "gentle",
    22: "sassy",
    23: "careful",
    24: "quirky",
}

# Only non-neutral natures are listed; neutral natures have no effect
NATURE_MODIFIERS = {
    "lonely":  {"boost": "attack",    "reduce": "defense"},
    "brave":   {"boost": "attack",    "reduce": "speed"},
    "adamant": {"boost": "attack",    "reduce": "spattack"},
    "naughty": {"boost": "attack",    "reduce": "spdefense"},
    "bold":    {"boost": "defense",   "reduce": "attack"},
    "relaxed": {"boost": "defense",   "reduce": "speed"},
    "impish":  {"boost": "defense",   "reduce": "spattack"},
    "lax":     {"boost": "defense",   "reduce": "spdefense"},
    "timid":   {"boost": "speed",     "reduce": "attack"},
    "hasty":   {"boost": "speed",     "reduce": "defense"},
    "jolly":   {"boost": "speed",     "reduce": "spattack"},
    "naive":   {"boost": "speed",     "reduce": "spdefense"},
    "modest":  {"boost": "spattack",  "reduce": "attack"},
    "mild":    {"boost": "spattack",  "reduce": "defense"},
    "quiet":   {"boost": "spattack",  "reduce": "speed"},
    "rash":    {"boost": "spattack",  "reduce": "spdefense"},
    "calm":    {"boost": "spdefense", "reduce": "attack"},
    "gentle":  {"boost": "spdefense", "reduce": "defense"},
    "sassy":   {"boost": "spdefense", "reduce": "speed"},
    "careful": {"boost": "spdefense", "reduce": "spattack"},
}

# Status byte bitmask constants (from Gen 4 ROM encoding)
STATUS_NONE          = 0x00
STATUS_SLEEP_MASK    = 0x07  # bits 0-2: sleep turn counter (1-7)
STATUS_POISON        = 0x08  # bit 3
STATUS_BADLY_POISONED = 0x10  # bit 4
STATUS_BURN          = 0x20  # bit 5
STATUS_FREEZE        = 0x40  # bit 6
STATUS_PARALYSIS     = 0x80  # bit 7

def parse_status_byte(byte: int) -> str:
    """Convert raw Gen 4 status byte to a status string."""
    if byte == STATUS_NONE:
        return None
    if byte & STATUS_SLEEP_MASK:
        return "asleep"
    if byte & STATUS_PARALYSIS:
        return "paralyzed"
    if byte & STATUS_FREEZE:
        return "frozen"
    if byte & STATUS_BURN:
        return "burned"
    if byte & STATUS_BADLY_POISONED:
        return "badly_poisoned"
    if byte & STATUS_POISON:
        return "poisoned"
    return None

# Moves with an inherently elevated critical hit ratio (+1 stage)
HIGH_CRIT_MOVES = frozenset({
    "slash", "razor-leaf", "crabhammer", "karate-chop", "razor-wind",
    "aeroblast", "cross-chop", "leaf-blade", "poison-tail", "night-slash",
    "psycho-cut", "shadow-claw", "spacial-rend", "stone-edge", "air-cutter",
    "blaze-kick", "attack-order",
})

# Item IDs for commonly held battle-relevant items in Platinum (US)
ITEM_IDS = {
    1:   "master-ball",
    220: "choice-band",
    236: "leftovers",
    239: "lum-berry",
    241: "sitrus-berry",
    247: "life-orb",
    248: "toxic-orb",
    249: "flame-orb",
    253: "choice-scarf",
    254: "choice-specs",
    265: "focus-sash",
    274: "expert-belt",
    275: "wise-glasses",
    276: "muscle-band",
    281: "scope-lens",
    # razor-claw is also a hold item but shares item ID with the evolution item
    # in Platinum; both trigger the crit boost
    303: "razor-claw",
    # metronome the held item (distinct from the move)
    # In Platinum, held metronome is item ID 175
    175: "metronome",
}
