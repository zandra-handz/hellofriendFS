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


def apply_level_change(user, new_level: Any) -> Dict[str, Any]:
    """
    Persist a host/guest gecko game-level change to BOTH participants' live-sesh
    rows and drop their hydrate caches. Returns a status dict; the caller turns
    a non-"ok" status into a request_level_change_failed ack.
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
        .only("other_user_id")
        .first()
    )
    if not sesh:
        return {"status": "no_active_sesh"}

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

        # Invalidate only after commit so a concurrent reconnect can never
        # repopulate Redis from a pre-commit read.
        transaction.on_commit(lambda: sesh_cache.invalidate(user.id, other_id))

    return {"status": "ok", "gecko_game_level": new_level, "partner_id": other_id}
