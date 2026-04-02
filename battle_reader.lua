-- battle_reader.lua
-- Runs inside DeSmuME via Tools > Lua Scripting > New Lua Script Window.
-- Reads battle state from Platinum (US) RAM and streams JSON lines to the
-- Python RomDecoder server over a TCP socket on 127.0.0.1:6000.
--
-- CALIBRATION NOTE:
-- The battle struct base addresses below are approximate. Before relying on
-- them you must verify against a known save state:
--   1. Freeze a Pokemon with known HP (e.g., 100/100) in battle.
--   2. Open DeSmuME's RAM viewer (Tools > RAM Search).
--   3. Search for the value 100 (2 bytes) to locate the hp_curr field.
--   4. Adjust PLAYER_BASE and OPP_BASE below to match.
--
-- Pokemon Platinum (US) active battle Pokemon structs live in main RAM.
-- These offsets are relative to each Pokemon's battle struct base address.

local PLAYER_BASE = 0x02238F24  -- approximate; calibrate before use
local OPP_BASE    = 0x022393C4  -- approximate; calibrate before use

-- Offsets within the battle Pokemon struct (relative to base)
local OFF_SPECIES  = 0x00  -- 2 bytes: National Dex ID
local OFF_HP_CURR  = 0x02  -- 2 bytes
local OFF_HP_MAX   = 0x04  -- 2 bytes
local OFF_LEVEL    = 0x06  -- 1 byte
local OFF_STATUS   = 0x08  -- 1 byte (bitmask)
local OFF_MOVE1    = 0x10  -- 2 bytes (move ID)
local OFF_MOVE2    = 0x12  -- 2 bytes
local OFF_MOVE3    = 0x14  -- 2 bytes
local OFF_MOVE4    = 0x16  -- 2 bytes
local OFF_PP1      = 0x18  -- 1 byte
local OFF_PP2      = 0x19  -- 1 byte
local OFF_PP3      = 0x1A  -- 1 byte
local OFF_PP4      = 0x1B  -- 1 byte
local OFF_ATTACK   = 0x20  -- 2 bytes
local OFF_DEFENSE  = 0x22  -- 2 bytes
local OFF_SPEED    = 0x24  -- 2 bytes
local OFF_SPATTACK = 0x26  -- 2 bytes
local OFF_SPDEFENSE= 0x28  -- 2 bytes
local OFF_ABILITY  = 0x30  -- 1 byte (ability slot: 0 or 1)
local OFF_NATURE   = 0x31  -- 1 byte (0-24)
local OFF_ITEM     = 0x32  -- 2 bytes

-- Weather address (single byte in battle engine)
local WEATHER_ADDR = 0x02241218  -- approximate; calibrate before use

local HOST = "127.0.0.1"
local PORT = 6000

-- -------------------------------------------------------------------------
-- JSON serialization (minimal, no external library needed)
-- -------------------------------------------------------------------------
local function json_array(t)
    local s = "["
    for i, v in ipairs(t) do
        if i > 1 then s = s .. "," end
        s = s .. tostring(v)
    end
    return s .. "]"
end

local function json_slot(slot)
    return string.format(
        '{"species":%d,"hp_curr":%d,"hp_max":%d,"level":%d,' ..
        '"status":%d,"moves":%s,"pp":%s,' ..
        '"attack":%d,"defense":%d,"speed":%d,"spattack":%d,"spdefense":%d,' ..
        '"ability":%d,"nature":%d,"item":%d}',
        slot.species, slot.hp_curr, slot.hp_max, slot.level,
        slot.status,
        json_array(slot.moves), json_array(slot.pp),
        slot.attack, slot.defense, slot.speed, slot.spattack, slot.spdefense,
        slot.ability, slot.nature, slot.item
    )
end

-- -------------------------------------------------------------------------
-- Memory reading helpers
-- -------------------------------------------------------------------------
local function read_slot(base)
    local slot = {}
    slot.species   = memory.read_u16_le(base + OFF_SPECIES)
    slot.hp_curr   = memory.read_u16_le(base + OFF_HP_CURR)
    slot.hp_max    = memory.read_u16_le(base + OFF_HP_MAX)
    slot.level     = memory.read_u8(base + OFF_LEVEL)
    slot.status    = memory.read_u8(base + OFF_STATUS)
    slot.moves     = {
        memory.read_u16_le(base + OFF_MOVE1),
        memory.read_u16_le(base + OFF_MOVE2),
        memory.read_u16_le(base + OFF_MOVE3),
        memory.read_u16_le(base + OFF_MOVE4),
    }
    slot.pp        = {
        memory.read_u8(base + OFF_PP1),
        memory.read_u8(base + OFF_PP2),
        memory.read_u8(base + OFF_PP3),
        memory.read_u8(base + OFF_PP4),
    }
    slot.attack    = memory.read_u16_le(base + OFF_ATTACK)
    slot.defense   = memory.read_u16_le(base + OFF_DEFENSE)
    slot.speed     = memory.read_u16_le(base + OFF_SPEED)
    slot.spattack  = memory.read_u16_le(base + OFF_SPATTACK)
    slot.spdefense = memory.read_u16_le(base + OFF_SPDEFENSE)
    slot.ability   = memory.read_u8(base + OFF_ABILITY)
    slot.nature    = memory.read_u8(base + OFF_NATURE)
    slot.item      = memory.read_u16_le(base + OFF_ITEM)
    return slot
end

local function slots_equal(a, b)
    if a == nil or b == nil then return false end
    return a.species   == b.species
       and a.hp_curr   == b.hp_curr
       and a.hp_max    == b.hp_max
       and a.level     == b.level
       and a.status    == b.status
       and a.attack    == b.attack
end

-- -------------------------------------------------------------------------
-- TCP connection management
-- -------------------------------------------------------------------------
local socket = require("socket")
local client = nil
local turn   = 0

local function connect()
    local sock, err = socket.connect(HOST, PORT)
    if sock then
        sock:settimeout(0)  -- non-blocking
        client = sock
        print("[battle_reader] Connected to Python server.")
    else
        print("[battle_reader] Connection failed: " .. tostring(err) .. ". Retrying next frame.")
        client = nil
    end
end

local function send_state(player_slot, opp_slot, weather)
    if client == nil then
        connect()
        if client == nil then return end
    end

    local msg = string.format(
        '{"player":%s,"opponent":%s,"weather":%d,"turn":%d}\n',
        json_slot(player_slot), json_slot(opp_slot), weather, turn
    )

    local ok, err = client:send(msg)
    if not ok then
        print("[battle_reader] Send failed: " .. tostring(err) .. ". Will reconnect.")
        client:close()
        client = nil
    end
end

-- -------------------------------------------------------------------------
-- Main loop — registered as a post-frame callback
-- -------------------------------------------------------------------------
local last_player = nil
local last_opp    = nil

emu.registerafter(function()
    -- Only read memory when in battle (species != 0 is a simple heuristic)
    local player_slot = read_slot(PLAYER_BASE)
    if player_slot.species == 0 then return end

    local opp_slot = read_slot(OPP_BASE)
    local weather  = memory.read_u8(WEATHER_ADDR)

    -- Only send when something changed to avoid flooding the socket
    if slots_equal(player_slot, last_player) and slots_equal(opp_slot, last_opp) then
        return
    end

    last_player = player_slot
    last_opp    = opp_slot
    turn        = turn + 1

    send_state(player_slot, opp_slot, weather)
end)

print("[battle_reader] Lua script loaded. Waiting for battle...")
