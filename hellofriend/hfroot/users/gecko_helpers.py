# from django.db import transaction
# from django.db.models import F
# from django.utils import timezone as _tz
# from django.utils.dateparse import parse_datetime

# import geckoscripts.models
# from friends import models as friends_models
# from users import models as users_models

# import logging
# logger = logging.getLogger('gecko.ws')






# def process_gecko_data(user, friend_id, steps=0, distance=0,
#                        started_on=None, ended_on=None,
#                        points_earned_list=None,
#                        points_pre_resolved=False):
#     """
#     Core logic for recording gecko activity data (steps, distance, duration,
#     points) against both per-friend and combined records.

#     If points_pre_resolved=True, skips ScoreRule lookup and uses
#     points_earned_list as-is (expects dicts with 'amount', 'reason',
#     'code', 'multiplier', 'timestamp_earned').

#     Returns the updated GeckoData instance for the given friend.
#     """




#     delta_steps = int(steps or 0)
#     delta_distance = int(distance or 0)

#     logger.info(
#         f'[process_gecko_data] start '
#         f'user={user.id} friend_id={friend_id} '
#         f'steps={delta_steps} distance={delta_distance} '
#         f'started_on={started_on} ended_on={ended_on} '
#         f'points_count={len(points_earned_list)} '
#         f'points_pre_resolved={points_pre_resolved}'
#     )

#     if not isinstance(points_earned_list, list):
#         points_earned_list = []

#     if not points_pre_resolved:
#         # Resolve points against ScoreRule (version=1)
#         rules_by_code = {
#             r.code: r for r in geckoscripts.models.ScoreRule.objects.filter(version=1)
#         }
#         score_state = users_models.GeckoScoreState.objects.filter(user=user).first()
#         active_multiplier = score_state.multiplier if score_state else 1
#         base_multiplier = score_state.base_multiplier if score_state else 1
#         streak_expires_at = score_state.expires_at if score_state else None

#         resolved_points = []
#         for e in points_earned_list:
#             if not isinstance(e, dict):
#                 continue
#             code = e.get('code')
#             label = e.get('label')
#             rule = rules_by_code.get(code)
#             if rule is None or rule.label != label:
#                 continue

#             ts_raw = e.get('timestamp_earned')
#             ts = parse_datetime(ts_raw) if ts_raw else None
#             if ts is None:
#                 ts = _tz.now()

#             if streak_expires_at and ts < streak_expires_at:
#                 applied_multiplier = active_multiplier
#             else:
#                 applied_multiplier = base_multiplier

#             resolved_points.append({
#                 'amount': rule.points * applied_multiplier,
#                 'reason': rule.label,
#                 'code': rule.code,
#                 'multiplier': applied_multiplier,
#                 'timestamp_earned': ts_raw,
#             })

#         points_earned_list = resolved_points

#     total_points = sum(e.get('amount', 0) for e in points_earned_list)

#     delta_duration = 0
#     if started_on and ended_on:
#         start = parse_datetime(started_on) if isinstance(started_on, str) else started_on
#         end = parse_datetime(ended_on) if isinstance(ended_on, str) else ended_on
#         if start and end:
#             delta_duration = int((end - start).total_seconds())

#     with transaction.atomic():
#         gecko_data_update = {
#             'total_steps': F('total_steps') + delta_steps,
#             'total_distance': F('total_distance') + delta_distance,
#             'total_duration': F('total_duration') + delta_duration,
#         }
#         if total_points:
#             gecko_data_update['total_points'] = F('total_points') + total_points
#         updated_rows = friends_models.GeckoData.objects.filter(
#             user=user, friend_id=friend_id
#         ).update(**gecko_data_update)

#         logger.info(
#             f'[process_gecko_data] GeckoData update '
#             f'user={user.id} friend_id={friend_id} rows_updated={updated_rows}'
#         )
#         combined_data_update = {
#             'total_steps': F('total_steps') + delta_steps,
#             'total_distance': F('total_distance') + delta_distance,
#             'total_duration': F('total_duration') + delta_duration,
#         }
#         if total_points:
#             combined_data_update['total_gecko_points'] = F('total_gecko_points') + total_points
#         combined_rows = users_models.GeckoCombinedData.objects.filter(
#             user=user
#         ).update(**combined_data_update)

