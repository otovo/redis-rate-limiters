--- Lua scripts are run atomically by default, and since redis
--- is single threaded, there are no race conditions to worry about.
---
--- This script does three things, in order:
--- 1. Retrieves token bucket state, which means the last slot assigned,
---    and how many tokens are left to be assigned for that slot
--- 2. Works out whether we need to move to the next slot, or consume another
---    token from the current one.
--- 3. Saves the token bucket state and returns the slot.
---
--- The token bucket implementation is forward looking, so we're really just handing
--- out the next time there would be tokens in the bucket, and letting the client
---
--- returns:
--- * The assigned slot, as a millisecond timestamp

redis.replicate_commands()

-- Arguments
local capacity = tonumber(ARGV[1])
local refill_amount = tonumber(ARGV[2])
local time_between_slots = tonumber(ARGV[3]) * 1000 -- ms

-- Keys
local data_key = KEYS[1]

-- Get current time (ms timestamp)
local redis_time = redis.call('TIME') -- Array of [seconds, microseconds]
local now = tonumber(redis_time[1]) * 1000 + (tonumber(redis_time[2]) / 1000)

-- Instantiate default bucket values
-- These are only used if a bucket doesn't already exist
local tokens = capacity

local slot = now + time_between_slots  -- next available slot == now + time_between_slots seconds

-- Retrieve (possibly) stored state
local data = redis.call('GET', data_key)

if data ~= false then
    for a, b in string.gmatch(data, '(%S+) (%S+)') do
        slot = tonumber(a)
        tokens = tonumber(b)
    end

    -- Add tokens if we have gone past the last scheduled slot
    if slot < now + 20 then  -- +20 to account for execution time
        local slots_passed = math.floor((now - slot) / time_between_slots)
        tokens = tokens + slots_passed * refill_amount
        slot = now + time_between_slots

        -- Make sure token count never exceeds capacity
        if tokens > capacity then
            tokens = capacity
        end
    end

    -- If the current slot has no more tokens to assign, move to the next slot.
    if tokens <= 0 then
        slot = slot + time_between_slots
        tokens = refill_amount
    end
end

-- Consume a token
tokens = tokens - 1

-- Save state and set expiry
redis.call('SETEX', data_key, 30, string.format('%d %d', slot, tokens))

return slot
