"""
Redis cache for the gecko score-state multiplier.

Written through by the streak-activation path in
users.gecko_score_helpers (persists GeckoScoreState, then writes this key
in the same step). Read by the per-point scoring path so steady-state
point scoring never reads GeckoScoreState from Postgres. GeckoScoreState
remains the durable backstop on a cold cache.
"""

import json
import os
import redis

KEY_FMT = "gecko_score:{user_id}"
# A streak multiplier is only live until its expires_at (bounded by
# GeckoScoreState.max_streak_length_seconds). After that the read side
# resolves to the base multiplier anyway, so the row only needs to
# outlive the longest possible active streak plus slack.
TTL_SECONDS = 60 * 60  # 1h — comfortably outlives any active streak window

_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=6379,
    db=1,
    decode_responses=True,
)


def key(user_id):
    return KEY_FMT.format(user_id=user_id)


def write(user_id, new_multiplier, base_multiplier, expires_at):
    # base_multiplier is cached too so the scorer can resolve the effective
    # multiplier (active streak -> multiplier, otherwise -> base_multiplier)
    # entirely from the cache, including the common no-active-streak case.
    _client.setex(
        key(user_id),
        TTL_SECONDS,
        json.dumps({
            "multiplier": new_multiplier,
            "base_multiplier": base_multiplier,
            "expires_at": int(expires_at.timestamp()) if expires_at else None,
        }),
    )


def read(user_id):
    raw = _client.get(key(user_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def invalidate(user_id):
    _client.delete(key(user_id))
