from django.db import transaction
from django.db.models import F
from django.utils import timezone as _tz
from django.utils.dateparse import parse_datetime

import geckoscripts.models
from friends import models as friends_models
from users import models as users_models


def process_gecko_data(user, friend_id, steps=0, distance=0,
                       started_on=None, ended_on=None,
                       points_earned_list=None):
    """
    Core logic for recording gecko activity data (steps, distance, duration,
    points) against both per-friend and combined records.

    Returns the updated GeckoData instance for the given friend.
    """
    delta_steps = int(steps or 0)
    delta_distance = int(distance or 0)
    if not isinstance(points_earned_list, list):
        points_earned_list = []

    # Resolve points against ScoreRule (version=1)
    rules_by_code = {
        r.code: r for r in geckoscripts.models.ScoreRule.objects.filter(version=1)
    }
    score_state = users_models.GeckoScoreState.objects.filter(user=user).first()
    active_multiplier = score_state.multiplier if score_state else 1
    base_multiplier = score_state.base_multiplier if score_state else 1
    streak_expires_at = score_state.expires_at if score_state else None

    resolved_points = []
    for e in points_earned_list:
        if not isinstance(e, dict):
            continue
        code = e.get('code')
        label = e.get('label')
        rule = rules_by_code.get(code)
        if rule is None or rule.label != label:
            continue

        ts_raw = e.get('timestamp_earned')
        ts = parse_datetime(ts_raw) if ts_raw else None
        if ts is None:
            ts = _tz.now()

        if streak_expires_at and ts < streak_expires_at:
            applied_multiplier = active_multiplier
        else:
            applied_multiplier = base_multiplier

        resolved_points.append({
            'amount': rule.points * applied_multiplier,
            'reason': rule.label,
            'code': rule.code,
            'multiplier': applied_multiplier,
            'timestamp_earned': ts_raw,
        })

    points_earned_list = resolved_points
    total_points = sum(e['amount'] for e in points_earned_list)

    delta_duration = 0
    if started_on and ended_on:
        start = parse_datetime(started_on) if isinstance(started_on, str) else started_on
        end = parse_datetime(ended_on) if isinstance(ended_on, str) else ended_on
        if start and end:
            delta_duration = int((end - start).total_seconds())

    with transaction.atomic():
        gecko_data_update = {
            'total_steps': F('total_steps') + delta_steps,
            'total_distance': F('total_distance') + delta_distance,
            'total_duration': F('total_duration') + delta_duration,
        }
        if total_points:
            gecko_data_update['total_points'] = F('total_points') + total_points
        friends_models.GeckoData.objects.filter(
            user=user, friend_id=friend_id
        ).update(**gecko_data_update)

        combined_data_update = {
            'total_steps': F('total_steps') + delta_steps,
            'total_distance': F('total_distance') + delta_distance,
            'total_duration': F('total_duration') + delta_duration,
        }
        if total_points:
            combined_data_update['total_gecko_points'] = F('total_gecko_points') + total_points
        users_models.GeckoCombinedData.objects.filter(user=user).update(**combined_data_update)

        existing_combined_session = None
        existing_friend_session = None

        if started_on and ended_on:
            existing_combined_session = users_models.GeckoCombinedSession.objects.filter(
                user=user,
                friend_id=friend_id,
                started_on__lte=started_on,
                ended_on__gte=started_on,
            ).first()

            if existing_combined_session:
                existing_combined_session.ended_on = ended_on
                existing_combined_session.steps += delta_steps
                existing_combined_session.distance += delta_distance
                existing_combined_session.points_earned = (existing_combined_session.points_earned or 0) + total_points
                existing_combined_session.save()
            else:
                existing_combined_session = users_models.GeckoCombinedSession.objects.create(
                    user=user,
                    friend_id=friend_id,
                    started_on=started_on,
                    ended_on=ended_on,
                    steps=delta_steps,
                    distance=delta_distance,
                    points_earned=total_points,
                )

            existing_friend_session = friends_models.GeckoDataSession.objects.filter(
                user=user,
                friend_id=friend_id,
                started_on__lte=started_on,
                ended_on__gte=started_on,
            ).first()

            if existing_friend_session:
                existing_friend_session.ended_on = ended_on
                existing_friend_session.steps += delta_steps
                existing_friend_session.distance += delta_distance
                existing_friend_session.points_earned = (existing_friend_session.points_earned or 0) + total_points
                existing_friend_session.save()
            else:
                existing_friend_session = friends_models.GeckoDataSession.objects.create(
                    user=user,
                    friend_id=friend_id,
                    started_on=started_on,
                    ended_on=ended_on,
                    steps=delta_steps,
                    distance=delta_distance,
                    points_earned=total_points,
                )

        if points_earned_list:
            users_models.GeckoPointsLedger.objects.bulk_create([
                users_models.GeckoPointsLedger(
                    user=user,
                    friend_id=friend_id,
                    friend_session=existing_friend_session,
                    combined_session=existing_combined_session,
                    amount=e.get('amount', 0),
                    reason=e.get('reason', ''),
                    code=e.get('code'),
                    multiplier=e.get('multiplier', 1),
                    **({"timestamp_earned": e.get("timestamp_earned")} if e.get("timestamp_earned") else {}),
                )
                for e in points_earned_list
            ])

    return friends_models.GeckoData.objects.get(user=user, friend_id=friend_id)
