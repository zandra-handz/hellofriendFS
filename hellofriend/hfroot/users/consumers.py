# import json
# from channels.generic.websocket import AsyncWebSocketConsumer
# from channels.db import database_sync_to_async
#
#
# class GeckoEnergyConsumer(AsyncWebSocketConsumer):
#     async def connect(self):
#         self.user_id = self.scope['url_route']['kwargs']['user_id']
#         self.room_group_name = f'gecko_energy_{self.user_id}'
#
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name,
#         )
#         await self.accept()
#
#     async def disconnect(self, close_code):
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name,
#         )
#
#     async def receive(self, text_data):
#         data = json.loads(text_data)
#         action = data.get('action')
#
#         if action == 'revive':
#             # Handle revive action
#             pass
#
#     async def energy_update(self, event):
#         """Called when energy state changes — pushes to client."""
#         await self.send(text_data=json.dumps(event['data']))
