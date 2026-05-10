"""
Redis cache for the 24h step/sustenance seed served on gecko WS connect.

Written through by users.gecko_helpers.update_hourly_steps so steady-state
hits never touch Postgres. Read by both Django (load_24h_seed fallback) and
Rust (gecko-socket-rust reads gecko_24h:{user_id} directly before HTTP).
"""

import json
import os
import redis

KEY_FMT = "gecko_24h:{user_id}"
TTL_SECONDS = 60 * 60 * 26  # 26h — covers the 24h rolling window plus slack

_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=6379,
    db=1,
    decode_responses=True,
)


def key(user_id):
    return KEY_FMT.format(user_id=user_id)


def write(user_id, steps_last_24h, sustenance_last_24h):
    _client.setex(
        key(user_id),
        TTL_SECONDS,
        json.dumps({
            "steps_last_24h": steps_last_24h,
            "sustenance_last_24h": sustenance_last_24h,
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
