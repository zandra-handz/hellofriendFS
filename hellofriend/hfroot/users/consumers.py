# import json
# import logging
# import datetime
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from django.utils import timezone
# from django.utils.dateparse import parse_datetime
# from users import constants

# logger = logging.getLogger('gecko.ws')


# class GeckoEnergyConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         user = self.scope['user']
#         if user.is_anonymous:
#             logger.warning('[connect] anonymous user rejected')
#             await self.close()
#             return

#         self.user = user
#         self.room_group_name = f'gecko_energy_{self.user.id}'
#         logger.info(f'[connect] user={self.user.id} group={self.room_group_name}')

#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name,
#         )
#         await self.accept()

#         # Load DB state into memory once
#         init = await self._load_initial_state()
#         self.score_state = init['score_state']
#         self.score_rules = init['score_rules']
#         self.pending_data = []
#         logger.info(f'[connect] loaded score_state energy={self.score_state["energy"]} rules={len(self.score_rules)}')

#         # Recompute with current time before sending
#         self._recompute_energy_in_memory()

#         await self.send(text_data=json.dumps({
#             'action': 'score_state',
#             'data': self._serialize_score_state(),
#         }))

#     async def disconnect(self, close_code):
#         if hasattr(self, 'pending_data') and self.pending_data:
#             await self._flush_to_db()

#         if hasattr(self, 'room_group_name'):
#             await self.channel_layer.group_discard(
#                 self.room_group_name,
#                 self.channel_name,
#             )

#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         action = data.get('action')

#         if action == 'get_score_state':
#             self._recompute_energy_in_memory()
#             await self.send(text_data=json.dumps({
#                 'action': 'score_state',
#                 'data': self._serialize_score_state(),
#             }))

#         elif action == 'update_gecko_data':
#             payload = data.get('data', {})
#             self._handle_update_in_memory(payload)
#             await self.send(text_data=json.dumps({
#                 'action': 'score_state',
#                 'data': self._serialize_score_state(),
#             }))

#         elif action == 'flush':
#             if self.pending_data:
#                 await self._flush_to_db()
#                 await self.send(text_data=json.dumps({
#                     'action': 'flush_ack',
#                     'data': {'status': 'ok'},
#                 }))
#             else:
#                 await self.send(text_data=json.dumps({
#                     'action': 'flush_ack',
#                     'data': {'status': 'nothing_to_flush'},
#                 }))

#     async def energy_update(self, event):
#         """Called when energy state changes — pushes to client."""
#         await self.send(text_data=json.dumps(event['data']))

#     # ------------------------------------------------------------------
#     # In-memory energy recomputation
#     # ------------------------------------------------------------------

#     def _recompute_energy_in_memory(self):
#         """Pure-Python recompute_energy operating on self.score_state dict."""
#         ss = self.score_state
#         now = timezone.now()
#         energy_updated_at = ss['energy_updated_at']
#         elapsed = (now - energy_updated_at).total_seconds()
#         if elapsed <= 0:
#             return

#         revival_seconds = ss.get('max_duration_till_revival', 60)

#         energy = ss['energy']
#         surplus_energy = ss['surplus_energy']
#         revives_at = ss['revives_at']

#         # Dead state
#         if energy <= 0.0 and surplus_energy <= 0.0:
#             if revives_at and now >= revives_at:
#                 ss['energy'] = 0.05
#                 ss['revives_at'] = None
#             elif not revives_at:
#                 ss['revives_at'] = now + datetime.timedelta(seconds=revival_seconds)
#             ss['energy_updated_at'] = now
#             return

#         stamina = ss.get('stamina', 1.0)
#         max_active_hours = ss.get('max_active_hours', 16)
#         full_rest_hours = 24 - max_active_hours
#         recharge_per_second = 1.0 / (full_rest_hours * 3600)
#         streak_recharge_per_second = recharge_per_second * 0.5

#         # Gather in-memory sessions that overlap this window
#         new_steps = 0
#         active_seconds = 0
#         for entry in self.pending_data:
#             started = entry.get('_started_dt')
#             ended = entry.get('_ended_dt')
#             if started and ended and ended > energy_updated_at:
#                 active_seconds += max(0, (ended - started).total_seconds())
#             new_steps += entry.get('steps', 0)

#         rest_seconds = max(0, elapsed - active_seconds)

#         multiplier = ss['multiplier']
#         base_multiplier = ss['base_multiplier']
#         expires_at = ss['expires_at']

#         streak_is_active = (
#             multiplier > base_multiplier
#             and expires_at > energy_updated_at
#         )

#         if streak_is_active and active_seconds > 0:
#             streak_end = min(expires_at, now)
#             streak_seconds = max(0, (streak_end - energy_updated_at).total_seconds())
#             streak_ratio = min(1.0, streak_seconds / elapsed)

#             streak_active_seconds = active_seconds * streak_ratio
#             streak_steps = new_steps * (streak_active_seconds / active_seconds) if active_seconds else 0
#             normal_steps = new_steps - streak_steps

#             fatigue = (
#                 (normal_steps * constants.STEP_FATIGUE_PER_STEP)
#                 + (streak_steps * constants.STEP_FATIGUE_PER_STEP * constants.STREAK_FATIGUE_MULTIPLIER)
#             )
#             recharge = (
#                 (rest_seconds * recharge_per_second)
#                 + (streak_active_seconds * streak_recharge_per_second)
#             )
#         else:
#             fatigue = new_steps * constants.STEP_FATIGUE_PER_STEP
#             recharge = rest_seconds * recharge_per_second

#         effective_recharge = recharge * stamina
#         effective_fatigue = fatigue / stamina

#         net = effective_recharge - effective_fatigue

#         if net >= 0:
#             room_in_main = 1.0 - energy
#             if net <= room_in_main:
#                 energy += net
#             else:
#                 energy = 1.0
#                 surplus_energy = min(
#                     constants.SURPLUS_CAP,
#                     surplus_energy + (net - room_in_main)
#                 )
#         else:
#             drain = -net
#             if surplus_energy >= drain:
#                 surplus_energy -= drain
#             else:
#                 drain -= surplus_energy
#                 surplus_energy = 0.0
#                 energy = max(0.0, energy - drain)

#         if energy <= 0.0 and surplus_energy <= 0.0:
#             if not revives_at:
#                 revives_at = now + datetime.timedelta(seconds=revival_seconds)
#         else:
#             revives_at = None

#         ss['energy'] = energy
#         ss['surplus_energy'] = surplus_energy
#         ss['energy_updated_at'] = now
#         ss['revives_at'] = revives_at

#     # ------------------------------------------------------------------
#     # In-memory update handler
#     # ------------------------------------------------------------------

#     def _handle_update_in_memory(self, payload):
#         """Process an update_gecko_data payload entirely in memory."""
#         ss = self.score_state

#         delta_steps = int(payload.get('steps') or 0)
#         delta_distance = int(payload.get('distance') or 0)
#         started_on = payload.get('started_on')
#         ended_on = payload.get('ended_on')
#         points_earned_list = payload.get('points_earned')
#         if not isinstance(points_earned_list, list):
#             points_earned_list = []

#         # Parse datetimes
#         started_dt = parse_datetime(started_on) if isinstance(started_on, str) else started_on
#         ended_dt = parse_datetime(ended_on) if isinstance(ended_on, str) else ended_on

#         # Resolve points against cached ScoreRules
#         active_multiplier = ss['multiplier']
#         base_multiplier = ss['base_multiplier']
#         streak_expires_at = ss['expires_at']

#         resolved_points = []
#         for e in points_earned_list:
#             if not isinstance(e, dict):
#                 continue
#             code = e.get('code')
#             label = e.get('label')
#             rule = self.score_rules.get(code)
#             if rule is None or rule['label'] != label:
#                 continue

#             ts_raw = e.get('timestamp_earned')
#             ts = parse_datetime(ts_raw) if ts_raw else None
#             if ts is None:
#                 ts = timezone.now()

#             if streak_expires_at and ts < streak_expires_at:
#                 applied_multiplier = active_multiplier
#             else:
#                 applied_multiplier = base_multiplier

#             resolved_points.append({
#                 'amount': rule['points'] * applied_multiplier,
#                 'reason': rule['label'],
#                 'code': rule['code'],
#                 'multiplier': applied_multiplier,
#                 'timestamp_earned': ts_raw,
#             })

#         total_points = sum(e['amount'] for e in resolved_points)

#         # Accumulate pending data for flush
#         self.pending_data.append({
#             'friend_id': payload.get('friend_id'),
#             'steps': delta_steps,
#             'distance': delta_distance,
#             'started_on': started_on,
#             'ended_on': ended_on,
#             'total_points': total_points,
#             'points_earned': resolved_points,
#             '_started_dt': started_dt,
#             '_ended_dt': ended_dt,
#         })

#         # Apply streak/multiplier update if provided
#         score_fields = payload.get('score_state')
#         if score_fields and isinstance(score_fields, dict):
#             if not (ss['expires_at'] and ss['expires_at'] > timezone.now()):
#                 max_multiplier = ss.get('max_score_multiplier', 1)
#                 max_streak_seconds = ss.get('max_streak_length_seconds', 60)

#                 if 'multiplier' in score_fields:
#                     try:
#                         requested = int(score_fields['multiplier'])
#                     except (TypeError, ValueError):
#                         self._recompute_energy_in_memory()
#                         return
#                     if requested > max_multiplier:
#                         score_fields['multiplier'] = max_multiplier
#                     ss['multiplier'] = score_fields['multiplier']

#                 requested_length = score_fields.get('expiration_length')
#                 length_seconds = max_streak_seconds
#                 if requested_length is not None:
#                     try:
#                         parsed = int(requested_length)
#                         if 0 < parsed <= max_streak_seconds:
#                             length_seconds = parsed
#                     except (TypeError, ValueError):
#                         pass
#                 ss['expires_at'] = timezone.now() + datetime.timedelta(seconds=length_seconds)

#         self._recompute_energy_in_memory()

#     # ------------------------------------------------------------------
#     # Serialization (from in-memory dict, no DB)
#     # ------------------------------------------------------------------

#     def _serialize_score_state(self):
#         """Build the same shape as GeckoScoreStateSerializer from the in-memory dict."""
#         ss = self.score_state
#         max_active_hours = ss.get('max_active_hours', 16)
#         full_rest_hours = 24 - max_active_hours
#         recharge_per_second = 1.0 / (full_rest_hours * 3600)

#         def _fmt_dt(val):
#             if val is None:
#                 return None
#             if isinstance(val, str):
#                 return val
#             return val.isoformat()

