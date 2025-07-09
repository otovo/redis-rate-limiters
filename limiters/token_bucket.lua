--- Lua scripts are run atomically by default, and since redis
--- is single threaded, there are no race conditions to worry about.
---
--- This script does three things, in order:
--- 1. Retrieves token bucket state, which means the last slot assigned,
---    and how many tokens are left to be assigned for that slot
--- 2. Works out whether we need to move to the next slot, or consume tokens
---    from the current one.
--- 3. Saves the token bucket state and returns the slot (or -1 if timeout exceeded).
---
--- The token bucket implementation is forward looking, so we're really just handing
--- out the next time there would be tokens in the bucket, and letting the client
---
--- returns:
--- * The assigned slot, as a millisecond timestamp, or -1 if request cannot be fulfilled
redis.replicate_commands()

-- Arguments
local capacity = tonumber(ARGV[1])
local refill_amount = tonumber(ARGV[2])
local time_between_slots = tonumber(ARGV[3]) * 1000 -- Convert to milliseconds
local seconds = tonumber(ARGV[4])
local microseconds = tonumber(ARGV[5])
local tokens_requested = tonumber(ARGV[6])
local max_timeout = ARGV[7] and tonumber(ARGV[7]) or nil -- Optional parameter

-- Keys
local data_key = KEYS[1]

-- Get current time in milliseconds
local now = (tonumber(seconds) * 1000) + (tonumber(microseconds) / 1000)

-- Check if request is impossible (more tokens than capacity)
if tokens_requested > capacity then
    return -1
end

-- Default bucket values (used if no bucket exists yet)
local tokens = capacity
local slot = now

-- Retrieve stored state, if any
local data = redis.call('GET', data_key)
if data then
    local last_slot, stored_tokens = data:match('(%S+) (%S+)')
    slot = tonumber(last_slot)
    tokens = tonumber(stored_tokens)

    -- Calculate the number of slots that have passed since the last update
    local slots_passed = math.floor((now - slot) / time_between_slots)
    if slots_passed > 0 then
        -- Refill the tokens based on the number of slots passed, capped by capacity
        tokens = math.min(tokens + slots_passed * refill_amount, capacity)
        -- Update the slot to this run, adding a penalty for execution time
        slot = now + 20
    end
end

-- Calculate how many tokens we need to wait for
local tokens_needed = math.max(0, tokens_requested - tokens)

-- If we need to wait for tokens, calculate the wait time
local wait_time = 0
if tokens_needed > 0 then
    -- Calculate how many additional slots we need to wait for
    local slots_needed = math.ceil(tokens_needed / refill_amount)
    wait_time = slot + (slots_needed * time_between_slots) - now
end

-- Check if max_timeout is specified and if wait time exceeds it
if max_timeout and wait_time > max_timeout then
    return -1
end

-- If no tokens are available for the current slot, move to the appropriate future slot
if tokens < tokens_requested then
    local tokens_needed = tokens_requested - tokens
    local slots_needed = math.ceil(tokens_needed / refill_amount)
    slot = slot + (slots_needed * time_between_slots)
    tokens = tokens + (slots_needed * refill_amount)
end

-- Consume the requested tokens
tokens = tokens - tokens_requested

-- Save updated state and set expiry
redis.call('SETEX', data_key, 30, string.format('%d %d', slot, tokens))

-- Return the slot when the tokens will be available
return slot
