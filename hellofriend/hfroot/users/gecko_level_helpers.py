"""
Persistence for the `request_level_change` socket action.

The Rust gecko socket owns the live side of a level change: it broadcasts the
new level to both peers' FE (`level_update`) the instant it arrives, with no
Django round-trip. This module only makes that change durable — both
participants' UserFriendCurrentLiveSesh rows carry `gecko_game_level`, so both
are updated, and the Rust hydrate caches are invalidated so a reconnect reads
the new value. No socket push happens here (that would duplicate the live
broadcast).

Called from views.gecko_socket_action.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from . import models, sesh_cache


logger = logging.getLogger(__name__)


def apply_level_change(user, new_level: Any, require_host: bool = False) -> Dict[str, Any]:
    """
    Persist a host/guest gecko game-level change to BOTH participants' live-sesh
    rows and drop their hydrate caches. Returns a status dict; the caller turns
    a non-"ok" status into a request_level_change_failed ack.

    When `require_host` is True (HTTP endpoint, called before entering the game
    screen), the change is rejected with a "not_host" status unless the caller's
    row is the host side. The socket path leaves this False so either
    participant may drive the live change.
    """
    valid_levels = set(dict(models.GeckoGameLevel.choices).keys())
    try:
        new_level = int(new_level)
    except (TypeError, ValueError):
        return {"status": "invalid_level"}
    if new_level not in valid_levels:
        return {"status": "invalid_level"}

    now = timezone.now()
    sesh = (
        models.UserFriendCurrentLiveSesh.objects
        .filter(user_id=user.id, expires_at__gt=now)
        .only("other_user_id", "is_host")
        .first()
    )
    if not sesh:
        return {"status": "no_active_sesh"}

    if require_host and not sesh.is_host:
        return {"status": "not_host"}

    other_id = sesh.other_user_id

    with transaction.atomic():
        # Bulk .update() deliberately bypasses the model's custom save() (log
        # trim / auto-create) — a level change must not churn session logs — and
        # touches both paired rows in one statement. updated_on is set
        # explicitly since auto_now only fires on .save().
        models.UserFriendCurrentLiveSesh.objects.filter(
            Q(user_id=user.id, other_user_id=other_id)
            | Q(user_id=other_id, other_user_id=user.id)
        ).update(gecko_game_level=new_level, updated_on=now)

        # Patch the new level straight into BOTH participants' cached blobs
        # after commit, so a socket hydrate reads it warm with no DB round-trip
        # (both sides share gecko_game_level). on_commit ordering means the
        # cache is only touched once the row write is durable, so a concurrent
        # reconnect can never read a pre-commit value. Patch is a no-op on a
        # cold blob — connect-time hydrate then falls back to the (fresh) DB.
        def _sync_cache():
            sesh_cache.patch(user.id, gecko_game_level=new_level)
            sesh_cache.patch(other_id, gecko_game_level=new_level)

        transaction.on_commit(_sync_cache)

    return {"status": "ok", "gecko_game_level": new_level, "partner_id": other_id}
