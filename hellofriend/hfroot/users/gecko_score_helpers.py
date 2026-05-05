"""
Stateless score-state load/serialize helpers shared by:
  * consumers.py (Django Channels, stateful per-connection),
  * views.gecko_socket_action (HTTP, stateless — used by the Rust socket).

These mirror consumers._load_initial_state / _serialize_score_state. The
consumer keeps a per-connection in-memory `score_state` dict so it can apply
many small `update_gecko_data` deltas before flushing to the DB once. The HTTP
path can't keep that buffer (each request is independent), so for HTTP callers
the source of truth is the GeckoScoreState row itself: read, mutate, save.

Don't change the dict shape without updating both call sites — the FE relies
on this exact field set being delivered as `score_state.data`.
"""

from __future__ import annotations

from typing import Any, Dict

from . import constants


def serialize_score_state(user, score_state: Dict[str, Any], total_steps_all_time: int) -> Dict[str, Any]:
    """Mirror of consumers._serialize_score_state, callable from sync code."""
    ss = score_state
    max_active_hours = ss.get("max_active_hours", 16)
    full_rest_hours = 24 - max_active_hours
    recharge_per_second = 1.0 / (full_rest_hours * 3600) if full_rest_hours > 0 else 0.0

    def _fmt_dt(val):
        if val is None:
            return None
        if isinstance(val, str):
            return val
        return val.isoformat()

    return {
        "user": user.id,
        "total_steps_all_time": total_steps_all_time,
        "multiplier": ss["multiplier"],
        "expires_at": _fmt_dt(ss["expires_at"]),
        "updated_on": _fmt_dt(ss.get("updated_on")),
        "base_multiplier": ss["base_multiplier"],
        "energy": ss["energy"],
        "surplus_energy": ss["surplus_energy"],
        "energy_updated_at": _fmt_dt(ss["energy_updated_at"]),
        "revives_at": _fmt_dt(ss["revives_at"]),
        "recharge_per_second": recharge_per_second,
        "streak_recharge_per_second": recharge_per_second * 0.5,
        "step_fatigue_per_step": constants.STEP_FATIGUE_PER_STEP,
        "streak_fatigue_multiplier": constants.STREAK_FATIGUE_MULTIPLIER,
        "surplus_cap": constants.SURPLUS_CAP,
        "personality_type": ss.get("personality_type"),
        "personality_type_label": ss.get("personality_type_label"),
        "memory_type": ss.get("memory_type"),
        "memory_type_label": ss.get("memory_type_label"),
        "active_hours_type": ss.get("active_hours_type"),
        "active_hours_type_label": ss.get("active_hours_type_label"),
        "story_type": ss.get("story_type"),
        "story_type_label": ss.get("story_type_label"),
        "stamina": ss.get("stamina", 1.0),
        "max_active_hours": max_active_hours,
        "max_duration_till_revival": ss.get("max_duration_till_revival", 60),
        "max_score_multiplier": ss.get("max_score_multiplier", 3),
        "max_streak_length_seconds": ss.get("max_streak_length_seconds", 10),
        "active_hours": ss.get("active_hours", []),
        "gecko_created_on": _fmt_dt(ss.get("gecko_created_on")),
    }


def _score_state_dict_from_obj(obj) -> Dict[str, Any]:
    return {
        "multiplier": obj.multiplier,
        "base_multiplier": obj.base_multiplier,
        "expires_at": obj.expires_at,
        "energy": obj.energy,
        "surplus_energy": obj.surplus_energy,
        "energy_updated_at": obj.energy_updated_at,
        "revives_at": obj.revives_at,
        "updated_on": obj.updated_on,
        "personality_type": obj.personality_type,
        "personality_type_label": obj.get_personality_type_display(),
        "memory_type": obj.memory_type,
        "memory_type_label": obj.get_memory_type_display(),
        "active_hours_type": obj.active_hours_type,
        "active_hours_type_label": obj.get_active_hours_type_display(),
        "story_type": obj.story_type,
        "story_type_label": obj.get_story_type_display(),
        "stamina": obj.stamina,
        "max_active_hours": obj.max_active_hours,
        "max_duration_till_revival": obj.max_duration_till_revival,
        "max_score_multiplier": obj.max_score_multiplier,
        "max_streak_length_seconds": obj.max_streak_length_seconds,
        "active_hours": obj.active_hours,
        "gecko_created_on": obj.gecko_created_on,
    }


