"""
Helper for pushing real-time notifications to a user's websocket channel
(see NotificationsConsumer in users/notifications_consumer.py).
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notify_user(user_id, event_type, payload=None):
    """
    Send a notification event to a specific user's notifications group.

    event_type must match a handler method on NotificationsConsumer
    (e.g. 'live_sesh_invite', 'live_sesh_invite_accepted', 'live_sesh_ended').
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {
            'type': event_type,
            'data': payload or {},
        },
    )
