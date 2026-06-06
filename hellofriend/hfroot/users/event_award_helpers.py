"""
Discrete-event point awards (hellos, future game wins, etc.) — NOT gecko
activity. Bypasses process_gecko_data on purpose: no live-sesh scoreboard
accrual, no streak multiplier, no hourly-steps bump, no GeckoData per-friend
totals. Just ledger + UserLifetimeTotals + socket push.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from geckoscripts.models import ScoreRule
from .models import GeckoPointsLedger, UserLifetimeTotals
from .rust_push import notify_user

logger = logging.getLogger(__name__)


# ScoreRule.code values for discrete-event awards. Must match a row created
# via `python manage.py create_score_rule --code N --label ... --points ...`.
HELLO_CREATED_CODE = 3
GECKO_GAME_WIN_CODE = 4  # ScoreRule label "AWARD_GECKO_GAME_WIN"


def award_event_points(
    user,
    code: int,
    past_meet=None,
    friend_id: Optional[int] = None,
    event_type: str = "hello_points",
) -> Optional[GeckoPointsLedger]:
    """
    Award the points associated with `code` to `user`. multiplier is always 1
    for events (streak does not apply). On commit, pushes an `event_type`
    socket event (default "hello_points") to the user's own socket(s) so the FE
    can update without refetch.

    Returns the created ledger row, or None if `code` is unknown.
    """
    rule = ScoreRule.objects.filter(code=code, version=1).first()
    if rule is None:
        logger.warning("[award_event_points] unknown code=%s user=%s", code, user.id)
        return None

    now = timezone.now()
    points = rule.points  # multiplier=1 — events don't streak

    with transaction.atomic():
        ledger_row = GeckoPointsLedger.objects.create(
            user=user,
            friend_id=friend_id,
            past_meet=past_meet,
            amount=points,
            reason=rule.label,
            code=rule.code,
            multiplier=1,
            timestamp_earned=now,
        )

        # Bump lifetime total in the same transaction so a partial failure
        # rolls back both. F() keeps it race-safe.
        UserLifetimeTotals.objects.filter(user=user).update(
            total_gecko_points=F("total_gecko_points") + points,
        )

        # Per-friend lifetime total. Same denormalization pattern as
        # UserLifetimeTotals — keeps "lifetime points with this friend"
        # a single indexed read instead of a SUM over the ledger.
        if friend_id is not None:
            from friends.models import GeckoData
            GeckoData.objects.filter(
                user=user, friend_id=friend_id,
            ).update(total_points=F("total_points") + points)

        payload: Dict[str, Any] = {
            "status": "ok",
            "awarded_user_id": user.id,
            "code": rule.code,
            "label": rule.label,
            "points": points,
            "multiplier": 1,
            "past_meet_id": past_meet.id if past_meet is not None else None,
            "friend_id": friend_id,
            "timestamp_earned": now.isoformat(),
        }

        # Fire AFTER commit — never push a notification for a row that
        # rolls back. notify_user is fire-and-forget; if no socket is open,
        # the message goes nowhere and that's fine.
        transaction.on_commit(
            lambda: _safe_notify(user.id, event_type, payload)
        )

    return ledger_row


def _safe_notify(user_id: int, event_type: str, payload: Dict[str, Any]) -> None:
    try:
        notify_user(user_id, event_type, payload)
    except Exception:
        logger.exception(
            "[award_event_points] notify_user failed user=%s event=%s",
            user_id, event_type,
        )