def load_initial_score_payload(user) -> Dict[str, Any]:
    """
    Mirror of consumers._load_initial_state. Loads (or creates) the score
    state row, recomputes energy, and returns the dict the FE expects under
    score_state.data.
    """
    from .models import GeckoScoreState, GeckoCombinedData

    obj, _ = GeckoScoreState.objects.get_or_create(user=user)
    obj.recompute_energy()

    combined, _ = GeckoCombinedData.objects.get_or_create(user=user)
    total_steps_all_time = combined.total_steps

    return serialize_score_state(
        user,
        _score_state_dict_from_obj(obj),
        total_steps_all_time,
    )


# ---------------------------------------------------------------------------
# update_gecko_data port (stateless / per-request).
#
# The consumer keeps `score_state` and `pending_data` in memory for the life
# of a connection so it can apply many step deltas before flushing once on
# disconnect. The HTTP path can't buffer across calls — every request must
# load → mutate → save. So here we treat each incoming payload as a single
# pending entry, run the same recompute math against it, persist score_state,
# and write the entry through process_gecko_data immediately.
# ---------------------------------------------------------------------------

import datetime
import logging

from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


def _load_score_rules() -> Dict[int, Dict[str, Any]]:
    from geckoscripts.models import ScoreRule
    return {
        r.code: {"code": r.code, "label": r.label, "points": r.points}
        for r in ScoreRule.objects.filter(version=1)
    }


