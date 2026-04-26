import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger('gecko.ws')


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
