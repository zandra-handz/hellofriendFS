import json
from django.core.cache import cache

KEY_FMT = "gecko_sesh:{user_id}"
TTL_SECONDS = 60 * 15


def key(user_id):
    return KEY_FMT.format(user_id=user_id)


def write(user_id, payload):
    cache.set(key(user_id), json.dumps(payload), TTL_SECONDS)


def invalidate(*user_ids):
    cache.delete_many([key(uid) for uid in user_ids if uid is not None])


def read(user_id):
    raw = cache.get(key(user_id))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None