def _recompute_energy_in_place(score_state: Dict[str, Any], pending_data, user_id: int) -> Dict[str, Any]:
    """
    Mirror of consumers._recompute_energy_in_memory, but operating on a
    plain dict + pending_data list passed in. Returns the debug dict.
    """
    from . import constants

    ss = score_state
    debug: Dict[str, Any] = {}
    now = timezone.now()
    energy_updated_at = ss["energy_updated_at"]
    elapsed = (now - energy_updated_at).total_seconds()

    if elapsed <= 0:
        return debug

    if (
        ss["multiplier"] > ss["base_multiplier"]
        and ss.get("expires_at")
        and ss["expires_at"] <= now
    ):
        ss["multiplier"] = ss["base_multiplier"]

    prev_energy = ss["energy"]
    prev_surplus = ss["surplus_energy"]

    revival_seconds = ss.get("max_duration_till_revival", 60)

    energy = ss["energy"]
    surplus_energy = ss["surplus_energy"]
    revives_at = ss["revives_at"]

    if energy <= 0.0 and surplus_energy <= 0.0:
        if revives_at and now >= revives_at:
            ss["energy"] = 0.05
            ss["revives_at"] = None
            logger.info("[recompute] revive triggered user=%s", user_id)
        elif not revives_at:
            ss["revives_at"] = now + datetime.timedelta(seconds=revival_seconds)
        ss["energy_updated_at"] = now
        return debug

    stamina = ss.get("stamina", 1.0)
    max_active_hours = ss.get("max_active_hours", 16)
    full_rest_hours = 24 - max_active_hours
    recharge_per_second = 1.0 / (full_rest_hours * 3600) if full_rest_hours > 0 else 0.0
    streak_recharge_per_second = recharge_per_second * 0.5

    new_steps = 0
    active_seconds = 0
    pending_in_window = 0
    pending_stale = 0
    pending_steps_all = 0
    pending_steps_in_window = 0

    for entry in pending_data:
        started = entry.get("_started_dt")
        ended = entry.get("_ended_dt")

        if not started or not ended:
            continue

        start = max(started, energy_updated_at)
        end = min(ended, now)

        entry_steps = entry.get("steps", 0)
        pending_steps_all += entry_steps

        if end > start:
            active_seconds += (end - start).total_seconds()
            pending_in_window += 1
            pending_steps_in_window += entry_steps
        else:
            pending_stale += 1

        new_steps += entry_steps

    rest_seconds = max(0, elapsed - active_seconds)

    multiplier = ss["multiplier"]
    base_multiplier = ss["base_multiplier"]
    expires_at = ss["expires_at"]

    streak_is_active = (
        multiplier > base_multiplier
        and expires_at
        and expires_at > energy_updated_at
    )

    if streak_is_active and active_seconds > 0:
        streak_end = min(expires_at, now)
        streak_seconds = max(0, (streak_end - energy_updated_at).total_seconds())
        streak_ratio = min(1.0, streak_seconds / elapsed) if elapsed > 0 else 0.0

        streak_active_seconds = active_seconds * streak_ratio
        streak_steps = (
            new_steps * (streak_active_seconds / active_seconds)
            if active_seconds else 0
        )
        normal_steps = new_steps - streak_steps

        fatigue = (
            (normal_steps * constants.STEP_FATIGUE_PER_STEP)
            + (
                streak_steps
                * constants.STEP_FATIGUE_PER_STEP
                * constants.STREAK_FATIGUE_MULTIPLIER
            )
        )
        recharge = (
            (rest_seconds * recharge_per_second)
            + (streak_active_seconds * streak_recharge_per_second)
        )
    else:
        fatigue = new_steps * constants.STEP_FATIGUE_PER_STEP
        recharge = rest_seconds * recharge_per_second

    effective_recharge = recharge * stamina
    effective_fatigue = fatigue / stamina if stamina > 0 else fatigue

    net = effective_recharge - effective_fatigue

    if net >= 0:
        room_in_main = 1.0 - energy
        if net <= room_in_main:
            energy += net
        else:
            energy = 1.0
            surplus_energy = min(
                constants.SURPLUS_CAP,
                surplus_energy + (net - room_in_main),
            )
    else:
        drain = -net
        if surplus_energy >= drain:
            surplus_energy -= drain
        else:
            drain -= surplus_energy
            surplus_energy = 0.0
            energy = max(0.0, energy - drain)

    if energy <= 0.0 and surplus_energy <= 0.0:
        if not revives_at:
            revives_at = now + datetime.timedelta(seconds=revival_seconds)
    else:
        revives_at = None

    debug.update({
        "window_seconds": elapsed,
        "active_seconds": active_seconds,
        "new_steps": new_steps,
        "fatigue": fatigue,
        "recharge": recharge,
        "net": net,
        "prev_energy": prev_energy,
        "prev_surplus": prev_surplus,
        "prev_updated_at": energy_updated_at,
        "new_energy": energy,
        "new_surplus": surplus_energy,
        "new_updated_at": now,
        "pending_entries_count": len(pending_data),
        "pending_entries_in_window": pending_in_window,
        "pending_entries_stale": pending_stale,
        "pending_total_steps_all": pending_steps_all,
        "pending_total_steps_in_window": pending_steps_in_window,
        "multiplier_active": multiplier > base_multiplier,
        "streak_expires_at": expires_at,
    })

    ss["energy"] = energy
    ss["surplus_energy"] = surplus_energy
    ss["energy_updated_at"] = now
    ss["revives_at"] = revives_at

    return debug


