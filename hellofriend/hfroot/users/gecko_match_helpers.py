"""
Stateless ports of the consumer's win/capsule-match handlers.

These functions:
  * read DB state (no per-connection cache like the consumer's
    self.capsule_matches or self.is_host),
  * return the {action, data} ack payload the caller should hand back to the
    requesting socket,
  * push any cross-user broadcasts (gecko_win_proposed, capsule_matches_ready,
    propose_gecko_match_win_ok, ...) via rust_push.notify_user, which fans
    out to both Channels and Rust transports.

Called from views.gecko_socket_action.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from django.utils import timezone

from . import models, rust_push


logger = logging.getLogger(__name__)


def _active_sesh(user_id: int):
    return (
        models.UserFriendCurrentLiveSesh.objects
        .filter(user_id=user_id, expires_at__gt=timezone.now())
        .only("other_user_id", "is_host", "friend_id")
        .first()
    )


def _compute_capsule_matches(guest_user_id: int, host_user_id: int) -> Dict[str, Any]:
    """Mirror of consumers._compute_capsule_matches_db."""
    from friends.models import Friend, ThoughtCapsulez

    guest_friend = (
        Friend.objects
        .filter(user_id=guest_user_id, linked_user_id=host_user_id)
        .only("id")
        .first()
    )
    if not guest_friend:
        return {"is_linked": False, "friend_id": None, "matches": []}

    host_friend = (
        Friend.objects
        .filter(user_id=host_user_id, linked_user_id=guest_user_id)
        .only("id")
        .first()
    )
    if not host_friend:
        return {"is_linked": False, "friend_id": guest_friend.id, "matches": []}

    guest_caps = ThoughtCapsulez.objects.filter(
        user_id=guest_user_id,
        friend_id=guest_friend.id,
        match_only=True,
    ).values("id", "gecko_game_type")

    host_caps = ThoughtCapsulez.objects.filter(
        user_id=host_user_id,
        friend_id=host_friend.id,
        match_only=True,
    ).values("id", "gecko_game_type")

    guest_by_type: Dict[Any, list] = {}
    for c in guest_caps:
        guest_by_type.setdefault(c["gecko_game_type"], []).append(str(c["id"]))

    host_by_type: Dict[Any, list] = {}
    for c in host_caps:
        host_by_type.setdefault(c["gecko_game_type"], []).append(str(c["id"]))

    matches = []
    for game_type, guest_ids in guest_by_type.items():
        host_ids = host_by_type.get(game_type)
        if not host_ids:
            continue
        matches.append({
            "gecko_game_type": game_type,
            "guest_capsule_ids": guest_ids,
            "host_capsule_ids": host_ids,
        })

    return {"is_linked": True, "friend_id": guest_friend.id, "matches": matches}


def _push_capsule_matches_ready(user_id: int, partner_id: int, sesh) -> None:
    """Compute matches between user_id and partner_id and push to both."""
    if sesh.is_host:
        host_user_id = user_id
        guest_user_id = partner_id
    else:
        host_user_id = partner_id
        guest_user_id = user_id

    result = _compute_capsule_matches(guest_user_id, host_user_id)

    payload = {
        "completed": True,
        "is_linked": result["is_linked"],
        "host_user_id": host_user_id,
        "guest_user_id": guest_user_id,
        "friend_id": result["friend_id"],
        "matches": result["matches"],
    }

    for uid in (user_id, partner_id):
        rust_push.notify_user(uid, "capsule_matches_ready", payload)


# ---------------------------------------------------------------------------
# Action handlers — each returns the ack payload (dict) for the caller and
# fires off any required peer broadcasts internally.
# ---------------------------------------------------------------------------

def handle_request_capsule_matches(user_id: int) -> Dict[str, Any]:
    sesh = _active_sesh(user_id)
    if not sesh:
        return {
            "action": "capsule_matches_ready",
            "data": {
                "completed": False,
                "is_linked": False,
                "host_user_id": None,
                "guest_user_id": None,
                "friend_id": None,
                "matches": [],
            },
        }
    _push_capsule_matches_ready(user_id, sesh.other_user_id, sesh)
    # The push above already delivered to the caller via notify_user; return
    # an empty ack so the proxy doesn't double-send.
    return {"action": "capsule_matches_request_acked", "data": {}}


def handle_repull_capsule_matches(user_id: int) -> Tuple[Dict[str, Any], int]:
    sesh = _active_sesh(user_id)
    if not sesh:
        return ({
            "action": "repull_capsule_matches_failed",
            "data": {"reason": "no_active_sesh"},
        }, 200)
    _push_capsule_matches_ready(user_id, sesh.other_user_id, sesh)
    return ({"action": "repull_capsule_matches_acked", "data": {}}, 200)


def handle_propose_gecko_win(user, capsule_id) -> Dict[str, Any]:
    from friends.models import ThoughtCapsulez, GeckoGameType
    from users.models import GeckoGameWinPending, BadRainbowzUser

    sesh = _active_sesh(user.id)
    if not sesh:
        return {"action": "propose_gecko_win_failed", "data": {"reason": "no_active_sesh"}}

    if not capsule_id:
        return {"action": "propose_gecko_win_failed", "data": {"reason": "missing_capsule_id"}}

    partner_id = sesh.other_user_id

    capsule = (
        ThoughtCapsulez.objects
        .filter(id=capsule_id, user_id=user.id)
        .first()
    )
    if capsule is None:
        return {
            "action": "propose_gecko_win_failed",
            "data": {"reason": "capsule_not_found_or_not_owner"},
        }

    target_user = BadRainbowzUser.objects.filter(id=partner_id).first()
    if target_user is None:
        return {"action": "propose_gecko_win_failed", "data": {"reason": "partner_not_found"}}

    if capsule.match_only:
        return {"action": "propose_gecko_win_failed", "data": {"reason": "capsule_is_match_only"}}

    gecko_game_type = capsule.gecko_game_type
    label = GeckoGameType(gecko_game_type).label

    GeckoGameWinPending.propose(
        target_user=target_user,
        sender=user,
        sender_capsule=capsule,
        gecko_game_type=gecko_game_type,
        gecko_game_type_label=label,
    )

    rust_push.notify_user(
        partner_id,
        "gecko_win_proposed",
        {
            "sender_user_id": user.id,
            "gecko_game_type": gecko_game_type,
            "pending_id": None,
            "my_capsule_id": None,
            "partner_capsule_id": str(capsule_id),
        },
    )

    return {
        "action": "propose_gecko_win_ok",
        "data": {
            "gecko_game_type": gecko_game_type,
            "gecko_game_type_label": label,
        },
    }


def handle_propose_gecko_match_win(user, requested_type) -> Dict[str, Any]:
    """
    Stateless port of the consumer's propose_gecko_match_win handler. Recomputes
    capsule matches on the fly (the consumer cached them in self.capsule_matches
    after _check_host_link_and_load).
    """
    from friends.models import ThoughtCapsulez, GeckoGameType
    from users.models import GeckoGameMatchWinPending, BadRainbowzUser

    try:
        requested_type = int(requested_type)
    except (TypeError, ValueError):
        return {
            "action": "propose_gecko_match_win_failed",
            "data": {"reason": "invalid_gecko_game_type"},
        }

    sesh = _active_sesh(user.id)
    if not sesh:
        return {
            "action": "propose_gecko_match_win_failed",
            "data": {"reason": "no_active_sesh"},
        }

    partner_id = sesh.other_user_id
    is_host = bool(sesh.is_host)

    if is_host:
        host_user_id = user.id
        guest_user_id = partner_id
    else:
        host_user_id = partner_id
        guest_user_id = user.id

    matches_result = _compute_capsule_matches(guest_user_id, host_user_id)
    match = next(
        (m for m in matches_result["matches"] if m.get("gecko_game_type") == requested_type),
        None,
    )

    if match is None:
        return {
            "action": "propose_gecko_match_win_failed",
            "data": {"reason": "no_match_for_type", "gecko_game_type": requested_type},
        }

    guest_ids = match.get("guest_capsule_ids") or []
    host_ids = match.get("host_capsule_ids") or []
    if not guest_ids or not host_ids:
        return {
            "action": "propose_gecko_match_win_failed",
            "data": {"reason": "no_match_for_type", "gecko_game_type": requested_type},
        }

    picked_guest = guest_ids[0]
    picked_host = host_ids[0]

    if is_host:
        my_capsule_id = picked_host
        partner_capsule_id = picked_guest
    else:
        my_capsule_id = picked_guest
        partner_capsule_id = picked_host

    my_capsule = (
        ThoughtCapsulez.objects
        .filter(id=my_capsule_id, user_id=user.id)
        .first()
    )
    if my_capsule is None:
        return {
            "action": "propose_gecko_match_win_failed",
            "data": {"reason": "my_capsule_not_found_or_not_owner"},
        }

    partner_capsule = (
        ThoughtCapsulez.objects
        .filter(id=partner_capsule_id, user_id=partner_id)
        .first()
    )
    if partner_capsule is None:
        return {
            "action": "propose_gecko_match_win_failed",
            "data": {"reason": "partner_capsule_not_found_or_not_owner"},
        }

    partner_user = BadRainbowzUser.objects.filter(id=partner_id).first()
    if partner_user is None:
        return {
            "action": "propose_gecko_match_win_failed",
            "data": {"reason": "partner_not_found"},
        }

    gecko_game_type = my_capsule.gecko_game_type
    label = GeckoGameType(gecko_game_type).label

    if is_host:
        host_user = user
        guest_user = partner_user
        host_capsule = my_capsule
        guest_capsule = partner_capsule
    else:
        host_user = partner_user
        guest_user = user
        host_capsule = partner_capsule
        guest_capsule = my_capsule

    pending = GeckoGameMatchWinPending.propose(
        initiator=user,
        host=host_user,
        guest=guest_user,
        host_capsule=host_capsule,
        guest_capsule=guest_capsule,
        gecko_game_type=gecko_game_type,
        gecko_game_type_label=label,
    )

    # Mirror consumer's four broadcasts.
    rust_push.notify_user(
        partner_id,
        "gecko_win_proposed",
        {
            "sender_user_id": user.id,
            "gecko_game_type": requested_type,
            "pending_id": pending.id,
            "my_capsule_id": str(partner_capsule_id),
            "partner_capsule_id": str(my_capsule_id),
        },
    )
    rust_push.notify_user(
        user.id,
        "gecko_win_proposed",
        {
            "sender_user_id": partner_id,
            "gecko_game_type": requested_type,
            "pending_id": pending.id,
            "my_capsule_id": str(my_capsule_id),
            "partner_capsule_id": str(partner_capsule_id),
        },
    )
    rust_push.notify_user(
        user.id,
        "propose_gecko_match_win_ok",
        {
            "pending_id": pending.id,
            "other_user_id": partner_id,
            "gecko_game_type": requested_type,
            "capsule_id": str(partner_capsule_id),
        },
    )
    rust_push.notify_user(
        partner_id,
        "propose_gecko_match_win_ok",
        {
            "pending_id": pending.id,
            "other_user_id": user.id,
            "gecko_game_type": requested_type,
            "capsule_id": str(my_capsule_id),
        },
    )

    # Direct ack already delivered via the user.id notify above; return empty.
    return {"action": "propose_gecko_match_win_acked", "data": {"pending_id": pending.id}}