#         logger.info(
#             f'[process_gecko_data] GeckoCombinedData update '
#             f'user={user.id} rows_updated={combined_rows}'
#         )
#         existing_combined_session = None
#         existing_friend_session = None

#         logger.info(
#             f'[process_gecko_data] session check '
#             f'user={user.id} started_on={started_on} ended_on={ended_on}'
#         )

#         if started_on and ended_on:
#             existing_combined_session = users_models.GeckoCombinedSession.objects.filter(
#                 user=user,
#                 friend_id=friend_id,
#                 started_on__lte=started_on,
#                 ended_on__gte=started_on,
#             ).first()


#             if existing_combined_session:
#                 logger.info(f'[process_gecko_data] updating combined session id={existing_combined_session.id}')
#             else:
#                 logger.info(f'[process_gecko_data] creating combined session')
#             if existing_combined_session:
#                 existing_combined_session.ended_on = ended_on
#                 existing_combined_session.steps += delta_steps
#                 existing_combined_session.distance += delta_distance
#                 existing_combined_session.points_earned = (existing_combined_session.points_earned or 0) + total_points
#                 existing_combined_session.save()
#             else:
#                 existing_combined_session = users_models.GeckoCombinedSession.objects.create(
#                     user=user,
#                     friend_id=friend_id,
#                     started_on=started_on,
#                     ended_on=ended_on,
#                     steps=delta_steps,
#                     distance=delta_distance,
#                     points_earned=total_points,
#                 )

#             existing_friend_session = friends_models.GeckoDataSession.objects.filter(
#                 user=user,
#                 friend_id=friend_id,
#                 started_on__lte=started_on,
#                 ended_on__gte=started_on,
#             ).first()

#             if existing_friend_session:
#                 existing_friend_session.ended_on = ended_on
#                 existing_friend_session.steps += delta_steps
#                 existing_friend_session.distance += delta_distance
#                 existing_friend_session.points_earned = (existing_friend_session.points_earned or 0) + total_points
#                 existing_friend_session.save()
#             else:
#                 existing_friend_session = friends_models.GeckoDataSession.objects.create(
#                     user=user,
#                     friend_id=friend_id,
#                     started_on=started_on,
#                     ended_on=ended_on,
#                     steps=delta_steps,
#                     distance=delta_distance,
#                     points_earned=total_points,
#                 )

#         if points_earned_list:

#             logger.info(
#                 f'[process_gecko_data] creating ledger entries '
#                 f'user={user.id} count={len(points_earned_list)}'
#             )
#             users_models.GeckoPointsLedger.objects.bulk_create([
#                 users_models.GeckoPointsLedger(
#                     user=user,
#                     friend_id=friend_id,
#                     friend_session=existing_friend_session,
#                     combined_session=existing_combined_session,
#                     amount=e.get('amount', 0),
#                     reason=e.get('reason', ''),
#                     code=e.get('code'),
#                     multiplier=e.get('multiplier', 1),
#                     **({"timestamp_earned": e.get("timestamp_earned")} if e.get("timestamp_earned") else {}),
#                 )
#                 for e in points_earned_list
#             ])

#     return friends_models.GeckoData.objects.get(user=user, friend_id=friend_id)



from datetime import timedelta

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone as _tz
from django.utils.dateparse import parse_datetime

import geckoscripts.models
from friends import models as friends_models
from users import models as users_models
from users import sesh_cache

import logging
logger = logging.getLogger('gecko.ws')


def update_hourly_steps(user, delta_steps=0, delta_distance=0, delta_points=0):
    """
    Rolling 24-hour bucket of activity, keyed by hour-of-day (0-23). Resets
    a bucket when its updated_at is older than 1 hour ago, otherwise
    increments. Always exactly 24 rows per user — wraps every day.

    Write-throughs gecko_24h:{user_id} in Redis so the WS connect path can
    read the seed without hitting Postgres.
    """
    if not (delta_steps or delta_distance or delta_points):
        return

    from . import seed_24h_cache

    now = _tz.now()
    hour = now.hour
    cutoff = now - timedelta(hours=1)

    obj, created = users_models.GeckoHourlySteps.objects.get_or_create(
        user=user, hour=hour,
        defaults={'steps': delta_steps, 'distance': delta_distance, 'points': delta_points},
    )

    if not created:
        if obj.updated_at < cutoff:
            users_models.GeckoHourlySteps.objects.filter(pk=obj.pk).update(
                steps=delta_steps, distance=delta_distance, points=delta_points,
            )
        else:
            users_models.GeckoHourlySteps.objects.filter(pk=obj.pk).update(
                steps=F('steps') + delta_steps,
                distance=F('distance') + delta_distance,
                points=F('points') + delta_points,
            )

    totals = users_models.GeckoHourlySteps.objects.filter(user=user).aggregate(
        steps_total=Sum('steps'),
        sustenance_total=Sum('points'),
    )
    seed_24h_cache.write(
        user.id,
        totals['steps_total'] or 0,
        totals['sustenance_total'] or 0,
    )