def _build_pending_entry(
    score_state: Dict[str, Any],
    payload: Dict[str, Any],
    score_rules: Dict[int, Dict[str, Any]],
    friend_id,
) -> Dict[str, Any]:
    """
    Mirror of consumers._handle_update_in_memory's per-entry construction.
    Mutates score_state for streak/multiplier updates from payload.score_state.
    Returns the pending entry dict (suitable for process_gecko_data + recompute).
    """
    ss = score_state

    delta_steps = int(payload.get("steps") or 0)
    delta_distance = int(payload.get("distance") or 0)

    started_on = payload.get("started_on")
    ended_on = payload.get("ended_on")
    points_earned_list = payload.get("points_earned")
    if not isinstance(points_earned_list, list):
        points_earned_list = []

    started_dt = parse_datetime(started_on) if isinstance(started_on, str) else started_on
    ended_dt = parse_datetime(ended_on) if isinstance(ended_on, str) else ended_on

    active_multiplier = ss["multiplier"]
    base_multiplier = ss["base_multiplier"]
    streak_expires_at = ss["expires_at"]

    resolved_points = []
    for e in points_earned_list:
        if not isinstance(e, dict):
            continue

        code = e.get("code")
        label = e.get("label")
        rule = score_rules.get(code)

        if rule is None or rule["label"] != label:
            continue

        ts_raw = e.get("timestamp_earned")
        ts = parse_datetime(ts_raw) if ts_raw else timezone.now()
        if ts is None:
            ts = timezone.now()

        applied_multiplier = (
            active_multiplier
            if (streak_expires_at and ts < streak_expires_at)
            else base_multiplier
        )

        resolved_points.append({
            "amount": rule["points"] * applied_multiplier,
            "reason": rule["label"],
            "code": rule["code"],
            "multiplier": applied_multiplier,
            "timestamp_earned": ts_raw,
        })

    total_points = sum(e["amount"] for e in resolved_points)

    entry = {
        "friend_id": friend_id,
        "steps": delta_steps,
        "distance": delta_distance,
        "started_on": started_on,
        "ended_on": ended_on,
        "total_points": total_points,
        "points_earned": resolved_points,
        "_started_dt": started_dt,
        "_ended_dt": ended_dt,
    }

    score_fields = payload.get("score_state")
    if score_fields and isinstance(score_fields, dict):
        if not (ss["expires_at"] and ss["expires_at"] > timezone.now()):
            max_multiplier = ss.get("max_score_multiplier", 1)
            max_streak_seconds = ss.get("max_streak_length_seconds", 60)

            if "multiplier" in score_fields:
                try:
                    requested = int(score_fields["multiplier"])
                except (TypeError, ValueError):
                    return entry

                if requested > max_multiplier:
                    score_fields["multiplier"] = max_multiplier

                ss["multiplier"] = score_fields["multiplier"]

            requested_length = score_fields.get("expiration_length")
            length_seconds = max_streak_seconds
            if requested_length is not None:
                try:
                    parsed = int(requested_length)
                    if 0 < parsed <= max_streak_seconds:
                        length_seconds = parsed
                except (TypeError, ValueError):
                    pass

            ss["expires_at"] = timezone.now() + datetime.timedelta(seconds=length_seconds)

    return entry


def apply_gecko_data_update(user, friend_id, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stateless equivalent of:
      consumer._handle_update_in_memory(payload)
      consumer._recompute_energy_in_memory()
      consumer._flush_to_db()  (just for this single entry)

    Loads score state, applies the update, persists, runs the gecko_data
    write through process_gecko_data, and returns the FE-bound score_state.
    """
    from .models import GeckoScoreState, GeckoCombinedData
    from .gecko_helpers import process_gecko_data

    obj, _ = GeckoScoreState.objects.get_or_create(user=user)
    obj.recompute_energy()

    score_state = _score_state_dict_from_obj(obj)
    score_rules = _load_score_rules()

    entry = _build_pending_entry(score_state, payload or {}, score_rules, friend_id)

    _recompute_energy_in_place(score_state, [entry], user.id)

    obj.multiplier = score_state["multiplier"]
    obj.expires_at = score_state["expires_at"]
    obj.energy = score_state["energy"]
    obj.surplus_energy = score_state["surplus_energy"]
    obj.energy_updated_at = score_state["energy_updated_at"]
    obj.revives_at = score_state["revives_at"]
    obj.save(update_fields=[
        "multiplier",
        "expires_at",
        "energy",
        "surplus_energy",
        "energy_updated_at",
        "revives_at",
    ])

    if entry["steps"] or entry["distance"] or entry["points_earned"]:
        try:
            process_gecko_data(
                user=user,
                friend_id=entry["friend_id"],
                steps=entry["steps"],
                distance=entry["distance"],
                started_on=entry["started_on"],
                ended_on=entry["ended_on"],
                points_earned_list=entry.get("points_earned", []),
                points_pre_resolved=True,
            )
        except Exception:
            logger.exception(
                "[apply_gecko_data_update] process_gecko_data failed user=%s friend_id=%s",
                user.id,
                friend_id,
            )

    combined, _ = GeckoCombinedData.objects.get_or_create(user=user)
    return serialize_score_state(user, score_state, combined.total_steps)
