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

        # Parse friend_id from query string (e.g. ws://.../?friend_id=42)
        from urllib.parse import parse_qs
        qs = parse_qs((self.scope.get('query_string') or b'').decode())
        try:
            provided_friend_id = int(qs.get('friend_id', [None])[0])
        except (TypeError, ValueError):
            provided_friend_id = None

        self.user = user
        self.room_group_name = f'gecko_energy_{self.user.id}'
        self.shared_with_friend_group_name = f'gecko_shared_with_friend_{self.user.id}'
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
        if partner_id is not None and getattr(self, 'is_host', False):
            # Host must supply a friend_id matching their sesh row's friend
            if self.sesh_friend_id is None or provided_friend_id != self.sesh_friend_id:
                logger.warning(
                    f'[connect] host user={self.user.id} friend_id mismatch '
                    f'(provided={provided_friend_id}, sesh={self.sesh_friend_id}) — rejecting'
                )
                await self.close()
                return
        if partner_id is not None:
            self.joined_sesh_group = f'gecko_shared_with_friend_{partner_id}'
            await self.channel_layer.group_add(
                self.joined_sesh_group,
                self.channel_name,
            )
            logger.info(
            f'[connect] user={self.user.id} joined partner sesh group={self.joined_sesh_group}'
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
        
        if getattr(self, 'joined_sesh_group', None):
            await self.channel_layer.group_discard(
                self.joined_sesh_group,
                self.channel_name,
            )
            self.joined_sesh_group = None

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

        if action == 'get_gecko_screen_position':
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
            if old and old != new_group:
                await self.channel_layer.group_discard(old, self.channel_name)

            self.joined_sesh_group = new_group
            await self.channel_layer.group_add(new_group, self.channel_name)

            logger.info(
                f'[join_live_sesh] user={self.user.id} joined partner group={new_group}'
            )

            await self.send(text_data=json.dumps({
                'action': 'join_live_sesh_ok',
                'data': {'partner_id': partner_id},

            }))
        
        elif action == 'leave_live_sesh':
            old = getattr(self, 'joined_sesh_group', None)
            if old:
                await self.channel_layer.group_discard(old, self.channel_name)
                self.joined_sesh_group = None
                self.is_host = False
                logger.info(f'[leave_live_sesh] user={self.user.id} left group={old}')

            await self.send(text_data=json.dumps({
                'action': 'leave_live_sesh_ok',
            }))

        elif action == 'update_gecko_position':
            payload = data.get('data', {})
            pos = payload.get('position')
            # steps = payload.get('steps') or []
            # moments = payload.get('moments') or []
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
                    'position': pos,
                    # 'steps': steps,
                    # 'moments': moments
                },
            )

        elif action == 'update_host_gecko_position':
            if not getattr(self, 'is_host', False):
                logger.warning(
                    f'[update_host_gecko_position] user={self.user.id} not host — ignoring'
                )
                return
            payload = data.get('data', {}) 
            pos = payload.get('position')
            steps = payload.get('steps') or [] 
            step_angles = payload.get('step_angles') or []
            held_moments = payload.get('held_moments') or []
            moments = payload.get('moments') or []

            if not (isinstance(pos, list) and len(pos) == 2):
                logger.warning(
                    f'[update_host_gecko_position] user={self.user.id} invalid position={pos!r}'
                )
                return

            self.host_gecko_screen_position = pos
            logger.info(
                f'[update_host_gecko_position] user={self.user.id} '
                f'pos={pos} steps={steps} step_angles={step_angles} held_moments={held_moments} moments={moments}'
            )
            await self.channel_layer.group_send(
                self.shared_with_friend_group_name,
                {
                    'type': 'host_gecko_position_broadcast',
                    'from_user': self.user.id,
                    'position': pos,
                    'steps': steps,
                    'step_angles': step_angles,
                    'held_moments': held_moments,
                    'moments': moments,
                    'timestamp': payload.get('timestamp'),
                },
            )

        elif action == 'update_guest_gecko_position':
            if getattr(self, 'is_host', False):
                logger.warning(
                    f'[update_guest_gecko_position] user={self.user.id} is host — ignoring'
                )
                return
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

        elif action == 'get_score_state':
            self._recompute_energy_in_memory()
            await self._record_sync_sample('get_score_state', None)

            await self.send(text_data=json.dumps({
                'action': 'score_state',
                'data': self._serialize_score_state(),
            }))

        elif action == 'update_gecko_data':
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

    async def gecko_position_broadcast(self, event):
        await self.send(bytes_data=ormsgpack.packb({
            'action': 'gecko_coords',
            'data': {
                'from_user': event.get('from_user'),
                'position': event.get('position'),
            },
        }))

    async def host_gecko_position_broadcast(self, event):
        await self.send(bytes_data=ormsgpack.packb({
            'action': 'host_gecko_coords',
            'data': {
                'from_user': event.get('from_user'),
                'position': event.get('position'),
                'steps': event.get('steps', []),
                'step_angles': event.get('step_angles', []),
                'moments': event.get('moments', []),
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
            'friend_id': payload.get('friend_id'),
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
        from users.models import UserFriendCurrentLiveSesh
        sesh = UserFriendCurrentLiveSesh.objects.filter(
            user_id=self.user.id,
            expires_at__gt=timezone.now(),
        ).only('other_user_id', 'is_host', 'friend_id').first()
        if not sesh:
            self.is_host = False
            self.sesh_friend_id = None
            return None
        self.is_host = sesh.is_host
        self.sesh_friend_id = sesh.friend_id
        return sesh.other_user_id

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


class NotificationsConsumer(AsyncWebsocketConsumer):
    """
    Lightweight per-user channel for real-time notifications
    (live sesh invites, accepts, session end, etc). Does not load
    any heavy state on connect — pure fan-out.
    """

    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            logger.warning('[notifications connect] anonymous user rejected')
            await self.close()
            return

        self.user = user
        self.group_name = f'notifications_{self.user.id}'
        logger.info(f'[notifications connect] user={self.user.id} group={self.group_name}')

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        logger.info(
            f'[notifications disconnect] user={getattr(self, "user", None)} code={close_code}'
        )
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # --- event handlers (invoked via channel_layer.group_send with matching type) ---

    async def live_sesh_invite(self, event):
        await self.send(text_data=json.dumps({
            'action': 'live_sesh_invite',
            'data': event.get('data', {}),
        }))

    async def live_sesh_invite_accepted(self, event):
        await self.send(text_data=json.dumps({
            'action': 'live_sesh_invite_accepted',
            'data': event.get('data', {}),
        }))

    async def live_sesh_ended(self, event):
        await self.send(text_data=json.dumps({
            'action': 'live_sesh_ended',
            'data': event.get('data', {}),
        }))