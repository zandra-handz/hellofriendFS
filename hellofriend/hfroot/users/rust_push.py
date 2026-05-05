"""
Helpers for talking to the Rust gecko socket server.

Two transport paths exist for socket-bound traffic:

  * Django Channels consumer (consumers.py) — reached via channel_layer.group_send
    on group `gecko_energy_{uid}` / `gecko_shared_with_friend_{uid}`.
  * Rust socket (gecko-socket-rust) — reached via HTTP POST to /internal/push/*
    with X-Rust-Internal-Secret.

A given user is connected to ONE of those at a time, but Django doesn't know
which. The notify_* helpers in this module fan out to both so the right
delivery happens regardless of which socket the user is on. The cost of the
duplicate call when the user is on the other transport is a single
read-and-discard at the receiving end.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Mapping, Optional

import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings


logger = logging.getLogger(__name__)


def _rust_base_url() -> str:
    return getattr(settings, "RUST_SOCKET_BASE_URL", "http://127.0.0.1:4000")


def _rust_secret() -> str:
    return getattr(settings, "RUST_INTERNAL_SECRET", "") or ""


def _post_to_rust(path: str, body: Mapping[str, Any]) -> Optional[dict]:
    url = f"{_rust_base_url()}{path}"
    try:
        resp = requests.post(
            url,
            json=body,
            headers={"X-Rust-Internal-Secret": _rust_secret()},
            timeout=2.0,
        )
    except requests.RequestException as exc:
        logger.debug("rust push %s unreachable: %s", path, exc)
        return None
    if resp.status_code >= 400:
        logger.debug("rust push %s -> %s %s", path, resp.status_code, resp.text[:200])
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def push_to_rust_user(
    user_id: int,
    action: str,
    data: Mapping[str, Any],
    *,
    close_after: bool = False,
) -> None:
    """Deliver `{action, data}` to all rust-side sockets for `user_id`."""
    _post_to_rust(
        "/internal/push/user",
        {
            "user_id": int(user_id),
            "action": action,
            "data": dict(data),
            "close_after": bool(close_after),
        },
    )


def push_to_rust_room(
    room: str,
    action: str,
    data: Mapping[str, Any],
    *,
    exclude_user_id: Optional[int] = None,
) -> None:
    _post_to_rust(
        "/internal/push/room",
        {
            "room": room,
            "action": action,
            "data": dict(data),
            "exclude_user_id": int(exclude_user_id) if exclude_user_id is not None else None,
        },
    )


def disconnect_rust_user(user_id: int) -> None:
    _post_to_rust("/internal/disconnect-user", {"user_id": int(user_id)})


# ---------------------------------------------------------------------------
# Dual-broadcast helpers — call instead of channel_layer.group_send directly.
# ---------------------------------------------------------------------------

def notify_user(user_id: int, event_type: str, data: Mapping[str, Any]) -> None:
    """
    Push a server-initiated event to a single user across both transports.

    `event_type` is the action string the FE will see (also the consumer
    method name, e.g. 'gecko_win_proposed', 'live_sesh_cancelled').
    `data` is the FE-bound payload — same dict the consumer's handler would
    nest under 'data' before json.dumps.
    """
    # Django Channels path (consumer.py users).
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        try:
            async_to_sync(channel_layer.group_send)(
                f"gecko_energy_{user_id}",
                {"type": event_type, **dict(data)},
            )
        except Exception:
            logger.exception("channel_layer.group_send failed user=%s event=%s", user_id, event_type)

    # Rust socket path.
    push_to_rust_user(user_id, event_type, data)


def notify_users(user_ids: Iterable[int], event_type: str, data: Mapping[str, Any]) -> None:
    for uid in user_ids:
        notify_user(uid, event_type, data)


def refresh_sesh_context(user_id: int, partner_id: Optional[int]) -> None:
    """
    Tell `user_id`'s socket(s) that their live-sesh context changed.
    Channels consumer reacts via `sesh_context_refresh`; Rust socket re-pulls
    via the rust_live_sesh_context endpoint on next join_live_sesh, so on the
    Rust side we just re-push the join state by sending a `sesh_context_refresh`
    action — clients can ignore it if they don't care.
    """
    notify_user(user_id, "sesh_context_refresh", {"partner_id": partner_id})


def cancel_live_sesh(user_id: int, payload: Mapping[str, Any]) -> None:
    """Send live_sesh_cancelled to a user and close their Rust socket."""
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        try:
            async_to_sync(channel_layer.group_send)(
                f"gecko_energy_{user_id}",
                {"type": "live_sesh_cancelled", "data": dict(payload)},
            )
        except Exception:
            logger.exception("channel_layer cancel send failed user=%s", user_id)

    # Rust: deliver the action then close the socket.
    push_to_rust_user(user_id, "live_sesh_cancelled", payload, close_after=True)
