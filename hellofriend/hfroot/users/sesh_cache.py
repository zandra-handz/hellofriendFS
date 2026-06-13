import json
import os
import redis

KEY_FMT = "gecko_sesh:{user_id}"
TTL_SECONDS = 60 * 15

_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "127.0.0.1"),
    port=6379,
    db=1,
    decode_responses=True,
)


def key(user_id):
    return KEY_FMT.format(user_id=user_id)


def write(user_id, payload):
    _client.setex(key(user_id), TTL_SECONDS, json.dumps(payload))


def invalidate(*user_ids):
    keys = [key(uid) for uid in user_ids if uid is not None]
    if keys:
        _client.delete(*keys)


def patch(user_id, **fields):
    """
    Update specific fields in a user's cached live-sesh blob in place, so a warm
    socket hydrate reads the new value with no DB hit. No-op if the blob is
    absent — connect-time hydrate then falls back to Django/DB, which is already
    fresh. Never writes a partial blob (that would break the Rust hydrate, which
    expects the full field set).
    """
    raw = _client.get(key(user_id))
    if raw is None:
        return
    try:
        blob = json.loads(raw)
    except (TypeError, ValueError):
        return
    blob.update(fields)
    _client.setex(key(user_id), TTL_SECONDS, json.dumps(blob))


def read(user_id):
    raw = _client.get(key(user_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None
