import time
from dataclasses import dataclass

import redis
from config import settings


WINDOW_SECONDS = 60
MAX_ATTEMPTS = 5


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int


redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
INCR_EXPIRE_SCRIPT = redis_client.register_script(
    """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[1])
end
local ttl = redis.call("TTL", KEYS[1])
return {current, ttl}
"""
)

TOKEN_BUCKET_SCRIPT = redis_client.register_script(
    """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local refill_rate = tonumber(ARGV[3])
local consume = tonumber(ARGV[4])
local ttl_seconds = tonumber(ARGV[5])

local data = redis.call("HMGET", key, "tokens", "last_refill")
local tokens = tonumber(data[1])
local last_refill = tonumber(data[2])

if tokens == nil then
  tokens = capacity
  last_refill = now
end

local elapsed = math.max(0, now - last_refill)
tokens = math.min(capacity, tokens + (elapsed * refill_rate))

local allowed = 0
if tokens >= consume then
  tokens = tokens - consume
  allowed = 1
end

redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
redis.call("EXPIRE", key, ttl_seconds)

local retry_after = 0
if allowed == 0 then
  retry_after = math.ceil((consume - tokens) / refill_rate)
end

return {allowed, tokens, retry_after}
"""
)


def _window_id(now_ts: float) -> int:
    return int(now_ts // WINDOW_SECONDS)


def _key(scope: str, identifier: str, window: int) -> str:
    safe_id = identifier.strip().lower()
    return f"rl:{scope}:{safe_id}:{window}"


def check_and_consume(scope: str, identifier: str) -> RateLimitResult:
    now_ts = time.time()
    current_window = _window_id(now_ts)
    prev_window = current_window - 1

    elapsed = now_ts % WINDOW_SECONDS
    prev_weight = (WINDOW_SECONDS - elapsed) / \
        WINDOW_SECONDS  # 1 -> 0 across window

    key_curr = _key(scope, identifier, current_window)
    key_prev = _key(scope, identifier, prev_window)

    prev_raw = redis_client.get(key_prev)
    curr_count, curr_ttl = INCR_EXPIRE_SCRIPT(
        keys=[key_curr],
        args=[WINDOW_SECONDS + 1],
    )
    curr_count = int(curr_count)
    curr_ttl = int(curr_ttl)

    prev_count = int(prev_raw or 0)

    effective = (prev_count * prev_weight) + curr_count
    allowed = effective <= MAX_ATTEMPTS

    remaining = max(0, int(MAX_ATTEMPTS - effective))
    reset_seconds = max(
        1, int(curr_ttl if curr_ttl and curr_ttl > 0 else WINDOW_SECONDS - elapsed))

    return RateLimitResult(
        allowed=allowed,
        limit=MAX_ATTEMPTS,
        remaining=remaining,
        reset_seconds=reset_seconds,
    )


def consume_token_bucket(
    scope: str,
    identifier: str,
    capacity: int,
    refill_rate_per_second: float,
    consume_tokens: int = 1,
) -> RateLimitResult:
    # Single Redis hash key; no window suffix for token bucket.
    safe_id = identifier.strip().lower()
    key = f"tb:{scope}:{safe_id}"
    now_ts = int(time.time())
    ttl_seconds = max(1, int((capacity / refill_rate_per_second) * 2))

    allowed_raw, tokens_raw, retry_after_raw = TOKEN_BUCKET_SCRIPT(
        keys=[key],
        args=[now_ts, capacity, refill_rate_per_second, consume_tokens, ttl_seconds],
    )
    allowed = int(allowed_raw) == 1
    tokens_left = int(float(tokens_raw))
    retry_after = int(retry_after_raw)

    return RateLimitResult(
        allowed=allowed,
        limit=capacity,
        remaining=max(0, tokens_left),
        reset_seconds=max(1, retry_after if retry_after > 0 else 1),
    )
