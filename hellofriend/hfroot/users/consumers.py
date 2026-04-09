import json
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from users import constants


class GeckoEnergyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
            return

        self.user = user
        self.room_group_name = f'gecko_energy_{self.user.id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )
        await self.accept()

        # Load DB state into memory once
        init = await self._load_initial_state()
        self.score_state = init['score_state']
        self.score_rules = init['score_rules']
        self.pending_data = []
        self.pending_points = []

        # Recompute with current time before sending
        self._recompute_energy_in_memory()

        await self.send(text_data=json.dumps({
            'action': 'score_state',
            'data': self._serialize_score_state(),
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'pending_data') and (self.pending_data or self.pending_points):
            await self._flush_to_db()

        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'get_score_state':
            self._recompute_energy_in_memory()
            await self.send(text_data=json.dumps({
                'action': 'score_state',
                'data': self._serialize_score_state(),
            }))

        elif action == 'update_gecko_data':
            payload = data.get('data', {})
            self._handle_update_in_memory(payload)
            await self.send(text_data=json.dumps({
                'action': 'score_state',
                'data': self._serialize_score_state(),
            }))

        elif action == 'flush':
            if self.pending_data or self.pending_points:
                await self._flush_to_db()
                await self.send(text_data=json.dumps({
                    'action': 'flush_ack',
                    'data': {'status': 'ok'},
                }))
            else:
                await self.send(text_data=json.dumps({
                    'action': 'flush_ack',
                    'data': {'status': 'nothing_to_flush'},
                }))

    async def energy_update(self, event):
        """Called when energy state changes — pushes to client."""
        await self.send(text_data=json.dumps(event['data']))

    # ------------------------------------------------------------------
    # In-memory energy recomputation
    # ------------------------------------------------------------------

    def _recompute_energy_in_memory(self):
        """Pure-Python recompute_energy operating on self.score_state dict."""
        ss = self.score_state
        now = timezone.now()
        energy_updated_at = ss['energy_updated_at']
        elapsed = (now - energy_updated_at).total_seconds()
        if elapsed <= 0:
            return

        revival_seconds = ss.get('max_duration_till_revival', 60)

        energy = ss['energy']
        surplus_energy = ss['surplus_energy']
        revives_at = ss['revives_at']

        # Dead state
        if energy <= 0.0 and surplus_energy <= 0.0:
            if revives_at and now >= revives_at:
                ss['energy'] = 0.05
                ss['revives_at'] = None
            elif not revives_at:
                ss['revives_at'] = now + datetime.timedelta(seconds=revival_seconds)
            ss['energy_updated_at'] = now
            return

        stamina = ss.get('stamina', 1.0)
        max_active_hours = ss.get('max_active_hours', 16)
        full_rest_hours = 24 - max_active_hours
        recharge_per_second = 1.0 / (full_rest_hours * 3600)
        streak_recharge_per_second = recharge_per_second * 0.5

        # Gather in-memory sessions that overlap this window
        new_steps = 0
        active_seconds = 0
        for entry in self.pending_data:
            started = entry.get('_started_dt')
            ended = entry.get('_ended_dt')
            if started and ended and ended > energy_updated_at:
                active_seconds += max(0, (ended - started).total_seconds())
            new_steps += entry.get('steps', 0)

        rest_seconds = max(0, elapsed - active_seconds)

        multiplier = ss['multiplier']
        base_multiplier = ss['base_multiplier']
        expires_at = ss['expires_at']

        streak_is_active = (
            multiplier > base_multiplier
            and expires_at > energy_updated_at
        )

        if streak_is_active and active_seconds > 0:
            streak_end = min(expires_at, now)
            streak_seconds = max(0, (streak_end - energy_updated_at).total_seconds())
            streak_ratio = min(1.0, streak_seconds / elapsed)

            streak_active_seconds = active_seconds * streak_ratio
            streak_steps = new_steps * (streak_active_seconds / active_seconds) if active_seconds else 0
            normal_steps = new_steps - streak_steps

            fatigue = (
                (normal_steps * constants.STEP_FATIGUE_PER_STEP)
                + (streak_steps * constants.STEP_FATIGUE_PER_STEP * constants.STREAK_FATIGUE_MULTIPLIER)
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

        if energy <= 0.0 and surplus_energy <= 0.0:
            if not revives_at:
                revives_at = now + datetime.timedelta(seconds=revival_seconds)
        else:
            revives_at = None

        ss['energy'] = energy
        ss['surplus_energy'] = surplus_energy
        ss['energy_updated_at'] = now
        ss['revives_at'] = revives_at

    # ------------------------------------------------------------------
    # In-memory update handler
    # ------------------------------------------------------------------

    def _handle_update_in_memory(self, payload):
        """Process an update_gecko_data payload entirely in memory."""
        ss = self.score_state

        delta_steps = int(payload.get('steps') or 0)
        delta_distance = int(payload.get('distance') or 0)
        started_on = payload.get('started_on')
        ended_on = payload.get('ended_on')
        points_earned_list = payload.get('points_earned')
        if not isinstance(points_earned_list, list):
            points_earned_list = []

        # Parse datetimes
        started_dt = parse_datetime(started_on) if isinstance(started_on, str) else started_on
        ended_dt = parse_datetime(ended_on) if isinstance(ended_on, str) else ended_on

        # Resolve points against cached ScoreRules
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
            ts = parse_datetime(ts_raw) if ts_raw else None
            if ts is None:
                ts = timezone.now()

            if streak_expires_at and ts < streak_expires_at:
                applied_multiplier = active_multiplier
            else:
                applied_multiplier = base_multiplier

            resolved_points.append({
                'amount': rule['points'] * applied_multiplier,
                'reason': rule['label'],
                'code': rule['code'],
                'multiplier': applied_multiplier,
                'timestamp_earned': ts_raw,
            })

        total_points = sum(e['amount'] for e in resolved_points)

        # Accumulate pending data for flush
        self.pending_data.append({
            'friend_id': payload.get('friend_id'),
            'steps': delta_steps,
            'distance': delta_distance,
            'started_on': started_on,
            'ended_on': ended_on,
            'total_points': total_points,
            '_started_dt': started_dt,
            '_ended_dt': ended_dt,
        })
        if resolved_points:
            for rp in resolved_points:
                rp['friend_id'] = payload.get('friend_id')
                rp['started_on'] = started_on
                rp['ended_on'] = ended_on
            self.pending_points.extend(resolved_points)

        # Apply streak/multiplier update if provided
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
    # Serialization (from in-memory dict, no DB)
    # ------------------------------------------------------------------

    def _serialize_score_state(self):
        """Build the same shape as GeckoScoreStateSerializer from the in-memory dict."""
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
    # DB operations (connect + flush only)
    # ------------------------------------------------------------------

    @database_sync_to_async
    def _load_initial_state(self):
        from users.models import GeckoScoreState
        from geckoscripts.models import ScoreRule

        obj, _ = GeckoScoreState.objects.get_or_create(user=self.user)
        obj.recompute_energy()

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
            r.code: {'code': r.code, 'label': r.label, 'points': r.points}
            for r in ScoreRule.objects.filter(version=1)
        }

        return {'score_state': score_state, 'score_rules': rules}

    @database_sync_to_async
    def _flush_to_db(self):
        from users.gecko_helpers import process_gecko_data
        from users.models import GeckoScoreState

        # Flush each pending activity entry
        for entry in self.pending_data:
            # Find the points that belong to this entry
            entry_points = [
                p for p in self.pending_points
                if p.get('friend_id') == entry['friend_id']
                and p.get('started_on') == entry['started_on']
                and p.get('ended_on') == entry['ended_on']
            ]
            process_gecko_data(
                user=self.user,
                friend_id=entry['friend_id'],
                steps=entry['steps'],
                distance=entry['distance'],
                started_on=entry['started_on'],
                ended_on=entry['ended_on'],
                points_earned_list=entry_points,
                points_pre_resolved=True,
            )

        # Sync in-memory score state back to DB
        ss = self.score_state
        obj, _ = GeckoScoreState.objects.get_or_create(user=self.user)
        obj.multiplier = ss['multiplier']
        obj.expires_at = ss['expires_at']
        obj.energy = ss['energy']
        obj.surplus_energy = ss['surplus_energy']
        obj.energy_updated_at = ss['energy_updated_at']
        obj.revives_at = ss['revives_at']
        obj.save(update_fields=[
            'multiplier', 'expires_at', 'energy',
            'surplus_energy', 'energy_updated_at', 'revives_at',
        ])

        self.pending_data.clear()
        self.pending_points.clear()