def process_gecko_data(user, friend_id, steps=0, distance=0,
                       started_on=None, ended_on=None,
                       points_earned_list=None,
                       points_pre_resolved=False,
                       return_gecko_data=False):
    """
    Core logic for recording gecko activity data (steps, distance, duration,
    points) against both per-friend and combined records.

    If points_pre_resolved=True, skips ScoreRule lookup and uses
    points_earned_list as-is (expects dicts with 'amount', 'reason',
    'code', 'multiplier', 'timestamp_earned').

    If return_gecko_data=True, performs a trailing SELECT and returns the
    updated GeckoData instance. Defaults False — hot socket path skips it.
    """

    delta_steps = int(steps or 0)
    delta_distance = int(distance or 0)

    if not isinstance(points_earned_list, list):
        points_earned_list = []

    logger.debug(
        '[process_gecko_data] start user=%s friend_id=%s steps=%s distance=%s '
        'started_on=%s ended_on=%s points_count=%s points_pre_resolved=%s',
        user.id, friend_id, delta_steps, delta_distance,
        started_on, ended_on, len(points_earned_list), points_pre_resolved,
    )

    if not points_pre_resolved:
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

        logger.debug('[process_gecko_data] resolved points=%s', resolved_points)
        points_earned_list = resolved_points

        

    total_points = sum(e.get('amount', 0) for e in points_earned_list)

    delta_duration = 0
    parsed_start = None
    parsed_end = None
    if started_on and ended_on:
        parsed_start = parse_datetime(started_on) if isinstance(started_on, str) else started_on
        parsed_end = parse_datetime(ended_on) if isinstance(ended_on, str) else ended_on
        if parsed_start and parsed_end:
            delta_duration = int((parsed_end - parsed_start).total_seconds())

    live_points = None

    with transaction.atomic():
        gecko_data_update = {
            'total_steps': F('total_steps') + delta_steps,
            'total_distance': F('total_distance') + delta_distance,
            'total_duration': F('total_duration') + delta_duration,
        }
        if total_points:
            gecko_data_update['total_points'] = F('total_points') + total_points

        updated_rows = friends_models.GeckoData.objects.filter(
            user=user,
            friend_id=friend_id,
        ).update(**gecko_data_update)

        logger.debug(
            '[process_gecko_data] GeckoData update user=%s friend_id=%s rows_updated=%s',
            user.id, friend_id, updated_rows,
        )

        combined_data_update = {
            'total_steps': F('total_steps') + delta_steps,
            'total_distance': F('total_distance') + delta_distance,
            'total_duration': F('total_duration') + delta_duration,
        }
        if total_points:
            combined_data_update['total_gecko_points'] = F('total_gecko_points') + total_points

        # combined_rows = users_models.GeckoCombinedData.objects.filter(
        #     user=user
        # ).update(**combined_data_update)

        score_rows = users_models.GeckoScoreState.objects.filter(
            user=user
        ).update(**combined_data_update)

        logger.debug(
            '[process_gecko_data] GeckoScoreState update user=%s score_rows=%s',
            user.id, score_rows,
        )

        update_hourly_steps(
            user,
            delta_steps=delta_steps,
            delta_distance=delta_distance,
            delta_points=total_points,
        )

        existing_combined_session = None

        if parsed_start and parsed_end:
            existing_combined_session = users_models.GeckoCombinedSession.objects.filter(
                user=user,
                friend_id=friend_id,
                started_on__lte=parsed_start,
                ended_on__gte=parsed_start,
            ).first()

            if existing_combined_session:
                existing_combined_session.ended_on = parsed_end
                existing_combined_session.steps += delta_steps
                existing_combined_session.distance += delta_distance
                existing_combined_session.points_earned = (
                    (existing_combined_session.points_earned or 0) + total_points
                )
                existing_combined_session.save()
            else:
                # Shared parent for live co-op: both participants' rows get
                # the same current live-sesh log id. Only when the peer was
                # present for this window (FE sends friend_id, else null).
                live_log_id = None
                if friend_id is not None:
                    live_log_id = (
                        users_models.UserFriendCurrentLiveSesh.objects
                        .filter(user_id=user.id)
                        .values_list('current_log_id', flat=True)
                        .first()
                    )
                existing_combined_session = users_models.GeckoCombinedSession.objects.create(
                    user=user,
                    friend_id=friend_id,
                    live_sesh_log_id=live_log_id,
                    started_on=parsed_start,
                    ended_on=parsed_end,
                    steps=delta_steps,
                    distance=delta_distance,
                    points_earned=total_points,
                )

        if points_earned_list:
            users_models.GeckoPointsLedger.objects.bulk_create([
                users_models.GeckoPointsLedger(
                    user=user,
                    friend_id=friend_id,
                    combined_session=existing_combined_session,
                    amount=e.get('amount', 0),
                    reason=e.get('reason', ''),
                    code=e.get('code'),
                    multiplier=e.get('multiplier', 1),
                    **(
                        {"timestamp_earned": e.get("timestamp_earned")}
                        if e.get("timestamp_earned") else {}
                    ),
                )
                for e in points_earned_list
            ])

        #added comment

        # Accrue this user's points onto THEIR OWN per-side row
        # (UserFriendLiveSeshPoints, one row per (sesh_log, user)). Host and
        # guest write different rows, so there is no cross-user row contention
        # and no host/guest Case branching. F() keeps repeated same-user
        # frames race-safe. The scoreboard is a read across both side rows.
        # Only accrue to the SHARED sesh scoreboard when the peer was present
        # for this window. The FE pins attribution by sending friend_id (peer
        # present) vs null (solo / peer absent). friend_id None => skip the
        # shared write; the user's own per-user data above still recorded.
        if total_points and friend_id is not None:
            sesh = (
                users_models.UserFriendCurrentLiveSesh.objects
                .filter(user_id=user.id)
                .values('current_log_id', 'friend_id')
                .first()
            )
            log_id = sesh['current_log_id'] if sesh else None
            # The screen can be open for friend B while the user's live
            # sesh is with friend A. Only accrue to the shared scoreboard
            # when the FE-attributed friend IS the sesh's friend; otherwise
            # fall through to the personal ledger only.
            if log_id and sesh['friend_id'] == friend_id:
                side, _ = users_models.UserFriendLiveSeshPoints.objects.get_or_create(
                    sesh_log_id=log_id,
                    user_id=user.id,
                )
                users_models.UserFriendLiveSeshPoints.objects.filter(
                    pk=side.pk,
                ).update(
                    points=F('points') + total_points,
                    steps=F('steps') + delta_steps,
                    distance=F('distance') + delta_distance,
                )

                # Partner identity comes from the log's host/guest (the
                # partner may not have a side row yet).
                log = (
                    users_models.UserFriendLiveSeshLog.objects
                    .filter(pk=log_id)
                    .values('host_id', 'guest_id')
                    .first()
                )
                partner_id = None
                if log:
                    partner_id = (
                        log['guest_id'] if log['host_id'] == user.id
                        else log['host_id']
                    )

                # Read-back: authoritative post-update totals for the FE
                # payload, one query across both side rows.
                totals = {
                    r['user_id']: r['points']
                    for r in users_models.UserFriendLiveSeshPoints.objects
                    .filter(sesh_log_id=log_id)
                    .values('user_id', 'points')
                }
                if partner_id is not None:
                    live_points = {
                        'my_points': totals.get(user.id, total_points),
                        'partner_points': totals.get(partner_id, 0),
                        'partner_id': partner_id,
                    }
                    # Reconnect reads Redis first; drop the stale cached
                    # payload for both sides so next hydrate re-pulls fresh.
                    transaction.on_commit(
                        lambda uid=user.id, pid=partner_id: sesh_cache.invalidate(uid, pid)
                    )

    if not return_gecko_data or friend_id is None:
        return live_points
    return friends_models.GeckoData.objects.get(user=user, friend_id=friend_id)