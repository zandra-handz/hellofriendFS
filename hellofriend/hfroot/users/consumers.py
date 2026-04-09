import json
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


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

        # Send initial state on connect
        state = await self.get_score_state()
        await self.send(text_data=json.dumps({
            'action': 'score_state',
            'data': state,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'get_score_state':
            state = await self.get_score_state()
            await self.send(text_data=json.dumps({
                'action': 'score_state',
                'data': state,
            }))

        elif action == 'update_gecko_data':
            payload = data.get('data', {})
            result = await self.handle_update_gecko_data(payload)
            await self.send(text_data=json.dumps({
                'action': 'score_state',
                'data': result,
            }))

    async def energy_update(self, event):
        """Called when energy state changes — pushes to client."""
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def handle_update_gecko_data(self, payload):
        from users.gecko_helpers import process_gecko_data
        from users.models import GeckoScoreState
        from users.serializers import GeckoScoreStateSerializer

        # 1. Record activity data (steps, distance, sessions, points)
        process_gecko_data(
            user=self.user,
            friend_id=payload.get('friend_id'),
            steps=payload.get('steps'),
            distance=payload.get('distance'),
            started_on=payload.get('started_on'),
            ended_on=payload.get('ended_on'),
            points_earned_list=payload.get('points_earned'),
        )

        # 2. Recompute energy with fresh session data
        obj, _ = GeckoScoreState.objects.get_or_create(user=self.user)
        obj.recompute_energy()

        # 3. Apply streak/multiplier update if provided
        score_fields = payload.get('score_state')
        if score_fields and isinstance(score_fields, dict):
            if not (obj.expires_at and obj.expires_at > timezone.now()):
                max_multiplier = obj.max_score_multiplier or 1
                max_streak_seconds = obj.max_streak_length_seconds or 60

                data = dict(score_fields)
                if 'multiplier' in data:
                    try:
                        requested = int(data['multiplier'])
                    except (TypeError, ValueError):
                        return GeckoScoreStateSerializer(obj).data
                    if requested > max_multiplier:
                        data['multiplier'] = max_multiplier

                requested_length = data.pop('expiration_length', None)
                length_seconds = max_streak_seconds
                if requested_length is not None:
                    try:
                        parsed = int(requested_length)
                        if 0 < parsed <= max_streak_seconds:
                            length_seconds = parsed
                    except (TypeError, ValueError):
                        pass
                data['expires_at'] = timezone.now() + datetime.timedelta(seconds=length_seconds)

                serializer = GeckoScoreStateSerializer(obj, data=data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                obj.recompute_energy()
                obj.refresh_from_db()

        return GeckoScoreStateSerializer(obj).data

    @database_sync_to_async
    def get_score_state(self):
        from users.models import GeckoScoreState
        from users.serializers import GeckoScoreStateSerializer

        obj, _ = GeckoScoreState.objects.get_or_create(user=self.user)
        obj.recompute_energy()
        return GeckoScoreStateSerializer(obj).data