#         return {
#             'user': self.user.id,
#             'multiplier': ss['multiplier'],
#             'expires_at': _fmt_dt(ss['expires_at']),
#             'updated_on': _fmt_dt(ss.get('updated_on')),
#             'base_multiplier': ss['base_multiplier'],
#             'energy': ss['energy'],
#             'surplus_energy': ss['surplus_energy'],
#             'energy_updated_at': _fmt_dt(ss['energy_updated_at']),
#             'revives_at': _fmt_dt(ss['revives_at']),
#             'recharge_per_second': recharge_per_second,
#             'streak_recharge_per_second': recharge_per_second * 0.5,
#             'step_fatigue_per_step': constants.STEP_FATIGUE_PER_STEP,
#             'streak_fatigue_multiplier': constants.STREAK_FATIGUE_MULTIPLIER,
#             'surplus_cap': constants.SURPLUS_CAP,
#             'personality_type': ss.get('personality_type'),
#             'personality_type_label': ss.get('personality_type_label'),
#             'memory_type': ss.get('memory_type'),
#             'memory_type_label': ss.get('memory_type_label'),
#             'active_hours_type': ss.get('active_hours_type'),
#             'active_hours_type_label': ss.get('active_hours_type_label'),
#             'story_type': ss.get('story_type'),
#             'story_type_label': ss.get('story_type_label'),
#             'stamina': ss.get('stamina', 1.0),
#             'max_active_hours': max_active_hours,
#             'max_duration_till_revival': ss.get('max_duration_till_revival', 60),
#             'max_score_multiplier': ss.get('max_score_multiplier', 3),
#             'max_streak_length_seconds': ss.get('max_streak_length_seconds', 10),
#             'active_hours': ss.get('active_hours', []),
#             'gecko_created_on': _fmt_dt(ss.get('gecko_created_on')),
#         }

#     # ------------------------------------------------------------------
#     # DB operations (connect + flush only)
#     # ------------------------------------------------------------------

#     @database_sync_to_async
#     def _load_initial_state(self):
#         from users.models import GeckoScoreState
#         from geckoscripts.models import ScoreRule

#         obj, _ = GeckoScoreState.objects.get_or_create(user=self.user)
#         obj.recompute_energy()

#         score_state = {
#             'multiplier': obj.multiplier,
#             'base_multiplier': obj.base_multiplier,
#             'expires_at': obj.expires_at,
#             'energy': obj.energy,
#             'surplus_energy': obj.surplus_energy,
#             'energy_updated_at': obj.energy_updated_at,
#             'revives_at': obj.revives_at,
#             'updated_on': obj.updated_on,
#             'personality_type': obj.personality_type,
#             'personality_type_label': obj.get_personality_type_display(),
#             'memory_type': obj.memory_type,
#             'memory_type_label': obj.get_memory_type_display(),
#             'active_hours_type': obj.active_hours_type,
#             'active_hours_type_label': obj.get_active_hours_type_display(),
#             'story_type': obj.story_type,
#             'story_type_label': obj.get_story_type_display(),
#             'stamina': obj.stamina,
#             'max_active_hours': obj.max_active_hours,
#             'max_duration_till_revival': obj.max_duration_till_revival,
#             'max_score_multiplier': obj.max_score_multiplier,
#             'max_streak_length_seconds': obj.max_streak_length_seconds,
#             'active_hours': obj.active_hours,
#             'gecko_created_on': obj.gecko_created_on,
#         }

#         rules = {
#             r.code: {'code': r.code, 'label': r.label, 'points': r.points}
#             for r in ScoreRule.objects.filter(version=1)
#         }

#         return {'score_state': score_state, 'score_rules': rules}

#     @database_sync_to_async
#     def _flush_to_db(self):
#         from users.gecko_helpers import process_gecko_data
#         from users.models import GeckoScoreState

#         # Flush each pending activity entry — same as the old view did,
#         # one process_gecko_data call per update
#         for entry in self.pending_data:
#             process_gecko_data(
#                 user=self.user,
#                 friend_id=entry['friend_id'],
#                 steps=entry['steps'],
#                 distance=entry['distance'],
#                 started_on=entry['started_on'],
#                 ended_on=entry['ended_on'],
#                 points_earned_list=entry.get('points_earned', []),
#                 points_pre_resolved=True,
#             )

#         # Sync in-memory score state back to DB
#         ss = self.score_state
#         obj, _ = GeckoScoreState.objects.get_or_create(user=self.user)
#         obj.multiplier = ss['multiplier']
#         obj.expires_at = ss['expires_at']
#         obj.energy = ss['energy']
#         obj.surplus_energy = ss['surplus_energy']
#         obj.energy_updated_at = ss['energy_updated_at']
#         obj.revives_at = ss['revives_at']
#         obj.save(update_fields=[
#             'multiplier', 'expires_at', 'energy',
#             'surplus_energy', 'energy_updated_at', 'revives_at',
#         ])

#         self.pending_data.clear()

# =============================================================================
#  GeckoEnergyConsumer
# =============================================================================
#
#  KEY: routine match resync = partner's reply to peer_presence_request.
#       One presence ping → presence + matches refreshed on both peers.
#       Other paths (request/repull/match_request fallback) = edge cases.
#
#  Channels: BE→FE push = method name == event['type'].
#
#  Groups joined on connect():
#    gecko_energy_{uid}                 own
#    gecko_shared_with_friend_{uid}     own
#    gecko_shared_with_friend_{partner} partner (self.joined_sesh_group)
#
#  Cache rule: every read checks `if not self.capsule_matches` →
#              fallback to _check_host_link_and_load (DB + broadcast).
#
# -----------------------------------------------------------------------------
#  FLOW 1 — INITIAL JOIN
# -----------------------------------------------------------------------------
#  GUEST FE          GUEST consumer              HOST consumer        HOST FE
#     │ ws            │ connect                     │                    │
#     ├──────────────▶│ groups, accept              │                    │
#     │               │ _check_host_link_and_load   │                    │
#     │               │  └─ DB → broadcast ────────▶│                    │
#     │ capsule_matches_ready  ◀──── both ────▶ ────┤                    │
#     │◀──────────────│                             ├───────────────────▶│
#     │ set_friend / join_live_sesh → repeats broadcast                  │
#
#  After join:  guest.capsule_matches=[…]   host.capsule_matches=[]
#               (host cache fills on first resync trigger; FE OK either way)
#
# -----------------------------------------------------------------------------
#  FLOW 2 — RESYNC TRIGGERS
# -----------------------------------------------------------------------------
#  A) PRESENCE PING  (focus / foreground)
#     FE A → request_peer_presence → A → ping partner group →
#       B's peer_presence_request handler:
#         - peer_presence(online) → A
#         - cached?  broadcast matches      else _check_host_link_and_load
#     ⇒ both peers get peer_presence + capsule_matches_ready
#
#  B) EXPLICIT RE-FETCH
#     FE A → request_capsule_matches → ping partner →
#       B's capsule_matches_request handler:
#         - cached?  reply to A only        else _check_host_link_and_load (both)
#     no sesh → request_capsule_matches_failed (requester only)
#
#  C) FULL DB REPULL  (after local capsule edit)
#     FE → repull_capsule_matches → _check_host_link_and_load → both peers
#
#  D) send_match_request {gecko_game_type}
#     cached for type? → pick guest_ids[0] + host_ids[0] → match_request_result (both)
#     not cached?      → _check_host_link_and_load → look again
#     still not?       → send_match_request_failed (requester only)
#
# -----------------------------------------------------------------------------
#  ACTION / HANDLER REFERENCE
# -----------------------------------------------------------------------------
#  FE→BE actions:
#    set_friend, get_score_state, get_gecko_message, get_gecko_screen_position,
#    join_live_sesh, leave_live_sesh, request_peer_presence,
#    update_gecko_position, update_host_gecko_position, update_guest_gecko_position,
#    update_gecko_data, flush, send_front_end_text_to_gecko,
#    send_read_status_to_gecko, send_validate_win_request,
#    send_validate_match_win_request, send_match_request,
#    request_capsule_matches, repull_capsule_matches
#
#  BE→FE handlers (type=method name):
#    peer_presence, peer_presence_request, energy_update, live_sesh_cancelled,
#    sesh_context_refresh, gecko_position_broadcast, host_gecko_position_broadcast,
#    guest_gecko_position_broadcast, capsule_matches_ready, capsule_matches_request,
#    match_request_result, validate_win
# =============================================================================

import asyncio
import json
import logging
import ormsgpack
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from users import constants

logger = logging.getLogger('gecko.ws')


class GeckoEnergyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            logger.warning('[connect] anonymous user rejected')
            await self.close()
            return

        self.user = user
        self.friend_id = None

        # these are to color-sync guest screen
        self.friend_light_color = None
        self.friend_dark_color = None



        self.room_group_name = f'gecko_energy_{self.user.id}'
        self.shared_with_friend_group_name = f'gecko_shared_with_friend_{self.user.id}'
        self.gecko_message = None

        active_channel_key = f'gecko_active_channel:{self.user.id}'
        old_channel = await self._cache_get(active_channel_key)
        if old_channel and old_channel != self.channel_name:
            try:
                await self.channel_layer.send(
                    old_channel,
                    {'type': 'force_disconnect'},
                )
                logger.info(
                    f'[connect] user={self.user.id} kicked old channel={old_channel}'
                )
            except Exception:
                logger.exception(
                    f'[connect] failed to kick old channel user={self.user.id}'
                )
        await self._cache_set(active_channel_key, self.channel_name)
        self._active_channel_key = active_channel_key

        logger.info(
            f'[connect] user={self.user.id} '
            f'group={self.room_group_name} '
            f'shared_with_friend_group={self.shared_with_friend_group_name}'
        )

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )
        await self.channel_layer.group_add(
            self.shared_with_friend_group_name,
            self.channel_name,
        )

        partner_id = await self._get_active_live_sesh_partner_id()
        if partner_id is not None:
            self.joined_sesh_group = f'gecko_shared_with_friend_{partner_id}'
            await self.channel_layer.group_add(
                self.joined_sesh_group,
                self.channel_name,
            )
            logger.info(
            f'[connect] user={self.user.id} joined partner sesh group={self.joined_sesh_group}'
            )

            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {'type': 'peer_presence', 'user_id': self.user.id, 'online': True, 'friend_light_color': self.friend_light_color, 'friend_dark_color': self.friend_dark_color}
            )

        await self.accept()

        try:
            init = await self._load_initial_state()
        except Exception:
            logger.exception(f'[connect] failed to load initial state user={self.user.id}')
            await self.close()
            return

        self.score_state = init['score_state']
        self.score_rules = init['score_rules']
        self.pending_data = []
        self.total_steps_all_time = init['total_steps_all_time']
        self.is_host = getattr(self, 'is_host', False)
        self.gecko_screen_position = [] # on FE:  this.lead = [lead0, lead1];
        self.host_gecko_screen_position = [] # on FE:  this.lead = [lead0, lead1];
        self.guest_gecko_screen_position = [] # on FE:  this.lead = [lead0, lead1];
        self.host_is_linked = False
        self.host_linked_friend_id = None
        self.capsule_matches = []
        self.capsule_matches_loaded = False
        self.gecko_play_mode = None



        logger.info(
            f'[connect] loaded score_state user={self.user.id} '
            f'energy={self.score_state["energy"]:.4f} rules={len(self.score_rules)} '
            f'total_steps_all_time={self.total_steps_all_time}'
        )

        self._recompute_energy_in_memory()

        await self.send(text_data=json.dumps({
            'action': 'score_state',
            'data': self._serialize_score_state(),
        }))

        if partner_id is not None and not self.is_host:
            await self._check_host_link_and_load(partner_id)

    async def disconnect(self, close_code):
        logger.info(f'[disconnect] user={getattr(self, "user", None)} code={close_code}')

        if hasattr(self, 'pending_data') and self.pending_data:
            logger.info(f'[disconnect] flushing pending entries={len(self.pending_data)}')
            await self._flush_to_db()

        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

        if hasattr(self, 'shared_with_friend_group_name'):
            await self.channel_layer.group_discard(
                self.shared_with_friend_group_name,
                self.channel_name,
            )

            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {'type': 'peer_presence', 'user_id': self.user.id, 'online': False, 'friend_light_color': None, 'friend_dark_color': None}
            )

        
        
        if getattr(self, 'joined_sesh_group', None):
            if hasattr(self, 'shared_with_friend_group_name'):
                if getattr(self, 'is_host', False):
                    await self.channel_layer.group_send(
                        self.shared_with_friend_group_name,
                        {
                            'type': 'host_gecko_position_broadcast',
                            'from_user': self.user.id,
                            'friend_id': getattr(self, 'friend_id', None),
                            'position': [0, 0],
                            'steps': [],
                            'steps_len': 0,
                            'first_fingers': [],
                            'held_moments': [],
                            'held_moments_len': 0,
                            'moments': [],
                            'moments_len': 0,
                            'timestamp': None,
                        },
                    )
                else:
                    await self.channel_layer.group_send(
                        self.shared_with_friend_group_name,
                        {
                            'type': 'guest_gecko_position_broadcast',
                            'from_user': self.user.id,
                            'position': [0, 0],
                            'steps': [],
                            'timestamp': None,
                        },
                    )
            await self.channel_layer.group_discard(
                self.joined_sesh_group,
                self.channel_name,
            )
            self.joined_sesh_group = None

        # Clear the active-channel cache entry only if it still points to us;
        # otherwise a newer connection has already claimed the slot.
        active_channel_key = getattr(self, '_active_channel_key', None)
        if active_channel_key:
            current = await self._cache_get(active_channel_key)
            if current == self.channel_name:
                await self._cache_delete(active_channel_key)

    async def force_disconnect(self, event):
        logger.info(
            f'[force_disconnect] user={getattr(self, "user", None)} '
            f'channel={self.channel_name}'
        )
        await self.close(code=4000)

    @database_sync_to_async
    def _cache_get(self, key):
        from django.core.cache import cache
        return cache.get(key)

    @database_sync_to_async
    def _cache_set(self, key, value, timeout=None):
        from django.core.cache import cache
        cache.set(key, value, timeout=timeout)

    @database_sync_to_async
    def _cache_delete(self, key):
        from django.core.cache import cache
        cache.delete(key)

    async def receive(self, text_data=None, bytes_data=None):
        if bytes_data is not None:
            try:
                data = ormsgpack.unpackb(bytes_data)
            except Exception:
                logger.warning(f'[receive] invalid msgpack user={self.user.id}')
                return
        else:
            try:
                data = json.loads(text_data)
            except Exception:
                logger.warning(f'[receive] invalid JSON user={self.user.id}')
                return

        action = data.get('action')
        logger.debug(f'[receive] user={self.user.id} action={action}')

        if action == 'set_friend':
            payload = data.get('data', {}) or {}
            try:
                new_fid = int(payload.get('friend_id'))
                self.friend_light_color = payload.get('friend_light_color')
                self.friend_dark_color = payload.get('friend_dark_color')


            except (TypeError, ValueError):
                logger.warning(f'[set_friend] user={self.user.id} invalid friend_id={payload.get("friend_id")!r}')
                await self.send(text_data=json.dumps({
                    'action': 'set_friend_failed',
                    'data': {'reason': 'invalid_friend_id'},
                }))
                return

            # Refresh sesh context so host/friend check is current.
            await self._get_active_live_sesh_partner_id()
            if getattr(self, 'is_host', False) and self.sesh_friend_id is not None:
                if new_fid != self.sesh_friend_id:
                    logger.warning(
                        f'[set_friend] host user={self.user.id} mismatch '
                        f'(provided={new_fid}, sesh={self.sesh_friend_id}) — rejecting'
                    )
                    await self.send(text_data=json.dumps({
                        'action': 'set_friend_failed',
                        'data': {'reason': 'sesh_friend_mismatch'},
                    }))
                    return

            self.friend_id = new_fid
            logger.info(f'[set_friend] user={self.user.id} friend_id={self.friend_id}')
            await self.send(text_data=json.dumps({
                'action': 'set_friend_ok',
                'data': {'friend_id': self.friend_id},
            }))

        elif action == 'get_gecko_message':
            await self.send(text_data=json.dumps({
                'action': 'gecko_message',
                'data': {
                    'from_user': self.user.id,
                    'message': self.gecko_message
                }
            }))

        

        elif action == 'get_gecko_screen_position':
            await self.send(text_data=json.dumps({
                'action': 'gecko_coords',
                'data': {
                    'from_user': self.user.id,
                    'position': self.gecko_screen_position,
                },
            }))

        elif action == 'join_live_sesh':
            partner_id = await self._get_active_live_sesh_partner_id()
            if partner_id is None:
                logger.info(f'[join_live_sesh] user={self.user.id} no active sesh — refusing')
                await self.send(text_data=json.dumps({
                    'action': 'join_live_sesh_failed',
                    'data': {'reason': 'no_active_sesh'},
                }))
                return
            
            # if already in a partner group, discard first
            old = getattr(self, 'joined_sesh_group', None)
            new_group = f'gecko_shared_with_friend_{partner_id}'
            # if old and old != new_group:
            #     await self.channel_layer.group_discard(old, self.channel_name)
            #
            # self.joined_sesh_group = new_group
            # await self.channel_layer.group_add(new_group, self.channel_name)
            if old != new_group:
                if old:
                    await self.channel_layer.group_discard(old, self.channel_name)
                self.joined_sesh_group = new_group
                await self.channel_layer.group_add(new_group, self.channel_name)

            logger.info(
                f'[join_live_sesh] user={self.user.id} joined partner group={new_group}'
            )

            # partner_username / partner_friend_id / partner_friend_name are
            # included for FE convenience. If we ever want to slim this payload,
            # the FE can drop these and look them up itself using partner_id
            # (e.g. /users/{partner_id} + the existing friends list cache).
            await self.send(text_data=json.dumps({
                'action': 'join_live_sesh_ok',
                'data': {
                    'partner_id': partner_id,
                    'partner_username': getattr(self, 'partner_username', None),
                    'partner_friend_id': getattr(self, 'partner_friend_id', None),
                    'partner_friend_name': getattr(self, 'partner_friend_name', None),
                    # 'friend_light_color': self.friend_light_color,
                    # 'friend_dark_color': self.friend_dark_color
                },
            }))

            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {'type': 'peer_presence', 'user_id': self.user.id, 'online': True, 'friend_light_color': self.friend_light_color, 'friend_dark_color': self.friend_dark_color}
            )

            if not self.is_host:
                await self._check_host_link_and_load(partner_id)



        elif action == 'leave_live_sesh':
            old = getattr(self, 'joined_sesh_group', None)
            if old:
                await self.channel_layer.group_send(
                    self.shared_with_friend_group_name,
                    {'type': 'peer_presence', 'user_id': self.user.id, 'online': False, 'friend_light_color': None, 'friend_dark_color': None}
                )
                if getattr(self, 'is_host', False):
                    self.host_gecko_screen_position = []
                    await self.channel_layer.group_send(
                        self.shared_with_friend_group_name,
                        {
                            'type': 'host_gecko_position_broadcast',
                            'from_user': self.user.id,
                            'friend_id': self.friend_id,
                            'position': [0, 0],
                            'steps': [],
                            'steps_len': 0,
                            'first_fingers': [],
                            'held_moments': [],
                            'held_moments_len': 0,
                            'moments': [],
                            'moments_len': 0,
                            'timestamp': None,
                        },
                    )
                else:
                    self.guest_gecko_screen_position = []
                    await self.channel_layer.group_send(
                        self.shared_with_friend_group_name,
                        {
                            'type': 'guest_gecko_position_broadcast',
                            'from_user': self.user.id,
                            'position': [0, 0],
                            'steps': [],
                            'timestamp': None,
                        },
                    )
                await self.channel_layer.group_discard(old, self.channel_name)
                self.joined_sesh_group = None
                self.is_host = False
                logger.info(f'[leave_live_sesh] user={self.user.id} left group={old}')

            await self.send(text_data=json.dumps({
                'action': 'leave_live_sesh_ok',
            }))


        # elif action == 'propose_gecko_win':
        #     payload = data.get('data', {}) or {}

        #     try:
        #         requested_type = int(payload.get('gecko_game_type'))
        #     except (TypeError, ValueError):
        #         logger.warning(
        #             f'[propose_gecko_match_win] user={self.user.id} '
        #             f'invalid gecko_game_type={payload.get("gecko_game_type")!r}'
        #         )
        #         await self.send(text_data=json.dumps({
        #             'action': 'propose_gecko_match_win_failed',
        #             'data': {'reason': 'invalid_gecko_game_type'},
        #         }))
        #         return
            
        #     partner_id = await self._get_active_live_sesh_partner_id()
        #     if partner_id is None:
        #         await self.send(text_data=json.dumps({
        #             'action': 'propose_gecko_win_failed',
        #             'data': {'reason': 'no_active_sesh'},
        #         }))
        #         return

        #     capsule_id = payload.get('capsule_id')
        #     if not capsule_id:
        #         await self.send(text_data=json.dumps({
        #             'action': 'propose_gecko_win_failed',
        #             'data': {'reason': 'missing_capsule_id'},
        #         }))
        #         return

        #     try:
        #         result = await self._propose_gecko_win_db(capsule_id, partner_id)
        #     except Exception:
        #         logger.exception(
        #             f'[propose_gecko_win] db error user={self.user.id} '
        #             f'gecko_game_type={requested_type} '
        #             f'capsule_id={capsule_id}'
        #         )
        #         await self.send(text_data=json.dumps({
        #             'action': 'propose_gecko_win_failed',
        #             'data': {'reason': 'db_error'},
        #         }))
        #         return

        #     if not result['ok']:
        #         await self.send(text_data=json.dumps({
        #             'action': 'propose_gecko_win_failed',
        #             'data': {'reason': result['reason']},
        #         }))
        #         return

        #     logger.info(
        #         f'[propose_gecko_win] user={self.user.id} -> partner={partner_id} '
        #         f'gecko_game_type={requested_type} '
        #         f'capsule_id={capsule_id} ' 
        #     )

        #     await self.channel_layer.group_send(
        #         f'gecko_energy_{partner_id}',
        #         {
        #             'type': 'gecko_win_proposed',
        #             'sender_user_id': self.user.id,
        #             'gecko_game_type': requested_type,
        #             'pending_id': None,
        #             'my_capsule_id': None,
        #             'partner_capsule_id': str(capsule_id),
        #         },
        #     )

        #     # not sure what to send back to owner yet
        #     # await self.channel_layer.group_send(
        #     #     f'gecko_energy_{self.user.id}',
        #     #     {
        #     #         'type': 'gecko_win_proposed',
        #     #         'sender_user_id': partner_id,
        #     #         'gecko_game_type': requested_type,
        #     #          'pending_id': None,
        #     #         'my_capsule_id': str(capsule_id),
        #     #         'partner_capsule_id': None,
        #     #     },
        #     # )


        elif action == 'propose_gecko_win':
            payload = data.get('data', {}) or {}

            partner_id = await self._get_active_live_sesh_partner_id()
            if partner_id is None:
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_win_failed',
                    'data': {'reason': 'no_active_sesh'},
                }))
                return

            capsule_id = payload.get('capsule_id')
            if not capsule_id:
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_win_failed',
                    'data': {'reason': 'missing_capsule_id'},
                }))
                return

            try:
                result = await self._propose_gecko_win_db(capsule_id, partner_id)
            except Exception:
                logger.exception(
                    f'[propose_gecko_win] db error user={self.user.id} '
                    f'capsule_id={capsule_id}'
                )
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_win_failed',
                    'data': {'reason': 'db_error'},
                }))
                return

            if not result['ok']:
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_win_failed',
                    'data': {'reason': result['reason']},
                }))
                return

            gecko_game_type = result['gecko_game_type']

            logger.info(
                f'[propose_gecko_win] user={self.user.id} -> partner={partner_id} '
                f'gecko_game_type={gecko_game_type} '
                f'capsule_id={capsule_id}'
            )

            await self.channel_layer.group_send(
                f'gecko_energy_{partner_id}',
                {
                    'type': 'gecko_win_proposed',
                    'sender_user_id': self.user.id,
                    'gecko_game_type': gecko_game_type,
                    'pending_id': None,
                    'my_capsule_id': None,
                    'partner_capsule_id': str(capsule_id),
                },
            )


        elif action == 'propose_gecko_match_win':
            payload = data.get('data', {}) or {}

            try:
                requested_type = int(payload.get('gecko_game_type'))
            except (TypeError, ValueError):
                logger.warning(
                    f'[propose_gecko_match_win] user={self.user.id} '
                    f'invalid gecko_game_type={payload.get("gecko_game_type")!r}'
                )
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_match_win_failed',
                    'data': {'reason': 'invalid_gecko_game_type'},
                }))
                return

            def _find(matches, t):
                for m in matches or []:
                    if m.get('gecko_game_type') == t:
                        return m
                return None

            partner_id = await self._get_active_live_sesh_partner_id()
            if partner_id is None:
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_match_win_failed',
                    'data': {'reason': 'no_active_sesh'},
                }))
                return

            match = _find(self.capsule_matches, requested_type)

            if match is None and not getattr(self, 'capsule_matches_loaded', False):
                await self._check_host_link_and_load(partner_id)
                match = _find(self.capsule_matches, requested_type)

            if match is None:
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_match_win_failed',
                    'data': {
                        'reason': 'no_match_for_type',
                        'gecko_game_type': requested_type,
                    },
                }))
                return

            guest_ids = match.get('guest_capsule_ids') or []
            host_ids = match.get('host_capsule_ids') or []

            if not guest_ids or not host_ids:
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_match_win_failed',
                    'data': {
                        'reason': 'no_match_for_type',
                        'gecko_game_type': requested_type,
                    },
                }))
                return

            picked_guest = guest_ids[0]
            picked_host = host_ids[0]

            if getattr(self, 'is_host', False):
                my_capsule_id = picked_host
                partner_capsule_id = picked_guest
            else:
                my_capsule_id = picked_guest
                partner_capsule_id = picked_host

            try:
                result = await self._propose_gecko_match_win_db(
                    my_capsule_id,
                    partner_capsule_id,
                    partner_id,
                )
            except Exception:
                logger.exception(
                    f'[propose_gecko_match_win] db error user={self.user.id} '
                    f'gecko_game_type={requested_type} '
                    f'my_capsule_id={my_capsule_id} '
                    f'partner_capsule_id={partner_capsule_id}'
                )
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_match_win_failed',
                    'data': {'reason': 'db_error'},
                }))
                return

            if not result['ok']:
                await self.send(text_data=json.dumps({
                    'action': 'propose_gecko_match_win_failed',
                    'data': {'reason': result['reason']},
                }))
                return

            logger.info(
                f'[propose_gecko_match_win] user={self.user.id} -> partner={partner_id} '
                f'gecko_game_type={requested_type} '
                f'my_capsule_id={my_capsule_id} '
                f'partner_capsule_id={partner_capsule_id} '
                f'pending_id={result["pending_id"]}'
            )

            await self.channel_layer.group_send(
                f'gecko_energy_{partner_id}',
                {
                    'type': 'gecko_win_proposed',
                    'sender_user_id': self.user.id,
                    'gecko_game_type': requested_type,
                    'pending_id': result['pending_id'],
                    'my_capsule_id': str(partner_capsule_id),
                    'partner_capsule_id': str(my_capsule_id),
                },
            )

            await self.channel_layer.group_send(
                f'gecko_energy_{self.user.id}',
                {
                    'type': 'gecko_win_proposed',
                    'sender_user_id': partner_id,
                    'gecko_game_type': requested_type,
                    'pending_id': result['pending_id'],
                    'my_capsule_id': str(my_capsule_id),
                    'partner_capsule_id': str(partner_capsule_id),
                },
            )

            await self.channel_layer.group_send(
                f'gecko_energy_{self.user.id}',
                {
                    'type': 'propose_gecko_match_win_ok',
                    'pending_id': result['pending_id'],
                    'other_user_id': partner_id,
                    'gecko_game_type': requested_type,
                    'capsule_id': str(partner_capsule_id),
                },
            )

            await self.channel_layer.group_send(
                f'gecko_energy_{partner_id}',
                {
                    'type': 'propose_gecko_match_win_ok',
                    'pending_id': result['pending_id'],
                    'other_user_id': self.user.id,
                    'gecko_game_type': requested_type,
                    'capsule_id': str(my_capsule_id),
                },
            )
                    
                



        elif action == 'request_capsule_matches':
            partner_group = getattr(self, 'joined_sesh_group', None)
            if not partner_group:
                partner_id = await self._get_active_live_sesh_partner_id()
                if partner_id is None:
                    logger.info(
                        f'[request_capsule_matches] user={self.user.id} no active sesh partner'
                    )
                    return
                partner_group = f'gecko_shared_with_friend_{partner_id}'

            logger.info(
                f'[request_capsule_matches] user={self.user.id} '
                f'pinging partner_group={partner_group}'
            )
            await self.channel_layer.group_send(
                partner_group,
                {
                    'type': 'capsule_matches_request',
                    'requester_user_id': self.user.id,
                },
            )

        elif action == 'repull_capsule_matches':
            partner_id = await self._get_active_live_sesh_partner_id()
            if partner_id is None:
                logger.info(
                    f'[repull_capsule_matches] user={self.user.id} no active sesh — refusing'
                )
                await self.send(text_data=json.dumps({
                    'action': 'repull_capsule_matches_failed',
                    'data': {'reason': 'no_active_sesh'},
                }))
                return
            await self._check_host_link_and_load(partner_id)

        elif action == 'request_peer_presence':
            partner_group = getattr(self, 'joined_sesh_group', None)
            if not partner_group:
                partner_id = await self._get_active_live_sesh_partner_id()
                if partner_id is None:
                    logger.info(
                        f'[request_peer_presence] user={self.user.id} no active sesh partner'
                    )
                    return
                partner_group = f'gecko_shared_with_friend_{partner_id}'

            logger.info(
                f'[request_peer_presence] user={self.user.id} '
                f'pinging partner_group={partner_group}'
            )
            await self.channel_layer.group_send(
                partner_group,
                {
                    'type': 'peer_presence_request',
                    'requester_user_id': self.user.id,
                },
            )

        elif action == 'update_gecko_position':
            if self.friend_id is None:
                logger.warning(f'[update_gecko_position] user={self.user.id} friend_id not set — ignoring')
                return
            payload = data.get('data', {})
            pos = payload.get('position')
            if not (isinstance(pos, list) and len(pos) == 2):
                logger.warning(
                    f'[update_gecko_position] user={self.user.id} invalid position={pos!r}'
                )
                return

            self.gecko_screen_position = pos
            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {
                    'type': 'gecko_position_broadcast',
                    'from_user': self.user.id,
                    'friend_id': self.friend_id,
                    'position': pos,
                },
            )

        elif action == 'send_front_end_text_to_gecko':
            payload = data.get('data', {})
            message = payload.get('message')

            self.gecko_message = message
               

            await self.send(text_data=json.dumps({
                'action': 'gecko_message',
                'data': {
                    'from_user': self.user.id,
                    'message': self.gecko_message,
                },
            }))
            return


        elif action == 'send_validate_win_request':
            payload = data.get('data', {})
            validate = payload.get('validate')

            if validate:
                return


            return
 

    
        elif action == 'send_read_status_to_gecko':
            payload = data.get('data', {})
            message_code = payload.get('message_code')

            if message_code == 0:
                self.gecko_message = "Hi! I'm going to start reading this, if ya don't mind!"
            elif message_code == 1:
                self.gecko_message = "Still have some to read..."
             
            elif message_code == 2:
                self.gecko_message = "Read em all!"
            else:
                self.gecko_message = "Hrrrrrmmm hmmmmmmmm"

            await self.send(text_data=json.dumps({
                'action': 'gecko_message',
                'data': {
                    'from_user': self.user.id,
                    'message': self.gecko_message,
                },
            }))
            return

            

        elif action == 'update_host_gecko_position':
            if not getattr(self, 'is_host', False):
                # Cache may be stale if the push-invalidation from the sesh-accept
                # view was missed. Re-read once before rejecting.
                await self._get_active_live_sesh_partner_id()
                if not getattr(self, 'is_host', False):
                    logger.warning(
                        f'[update_host_gecko_position] user={self.user.id} not host — ignoring'
                    )
                    return
                logger.info(
                    f'[update_host_gecko_position] user={self.user.id} cache was stale, now host'
                )
            if self.friend_id is None:
                logger.warning(f'[update_host_gecko_position] user={self.user.id} friend_id not set — ignoring')
                return
            payload = data.get('data', {})
            pos = payload.get('position')
            steps = payload.get('steps') or []
            steps_len = payload.get('steps_len')
            first_fingers = payload.get('first_fingers') or []
            held_moments = payload.get('held_moments') or []
            held_moments_len = payload.get('held_moments_len')
            moments = payload.get('moments') or []
            moments_len = payload.get('moments_len')

            if not (isinstance(pos, list) and len(pos) == 2):
                logger.warning(
                    f'[update_host_gecko_position] user={self.user.id} invalid position={pos!r}'
                )
                return

            self.host_gecko_screen_position = pos
            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {
                    'type': 'host_gecko_position_broadcast',
                    'from_user': self.user.id,
                    'friend_id': self.friend_id,
                    'position': pos,
                    'steps': steps,
                    'steps_len': steps_len,
                    'first_fingers': first_fingers,
                    'held_moments': held_moments,
                    'held_moments_len': held_moments_len,
                    'moments': moments,
                    'moments_len': moments_len,
                    'timestamp': payload.get('timestamp'),
                },
            )

        elif action == 'send_all_host_capsules':
            if not getattr(self, 'is_host', False):
                await self._get_active_live_sesh_partner_id()
                if not getattr(self, 'is_host', False):
                    logger.warning(
                        f'[send_all_host_capsules] user={self.user.id} not host — ignoring'
                    )
                    return
                logger.info(
                    f'[send_all_host_capsules] user={self.user.id} cache was stale, now host'
                )

            if self.friend_id is None:
                logger.warning(
                    f'[send_all_host_capsules] user={self.user.id} friend_id not set — ignoring'
                )
                return

            payload = data.get('data', {}) or {}
            moments = payload.get('moments') or []
            moments_len = payload.get('moments_len')

            if not isinstance(moments, list):
                logger.warning(
                    f'[send_all_host_capsules] user={self.user.id} invalid moments={moments!r}'
                )
                return

            if moments_len is None:
                moments_len = len(moments)

            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {
                    'type': 'all_host_capsules_broadcast',
                    'from_user': self.user.id,
                    'friend_id': self.friend_id,
                    'moments': moments,
                    'moments_len': moments_len,
                    'timestamp': payload.get('timestamp'),
                },
            )


        elif action == 'update_guest_gecko_position':
            if getattr(self, 'is_host', False):
                await self._get_active_live_sesh_partner_id()
                if getattr(self, 'is_host', False):
                    logger.warning(
                        f'[update_guest_gecko_position] user={self.user.id} is host — ignoring'
                    )
                    return
                logger.info(
                    f'[update_guest_gecko_position] user={self.user.id} cache was stale, now guest'
                )
            payload = data.get('data', {})
            pos = payload.get('position')
            steps = payload.get('steps') or [] 

            if not (isinstance(pos, list) and len(pos) == 2):
                logger.warning(
                    f'[update_guest_gecko_position] user={self.user.id} invalid position={pos!r}'
                )
                return

            self.guest_gecko_screen_position = pos
            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {
                    'type': 'guest_gecko_position_broadcast',
                    'from_user': self.user.id,
                    'position': pos,
                    'steps': steps,
                    'timestamp': payload.get('timestamp'),
                },
            )

        elif action == 'update_capsule_progress':
            payload = data.get('data', {}) or {}

            capsule_id = payload.get('capsule_id')
            new_progress = payload.get('new_progress')

            if not capsule_id:
                logger.warning(
                    f'[update_capsule_progress] user={self.user.id} missing capsule_id'
                )
                return

            if not isinstance(new_progress, (int, float)):
                logger.warning(
                    f'[update_capsule_progress] user={self.user.id} invalid progress={new_progress!r}'
                )
                return

            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {
                    'type': 'capsule_progress_broadcast',
                    'from_user': self.user.id,
                    'capsule_id': capsule_id,
                    # 'new_progress': max(0, min(1, float(new_progress))),
                    'new_progress': int(new_progress),
                    'timestamp': payload.get('timestamp'),
                },
            )

        elif action == 'get_score_state':
            self._recompute_energy_in_memory()
            await self._record_sync_sample('get_score_state', None)

            await self.send(text_data=json.dumps({
                'action': 'score_state',
                'data': self._serialize_score_state(),
            }))

        elif action == 'update_gecko_data':
            if self.friend_id is None:
                logger.warning(f'[update_gecko_data] user={self.user.id} friend_id not set — ignoring')
                return
            payload = data.get('data', {})
            logger.debug(
                f'[update] user={self.user.id} steps={payload.get("steps")} '
                f'distance={payload.get("distance")}'
            )

            self._handle_update_in_memory(payload)

            event_type = payload.get('event_type')
            if not isinstance(event_type, str) or not event_type:
                event_type = 'update_gecko_data'
            await self._record_sync_sample(event_type, payload)

            await self.send(text_data=json.dumps({
                'action': 'score_state',
                'data': self._serialize_score_state(),
            }))

        elif action == 'flush':
            if self.pending_data:
                logger.info(f'[flush] user={self.user.id} entries={len(self.pending_data)}')
                await self._flush_to_db()

                await self.send(text_data=json.dumps({
                    'action': 'flush_ack',
                    'data': {'status': 'ok'},
                }))
            else:
                logger.debug(f'[flush] user={self.user.id} nothing to flush')
                await self.send(text_data=json.dumps({
                    'action': 'flush_ack',
                    'data': {'status': 'nothing_to_flush'},
                }))

        else:
            logger.warning(f'[receive] unknown action user={self.user.id} action={action}')


    # TO FINISH
    async def validate_win(self, event):
        if event['user_id'] == self.user.id:
            return

    async def peer_presence(self, event):
        if event['user_id'] == self.user.id:
            return
        await self.send(text_data=json.dumps({
            'action': 'peer_presence',
            'data': { 'user_id': event['user_id'], 'online': event['online'], 'friend_light_color': event['friend_light_color'], 'friend_dark_color': event['friend_dark_color']}
        }))

    async def peer_presence_request(self, event):
        requester_id = event.get('requester_user_id')
        if requester_id == self.user.id:
            return
        await self.channel_layer.group_send(
            f'gecko_shared_with_friend_{requester_id}',
            {'type': 'peer_presence', 'user_id': self.user.id, 'online': True, 'friend_light_color': self.friend_light_color, 'friend_dark_color': self.friend_dark_color},
        )

        if not self.capsule_matches:
            await self._check_host_link_and_load(requester_id)
            return

        if getattr(self, 'is_host', False):
            host_user_id = self.user.id
            guest_user_id = requester_id
        else:
            host_user_id = requester_id
            guest_user_id = self.user.id

        target_group = (
            getattr(self, 'joined_sesh_group', None)
            or self.shared_with_friend_group_name
        )
        await self.channel_layer.group_send(
            target_group,
            {
                'type': 'capsule_matches_ready',
                'is_linked': self.host_is_linked,
                'host_user_id': host_user_id,
                'guest_user_id': guest_user_id,
                'friend_id': self.host_linked_friend_id,
                'matches': self.capsule_matches,
            },
        )

    async def capsule_matches_request(self, event):
        requester_id = event.get('requester_user_id')
        if requester_id == self.user.id:
            return

        if not self.capsule_matches:
            await self._check_host_link_and_load(requester_id)
            return

        if getattr(self, 'is_host', False):
            host_user_id = self.user.id
            guest_user_id = requester_id
        else:
            host_user_id = requester_id
            guest_user_id = self.user.id

        await self.channel_layer.group_send(
            f'gecko_shared_with_friend_{requester_id}',
            {
                'type': 'capsule_matches_ready',
                'is_linked': self.host_is_linked,
                'host_user_id': host_user_id,
                'guest_user_id': guest_user_id,
                'friend_id': self.host_linked_friend_id,
                'matches': self.capsule_matches,
            },
        )
        
    async def energy_update(self, event):
        logger.debug(f'[push] energy_update user={self.user.id}')
        await self.send(text_data=json.dumps(event['data']))

    async def live_sesh_cancelled(self, event):
        # Pushed via channel_layer.group_send to gecko_energy_{user_id} when
        # a live sesh is cancelled. Notify the FE then close the socket.
        try:
            await self.send(text_data=json.dumps({
                'action': 'live_sesh_cancelled',
                'data': event.get('data', {}),
            }))
        finally:
            logger.info(f'[live_sesh_cancelled] closing socket user={getattr(self, "user", None)}')
            await self.close()

    async def sesh_context_refresh(self, event):
        await self._get_active_live_sesh_partner_id()
        logger.info(
            f'[sesh_context_refresh] user={self.user.id} '
            f'is_host={self.is_host} sesh_friend_id={self.sesh_friend_id}'
        )
        event_partner = event.get('partner_id')
        old = getattr(self, 'joined_sesh_group', None)

        if event_partner is None:
            if old:
                await self.channel_layer.group_discard(old, self.channel_name)
                self.joined_sesh_group = None
            return

        new_group = f'gecko_shared_with_friend_{event_partner}'
        if old != new_group:
            if old:
                await self.channel_layer.group_discard(old, self.channel_name)
            await self.channel_layer.group_add(new_group, self.channel_name)
            self.joined_sesh_group = new_group

    async def gecko_position_broadcast(self, event):
        await self.send(bytes_data=ormsgpack.packb({
            'action': 'gecko_coords',
            'data': {
                'from_user': event.get('from_user'),
                'friend_id': event.get('friend_id'),
                'position': event.get('position'),
            },
        }))

    async def host_gecko_position_broadcast(self, event):
        await self.send(bytes_data=ormsgpack.packb({
            'action': 'host_gecko_coords',
            'data': {
                'from_user': event.get('from_user'),
                'friend_id': event.get('friend_id'),
                'position': event.get('position'),
                'steps': event.get('steps', []),
                'steps_len': event.get('steps_len'),
                'first_fingers': event.get('first_fingers', []),
                'held_moments': event.get('held_moments', []),
                'held_moments_len': event.get('held_moments_len'),
                'moments': event.get('moments', []),
                'moments_len': event.get('moments_len'),
                'timestamp': event.get('timestamp'),
            },
        }))

    async def all_host_capsules_broadcast(self, event):
        if event.get('from_user') == self.user.id:
            return

        await self.send(bytes_data=ormsgpack.packb({
            'action': 'all_host_capsules',
            'data': {
                'from_user': event.get('from_user'),
                'friend_id': event.get('friend_id'),
                'moments': event.get('moments', []),
                'moments_len': event.get('moments_len'),
                'timestamp': event.get('timestamp'),
            },
        }))

    async def guest_gecko_position_broadcast(self, event):
        await self.send(bytes_data=ormsgpack.packb({
            'action': 'guest_gecko_coords',
            'data': {
                'from_user': event.get('from_user'),
                'position': event.get('position'),
                'steps': event.get('steps', []), 
                'timestamp': event.get('timestamp'),
            },
        }))

    async def capsule_progress_broadcast(self, event):
        await self.send(bytes_data=ormsgpack.packb({
            'action': 'capsule_progress',
            'data': {
                'from_user': event.get('from_user'),
                'capsule_id': event.get('capsule_id'),
                'new_progress': event.get('new_progress'),
                'timestamp': event.get('timestamp'),
            },
        }))

    # ------------------------------------------------------------------
    # In-memory energy recomputation
    # ------------------------------------------------------------------

    def _recompute_energy_in_memory(self):
        ss = self.score_state
        self._last_recompute_debug = None
        now = timezone.now()
        energy_updated_at = ss['energy_updated_at']
        elapsed = (now - energy_updated_at).total_seconds()

        if elapsed <= 0:
            return
    
        if (
            ss['multiplier'] > ss['base_multiplier']
            and ss.get('expires_at')
            and ss['expires_at'] <= now
        ):
            ss['multiplier'] = ss['base_multiplier']

        prev_energy = ss['energy']
        prev_surplus = ss['surplus_energy']

        revival_seconds = ss.get('max_duration_till_revival', 60)

        energy = ss['energy']
        surplus_energy = ss['surplus_energy']
        revives_at = ss['revives_at']

        if energy <= 0.0 and surplus_energy <= 0.0:
            if revives_at and now >= revives_at:
                ss['energy'] = 0.05
                ss['revives_at'] = None
                logger.info(f'[recompute] revive triggered user={self.user.id}')
            elif not revives_at:
                ss['revives_at'] = now + datetime.timedelta(seconds=revival_seconds)
            ss['energy_updated_at'] = now
            return

        stamina = ss.get('stamina', 1.0)
        max_active_hours = ss.get('max_active_hours', 16)
        full_rest_hours = 24 - max_active_hours
        recharge_per_second = 1.0 / (full_rest_hours * 3600)
        streak_recharge_per_second = recharge_per_second * 0.5

        new_steps = 0
        active_seconds = 0
        pending_in_window = 0
        pending_stale = 0
        pending_steps_all = 0
        pending_steps_in_window = 0
        # for entry in self.pending_data:
        #     started = entry.get('_started_dt')
        #     ended = entry.get('_ended_dt')
        #     if started and ended and ended > energy_updated_at:
        #         active_seconds += max(0, (ended - started).total_seconds())
        #     new_steps += entry.get('steps', 0)

        for entry in self.pending_data:
            started = entry.get('_started_dt')
            ended = entry.get('_ended_dt')

            if not started or not ended:
                continue

            # clamp to recompute window
            start = max(started, energy_updated_at)
            end = min(ended, now)

            entry_steps = entry.get('steps', 0)
            pending_steps_all += entry_steps

            if end > start:
                active_seconds += (end - start).total_seconds()
                pending_in_window += 1
                pending_steps_in_window += entry_steps
            else:
                pending_stale += 1

            new_steps += entry_steps

        rest_seconds = max(0, elapsed - active_seconds)

        multiplier = ss['multiplier']
        base_multiplier = ss['base_multiplier']
        expires_at = ss['expires_at']

        streak_is_active = (
            multiplier > base_multiplier
            and expires_at
            and expires_at > energy_updated_at
        )

        logger.info(
            f'[recompute inputs] user={self.user.id} '
            f'energy_before={prev_energy:.12f} '
            f'surplus_before={prev_surplus:.12f} '
            f'elapsed={elapsed:.6f} '
            f'new_steps={new_steps} '
            f'active_seconds={active_seconds:.6f} '
            f'rest_seconds={rest_seconds:.6f} '
            f'stamina={stamina:.6f} '
            f'multiplier={multiplier} '
            f'base_multiplier={base_multiplier} '
            f'expires_at={expires_at} '
            f'streak_is_active={streak_is_active} '
            f'recharge_per_second={recharge_per_second:.12f} '
            f'streak_recharge_per_second={streak_recharge_per_second:.12f}'
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
        effective_fatigue = fatigue / stamina

        net = effective_recharge - effective_fatigue



        if net >= 0:
            room_in_main = 1.0 - energy
            if net <= room_in_main:
                energy += net
            else:
                energy = 1.0
                surplus_energy = min(
                    constants.SURPLUS_CAP,
                    surplus_energy + (net - room_in_main)
                )
        else:
            drain = -net
            if surplus_energy >= drain:
                surplus_energy -= drain
            else:
                drain -= surplus_energy
                surplus_energy = 0.0
                energy = max(0.0, energy - drain)

        logger.info(
            f'[recompute outputs] user={self.user.id} '
            f'fatigue={fatigue:.12f} '
            f'recharge={recharge:.12f} '
            f'effective_recharge={effective_recharge:.12f} '
            f'effective_fatigue={effective_fatigue:.12f} '
            f'net={net:.12f} '
            f'energy_after={energy:.12f} '
            f'surplus_after={surplus_energy:.12f}'
        )


        if energy <= 0.0 and surplus_energy <= 0.0:
            if not revives_at:
                revives_at = now + datetime.timedelta(seconds=revival_seconds)
        else:
            revives_at = None

        self._last_recompute_debug = {
            'window_seconds': elapsed,
            'active_seconds': active_seconds,
            'new_steps': new_steps,
            'fatigue': fatigue,
            'recharge': recharge,
            'net': net,
            'prev_energy': prev_energy,
            'prev_surplus': prev_surplus,
            'prev_updated_at': energy_updated_at,
            'new_energy': energy,
            'new_surplus': surplus_energy,
            'new_updated_at': now,
            'pending_entries_count': len(self.pending_data),
            'pending_entries_in_window': pending_in_window,
            'pending_entries_stale': pending_stale,
            'pending_total_steps_all': pending_steps_all,
            'pending_total_steps_in_window': pending_steps_in_window,
            'multiplier_active': multiplier > base_multiplier,
            'streak_expires_at': expires_at,
        }

        ss['energy'] = energy
        ss['surplus_energy'] = surplus_energy
        ss['energy_updated_at'] = now
        ss['revives_at'] = revives_at

        logger.debug(
            f'[recompute] user={self.user.id} '
            f'energy {prev_energy:.4f}->{energy:.4f} '
            f'surplus {prev_surplus:.4f}->{surplus_energy:.4f} '
            f'steps={new_steps} elapsed={elapsed:.2f}s'
        )

    # ------------------------------------------------------------------
    # In-memory update handler
    # ------------------------------------------------------------------

    def _handle_update_in_memory(self, payload):
        ss = self.score_state

        delta_steps = int(payload.get('steps') or 0)
        delta_distance = int(payload.get('distance') or 0)

        self.total_steps_all_time += delta_steps

        logger.debug(
            f'[update_mem] user={self.user.id} '
            f'steps={delta_steps} distance={delta_distance} '
            f'total_steps_all_time={self.total_steps_all_time}'
        )

        started_on = payload.get('started_on')
        ended_on = payload.get('ended_on')
        points_earned_list = payload.get('points_earned')

        if not isinstance(points_earned_list, list):
            points_earned_list = []

        started_dt = parse_datetime(started_on) if isinstance(started_on, str) else started_on
        ended_dt = parse_datetime(ended_on) if isinstance(ended_on, str) else ended_on


        logger.info(
            f'[update_mem payload] user={self.user.id} '
            f'steps={delta_steps} '
            f'distance={delta_distance} '
            f'total_steps_all_time={self.total_steps_all_time} '
            f'started_on={started_on} '
            f'ended_on={ended_on} '
            f'started_dt={started_dt} '
            f'ended_dt={ended_dt} '
            f'points_count={len(points_earned_list)}'
        )
        active_multiplier = ss['multiplier']
        base_multiplier = ss['base_multiplier']
        streak_expires_at = ss['expires_at']

        resolved_points = []
        for e in points_earned_list:
            if not isinstance(e, dict):
                continue

            code = e.get('code')
            label = e.get('label')
            rule = self.score_rules.get(code)

            if rule is None or rule['label'] != label:
                continue

            ts_raw = e.get('timestamp_earned')
            ts = parse_datetime(ts_raw) if ts_raw else timezone.now()
            if ts is None:
                ts = timezone.now()

            applied_multiplier = (
                active_multiplier
                if (streak_expires_at and ts < streak_expires_at)
                else base_multiplier
            )

            resolved_points.append({
                'amount': rule['points'] * applied_multiplier,
                'reason': rule['label'],
                'code': rule['code'],
                'multiplier': applied_multiplier,
                'timestamp_earned': ts_raw,
            })

        total_points = sum(e['amount'] for e in resolved_points)

        self.pending_data.append({
            'friend_id': self.friend_id,
            'steps': delta_steps,
            'distance': delta_distance,
            'started_on': started_on,
            'ended_on': ended_on,
            'total_points': total_points,
            'points_earned': resolved_points,
            '_started_dt': started_dt,
            '_ended_dt': ended_dt,
        })

        logger.info(
            f'[update_mem pending] user={self.user.id} '
            f'pending_count={len(self.pending_data)} '
            f'last_steps={self.pending_data[-1]["steps"]} '
            f'last_started_dt={self.pending_data[-1]["_started_dt"]} '
            f'last_ended_dt={self.pending_data[-1]["_ended_dt"]}'
        )

        logger.debug(
            f'[update_mem] queued user={self.user.id} '
            f'entries={len(self.pending_data)} total_points={total_points}'
        )

        score_fields = payload.get('score_state')
        if score_fields and isinstance(score_fields, dict):
            if not (ss['expires_at'] and ss['expires_at'] > timezone.now()):
                max_multiplier = ss.get('max_score_multiplier', 1)
                max_streak_seconds = ss.get('max_streak_length_seconds', 60)

                if 'multiplier' in score_fields:
                    try:
                        requested = int(score_fields['multiplier'])
                    except (TypeError, ValueError):
                        self._recompute_energy_in_memory()
                        return

                    if requested > max_multiplier:
                        score_fields['multiplier'] = max_multiplier

                    ss['multiplier'] = score_fields['multiplier']

                requested_length = score_fields.get('expiration_length')
                length_seconds = max_streak_seconds
                if requested_length is not None:
                    try:
                        parsed = int(requested_length)
                        if 0 < parsed <= max_streak_seconds:
                            length_seconds = parsed
                    except (TypeError, ValueError):
                        pass

                ss['expires_at'] = timezone.now() + datetime.timedelta(seconds=length_seconds)

        self._recompute_energy_in_memory()

    # ------------------------------------------------------------------
    # Sync telemetry
    # ------------------------------------------------------------------

    async def _record_sync_sample(self, trigger, payload):
        debug = getattr(self, '_last_recompute_debug', None)
        if not debug:
            return

        client_energy = payload.get('client_energy') if payload else None
        client_surplus = payload.get('client_surplus_energy') if payload else None
        client_multiplier = payload.get('client_multiplier') if payload else None
        client_computed_at_raw = payload.get('client_computed_at') if payload else None
        client_computed_at = (
            parse_datetime(client_computed_at_raw)
            if isinstance(client_computed_at_raw, str) else None
        )
        client_steps = payload.get('steps') if payload else None
        client_distance = payload.get('distance') if payload else None

        client_started_on_raw = payload.get('started_on') if payload else None
        client_started_on = (
            parse_datetime(client_started_on_raw)
            if isinstance(client_started_on_raw, str) else None
        )
        client_ended_on_raw = payload.get('ended_on') if payload else None
        client_ended_on = (
            parse_datetime(client_ended_on_raw)
            if isinstance(client_ended_on_raw, str) else None
        )

        client_fatigue_raw = payload.get('client_fatigue') if payload else None
        client_fatigue = (
            float(client_fatigue_raw)
            if isinstance(client_fatigue_raw, (int, float)) else None
        )
        client_recharge_raw = payload.get('client_recharge') if payload else None
        client_recharge = (
            float(client_recharge_raw)
            if isinstance(client_recharge_raw, (int, float)) else None
        )

        energy_delta = None
        if isinstance(client_energy, (int, float)):
            energy_delta = client_energy - debug['new_energy']

        phantom_steps = debug['new_steps'] - debug['pending_total_steps_in_window']

        await self._write_sync_sample(
            trigger=trigger,
            client_energy=client_energy,
            client_surplus=client_surplus,
            client_multiplier=client_multiplier,
            client_computed_at=client_computed_at,
            client_steps=int(client_steps) if client_steps is not None else None,
            client_distance=float(client_distance) if client_distance is not None else None,
            client_started_on=client_started_on,
            client_ended_on=client_ended_on,
            client_fatigue=client_fatigue,
            client_recharge=client_recharge,
            debug=debug,
            energy_delta=energy_delta,
            phantom_steps=phantom_steps,
            total_steps_all_time=self.total_steps_all_time,
        )



    # @database_sync_to_async marks this sync ORM call safe to use inside the
    # async consumer. The wrapper runs the function in a worker thread and
    # gives back a coroutine (hence the `await` at the call site).
    #   - Without wrapper: ORM runs in the event-loop thread -> blocks everything.
    #   - With wrapper: ORM runs in a worker thread -> event loop keeps serving
    #     other connections while your coroutine sleeps.
    @database_sync_to_async
    def _get_active_live_sesh_partner_id(self):
        from users.models import UserFriendCurrentLiveSesh, BadRainbowzUser                                                                                                                                                                                                                                         
        from friends.models import Friend
        sesh = (                                                                                                                                                                                                                                                                                                    
            UserFriendCurrentLiveSesh.objects
            .filter(user_id=self.user.id, expires_at__gt=timezone.now())
            .select_related('friend')
            .only(
                'other_user_id', 'is_host', 'friend_id',
                'friend__theme_color_light', 'friend__theme_color_dark',
            )
            .first()
        )
        if not sesh:
            self.is_host = False
            self.sesh_friend_id = None
            self.partner_username = None
            self.partner_friend_id = None
            self.partner_friend_name = None
            self.friend_light_color = None
            self.friend_dark_color = None
            self.gecko_play_mode = None
            return None
        self.is_host = sesh.is_host
        self.sesh_friend_id = sesh.friend_id
        self.gecko_play_mode = sesh.gecko_play_mode # model ensures will always default to a valid option
        if sesh.friend is not None:
            self.friend_light_color = sesh.friend.theme_color_light
            self.friend_dark_color = sesh.friend.theme_color_dark
        else:
            self.friend_light_color = None
            self.friend_dark_color = None
        # Partner display data (username + the user's Friend record that
        # represents the partner). Resolved here so join_live_sesh_ok can
        # ship it in one payload — but this could also be looked up on the
        # FE from existing user/friend HTTP endpoints using partner_id.
        # Doing it here trades two cheap indexed queries for zero extra
        # round-trips on the FE.
        self.partner_username = (
            BadRainbowzUser.objects.filter(id=sesh.other_user_id)
            .values_list('username', flat=True)
            .first()
        )
        friend_record = (
            Friend.objects
            .filter(user_id=self.user.id, linked_user_id=sesh.other_user_id)
            .values('id', 'name')
            .first()
        )
        if friend_record:
            self.partner_friend_id = friend_record['id']
            self.partner_friend_name = friend_record['name']
        else:
            self.partner_friend_id = None
            self.partner_friend_name = None
        return sesh.other_user_id

 

    @database_sync_to_async
    def _compute_capsule_matches_db(self, guest_user_id, host_user_id):
        from friends.models import Friend, ThoughtCapsulez

        guest_friend = Friend.objects.filter(
            user_id=guest_user_id,
            linked_user_id=host_user_id,
        ).only('id').first()
        if not guest_friend:
            return {'is_linked': False, 'friend_id': None, 'matches': []}

        host_friend = Friend.objects.filter(
            user_id=host_user_id,
            linked_user_id=guest_user_id,
        ).only('id').first()
        if not host_friend:
            return {'is_linked': False, 'friend_id': guest_friend.id, 'matches': []}

        guest_caps = ThoughtCapsulez.objects.filter(
            user_id=guest_user_id,
            friend_id=guest_friend.id,
            match_only=True,
        ).values('id', 'gecko_game_type')

        host_caps = ThoughtCapsulez.objects.filter(
            user_id=host_user_id,
            friend_id=host_friend.id,
            match_only=True,
        ).values('id', 'gecko_game_type')

        guest_by_type = {}
        for c in guest_caps:
            guest_by_type.setdefault(c['gecko_game_type'], []).append(str(c['id']))

        host_by_type = {}
        for c in host_caps:
            host_by_type.setdefault(c['gecko_game_type'], []).append(str(c['id']))

        matches = []
        for game_type, guest_ids in guest_by_type.items():
            host_ids = host_by_type.get(game_type)
            if not host_ids:
                continue
            matches.append({
                'gecko_game_type': game_type,
                'guest_capsule_ids': guest_ids,
                'host_capsule_ids': host_ids,
            })

        return {'is_linked': True, 'friend_id': guest_friend.id, 'matches': matches}

    async def _check_host_link_and_load(self, partner_user_id):
        if getattr(self, 'is_host', False):
            guest_user_id = partner_user_id
            host_user_id = self.user.id
        else:
            guest_user_id = self.user.id
            host_user_id = partner_user_id

        result = await self._compute_capsule_matches_db(guest_user_id, host_user_id)
        self.host_is_linked = result['is_linked']
        self.host_linked_friend_id = result['friend_id']
        self.capsule_matches = result['matches']
        self.capsule_matches_loaded = True

        logger.info(
            f'[host_link_check] user={self.user.id} partner={partner_user_id} '
            f'is_linked={self.host_is_linked} friend_id={self.host_linked_friend_id} '
            f'matches={len(self.capsule_matches)}'
        )

        target_group = (
            getattr(self, 'joined_sesh_group', None)
            or self.shared_with_friend_group_name
        )
        await self.channel_layer.group_send(
            target_group,
            {
                'type': 'capsule_matches_ready',
                'is_linked': self.host_is_linked,
                'host_user_id': host_user_id,
                'guest_user_id': guest_user_id,
                'friend_id': self.host_linked_friend_id,
                'matches': self.capsule_matches,
            },
        )

    async def gecko_win_proposed(self, event):
        await self.send(text_data=json.dumps({
            'action': 'gecko_win_proposed',
            'data': {
                'sender_user_id': event.get('sender_user_id'),
                'gecko_game_type': event.get('gecko_game_type'),
                'pending_id': event.get('pending_id'),
                'my_capsule_id': event.get('my_capsule_id'),
                'partner_capsule_id': event.get('partner_capsule_id'),
            },
        }))

    async def propose_gecko_match_win_ok(self, event):
        await self.send(text_data=json.dumps({
            'action': 'propose_gecko_match_win_ok',
            'data': {
                'pending_id': event.get('pending_id'),
                'other_user_id': event.get('other_user_id'),
                'gecko_game_type': event.get('gecko_game_type'),
                'capsule_id': event.get('capsule_id'),
            },
        }))

    async def gecko_win_match_pending_accept_partner(self, event):
        await self.send(text_data=json.dumps({
            'action': 'gecko_win_match_pending_accept_partner',
            'data': {
                'pending_id': event.get('pending_id'),
                'accepted_by_user_id': event.get('accepted_by_user_id'),
            },
        }))

    async def gecko_win_match_finalized(self, event):
        await self.send(text_data=json.dumps({
            'action': 'gecko_win_match_finalized',
            'data': {
                'pending_id': event.get('pending_id'),
                'partner_user_id': event.get('partner_user_id'),
            },
        }))
 
     
        
    @database_sync_to_async
    def _propose_gecko_match_win_db(self, my_capsule_id, partner_capsule_id, partner_user_id):
        from friends.models import ThoughtCapsulez, GeckoGameType
        from users.models import GeckoGameMatchWinPending, BadRainbowzUser

        my_capsule = (
            ThoughtCapsulez.objects
            .filter(id=my_capsule_id, user_id=self.user.id)
            .first()
        )
        if my_capsule is None:
            return {'ok': False, 'reason': 'my_capsule_not_found_or_not_owner'}

        partner_capsule = (
            ThoughtCapsulez.objects
            .filter(id=partner_capsule_id, user_id=partner_user_id)
            .first()
        )
        if partner_capsule is None:
            return {'ok': False, 'reason': 'partner_capsule_not_found_or_not_owner'}

        partner_user = BadRainbowzUser.objects.filter(id=partner_user_id).first()
        if partner_user is None:
            return {'ok': False, 'reason': 'partner_not_found'}

        gecko_game_type = my_capsule.gecko_game_type
        label = GeckoGameType(gecko_game_type).label

        if getattr(self, 'is_host', False):
            host_user = self.user
            guest_user = partner_user
            host_capsule = my_capsule
            guest_capsule = partner_capsule
        else:
            host_user = partner_user
            guest_user = self.user
            host_capsule = partner_capsule
            guest_capsule = my_capsule

        pending = GeckoGameMatchWinPending.propose(
            initiator=self.user,
            host=host_user,
            guest=guest_user,
            host_capsule=host_capsule,
            guest_capsule=guest_capsule,
            gecko_game_type=gecko_game_type,
            gecko_game_type_label=label,
        )

        return {
            'ok': True,
            'pending_id': pending.id,
            'gecko_game_type': gecko_game_type,
            'gecko_game_type_label': label,
        }

    @database_sync_to_async
    def _propose_gecko_win_db(self, capsule_id, partner_user_id):
        from friends.models import ThoughtCapsulez, GeckoGameType
        from users.models import GeckoGameWinPending, BadRainbowzUser

        capsule = (
            ThoughtCapsulez.objects
            .filter(id=capsule_id, user_id=self.user.id)
            .first()
        )
        if capsule is None:
            return {'ok': False, 'reason': 'capsule_not_found_or_not_owner'}

        target_user = BadRainbowzUser.objects.filter(id=partner_user_id).first()
        if target_user is None:
            return {'ok': False, 'reason': 'partner_not_found'}
        
        # in future might allow host to decide if they want to match this
        if capsule.match_only:
            return {'ok': False, 'reason': 'capsule_is_match_only'}

        gecko_game_type = capsule.gecko_game_type
        gecko_game_type_label = GeckoGameType(gecko_game_type).label

        GeckoGameWinPending.propose(
            target_user=target_user,
            sender=self.user,
            sender_capsule=capsule,
            gecko_game_type=gecko_game_type,
            gecko_game_type_label=gecko_game_type_label,
        )

        return {
            'ok': True,
            'gecko_game_type': gecko_game_type,
            'gecko_game_type_label': gecko_game_type_label,
        }

    # @database_sync_to_async
    # def _propose_gecko_win_db(self, capsule_id, partner_user_id):
    #     from friends.models import ThoughtCapsulez
    #     from users.models import GeckoGameWinPending, BadRainbowzUser

    #     capsule = (
    #         ThoughtCapsulez.objects
    #         .filter(id=capsule_id, user_id=self.user.id)
    #         .first()
    #     )
    #     if capsule is None:
    #         return {'ok': False, 'reason': 'capsule_not_found_or_not_owner'}

    #     target_user = BadRainbowzUser.objects.filter(id=partner_user_id).first()
    #     if target_user is None:
    #         return {'ok': False, 'reason': 'partner_not_found'}

    #     pending = GeckoGameWinPending.propose(
    #         target_user=target_user,
    #         sender=self.user,
    #         sender_capsule=capsule,
    #     )
    #     return {'ok': True, 
    #             # 'pending_id': pending.id
    #             }

    async def gecko_win_accepted(self, event):
        await self.send(text_data=json.dumps({
            'action': 'gecko_win_accepted',
            'data': {
                'pending_id': event.get('pending_id'),
                'accepted_by_user_id': event.get('accepted_by_user_id'),
                'deleted_capsule_id': event.get('deleted_capsule_id'),
                'source': event.get('source'),
            },
        }))


    async def gecko_win_declined(self, event):
        await self.send(text_data=json.dumps({
            'action': 'gecko_win_declined',
            'data': {
                'pending_id': event.get('pending_id'),
                'declined_by_user_id': event.get('declined_by_user_id'),
                'source': event.get('source'),
            },
        }))




    async def match_request_result(self, event):
        await self.send(text_data=json.dumps({
            'action': 'match_request_result',
            'data': {
                'requested_by_user_id': event['requested_by_user_id'],
                'gecko_game_type': event['gecko_game_type'],
                'guest_capsule_id': event['guest_capsule_id'],
                'host_capsule_id': event['host_capsule_id'],
            },
        }))

    async def capsule_matches_ready(self, event):
        await self.send(text_data=json.dumps({
            'action': 'capsule_matches_ready',
            'data': {
                'completed': True,
                'is_linked': event['is_linked'],
                'host_user_id': event['host_user_id'],
                'guest_user_id': event['guest_user_id'],
                'friend_id': event['friend_id'],
                'matches': event['matches'],
            },
        }))

    @database_sync_to_async
    def _write_sync_sample(
        self, *, trigger, client_energy, client_surplus, client_multiplier,
        client_computed_at, client_steps, client_distance,
        client_started_on, client_ended_on,
        client_fatigue, client_recharge,
        debug, energy_delta, phantom_steps, total_steps_all_time,
    ):
        from users.models import GeckoEnergySyncSample
        GeckoEnergySyncSample.objects.create(
            user=self.user,
            trigger=trigger,
            client_energy=client_energy,
            client_surplus=client_surplus,
            client_multiplier=client_multiplier,
            client_computed_at=client_computed_at,
            client_steps_in_payload=client_steps,
            client_distance_in_payload=client_distance,
            client_started_on=client_started_on,
            client_ended_on=client_ended_on,
            client_fatigue=client_fatigue,
            client_recharge=client_recharge,
            server_energy_before=debug['prev_energy'],
            server_energy_after=debug['new_energy'],
            server_surplus_before=debug['prev_surplus'],
            server_surplus_after=debug['new_surplus'],
            server_updated_at_before=debug['prev_updated_at'],
            server_updated_at_after=debug['new_updated_at'],
            recompute_window_seconds=debug['window_seconds'],
            recompute_active_seconds=debug['active_seconds'],
            recompute_new_steps=debug['new_steps'],
            recompute_fatigue=debug['fatigue'],
            recompute_recharge=debug['recharge'],
            recompute_net=debug['net'],
            pending_entries_count=debug['pending_entries_count'],
            pending_entries_in_window=debug['pending_entries_in_window'],
            pending_entries_stale=debug['pending_entries_stale'],
            pending_total_steps_all=debug['pending_total_steps_all'],
            pending_total_steps_in_window=debug['pending_total_steps_in_window'],
            energy_delta=energy_delta,
            phantom_steps=phantom_steps,
            multiplier_active=debug['multiplier_active'],
            streak_expires_at=debug['streak_expires_at'],
            total_steps_all_time=total_steps_all_time,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize_score_state(self):
        ss = self.score_state
        max_active_hours = ss.get('max_active_hours', 16)
        full_rest_hours = 24 - max_active_hours
        recharge_per_second = 1.0 / (full_rest_hours * 3600)

        def _fmt_dt(val):
            if val is None:
                return None
            if isinstance(val, str):
                return val
            return val.isoformat()

        return {
            'user': self.user.id,
            'total_steps_all_time': self.total_steps_all_time,
            'multiplier': ss['multiplier'],
            'expires_at': _fmt_dt(ss['expires_at']),
            'updated_on': _fmt_dt(ss.get('updated_on')),
            'base_multiplier': ss['base_multiplier'],
            'energy': ss['energy'],
            'surplus_energy': ss['surplus_energy'],
            'energy_updated_at': _fmt_dt(ss['energy_updated_at']),
            'revives_at': _fmt_dt(ss['revives_at']),
            'recharge_per_second': recharge_per_second,
            'streak_recharge_per_second': recharge_per_second * 0.5,
            'step_fatigue_per_step': constants.STEP_FATIGUE_PER_STEP,
            'streak_fatigue_multiplier': constants.STREAK_FATIGUE_MULTIPLIER,
            'surplus_cap': constants.SURPLUS_CAP,
            'personality_type': ss.get('personality_type'),
            'personality_type_label': ss.get('personality_type_label'),
            'memory_type': ss.get('memory_type'),
            'memory_type_label': ss.get('memory_type_label'),
            'active_hours_type': ss.get('active_hours_type'),
            'active_hours_type_label': ss.get('active_hours_type_label'),
            'story_type': ss.get('story_type'),
            'story_type_label': ss.get('story_type_label'),
            'stamina': ss.get('stamina', 1.0),
            'max_active_hours': max_active_hours,
            'max_duration_till_revival': ss.get('max_duration_till_revival', 60),
            'max_score_multiplier': ss.get('max_score_multiplier', 3),
            'max_streak_length_seconds': ss.get('max_streak_length_seconds', 10),
            'active_hours': ss.get('active_hours', []),
            'gecko_created_on': _fmt_dt(ss.get('gecko_created_on')),
        }

    # ------------------------------------------------------------------
    # DB operations
    # ------------------------------------------------------------------

    @database_sync_to_async
    def _load_initial_state(self):
        from users.models import GeckoScoreState, GeckoCombinedData
        from geckoscripts.models import ScoreRule

        obj, _ = GeckoScoreState.objects.get_or_create(user=self.user)
        obj.recompute_energy()

        combined, _ = GeckoCombinedData.objects.get_or_create(user=self.user)
        total_steps_all_time = combined.total_steps

        score_state = {
            'multiplier': obj.multiplier,
            'base_multiplier': obj.base_multiplier,
            'expires_at': obj.expires_at,
            'energy': obj.energy,
            'surplus_energy': obj.surplus_energy,
            'energy_updated_at': obj.energy_updated_at,
            'revives_at': obj.revives_at,
            'updated_on': obj.updated_on,
            'personality_type': obj.personality_type,
            'personality_type_label': obj.get_personality_type_display(),
            'memory_type': obj.memory_type,
            'memory_type_label': obj.get_memory_type_display(),
            'active_hours_type': obj.active_hours_type,
            'active_hours_type_label': obj.get_active_hours_type_display(),
            'story_type': obj.story_type,
            'story_type_label': obj.get_story_type_display(),
            'stamina': obj.stamina,
            'max_active_hours': obj.max_active_hours,
            'max_duration_till_revival': obj.max_duration_till_revival,
            'max_score_multiplier': obj.max_score_multiplier,
            'max_streak_length_seconds': obj.max_streak_length_seconds,
            'active_hours': obj.active_hours,
            'gecko_created_on': obj.gecko_created_on,
        }

        rules = {
            r.code: {
                'code': r.code,
                'label': r.label,
                'points': r.points,
            }
            for r in ScoreRule.objects.filter(version=1)
        }

        return {
            'score_state': score_state,
            'score_rules': rules,
            'total_steps_all_time': total_steps_all_time,
        }

    @database_sync_to_async
    def _flush_to_db(self):
        from users.gecko_helpers import process_gecko_data
        from users.models import GeckoScoreState

        logger.info(f'[flush_db] user={self.user.id} entries={len(self.pending_data)}')

        for entry in self.pending_data:
            process_gecko_data(
                user=self.user,
                friend_id=entry['friend_id'],
                steps=entry['steps'],
                distance=entry['distance'],
                started_on=entry['started_on'],
                ended_on=entry['ended_on'],
                points_earned_list=entry.get('points_earned', []),
                points_pre_resolved=True,
            )

        ss = self.score_state
        obj, _ = GeckoScoreState.objects.get_or_create(user=self.user)

        obj.multiplier = ss['multiplier']
        obj.expires_at = ss['expires_at']
        obj.energy = ss['energy']
        obj.surplus_energy = ss['surplus_energy']
        obj.energy_updated_at = ss['energy_updated_at']
        obj.revives_at = ss['revives_at']

        obj.save(update_fields=[
            'multiplier',
            'expires_at',
            'energy',
            'surplus_energy',
            'energy_updated_at',
            'revives_at',
        ])

        self.pending_data.clear()

        logger.info(f'[flush_db] complete user={self.user.id}')












 