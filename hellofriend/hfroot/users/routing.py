from django.urls import re_path
from .consumers import GeckoEnergyConsumer
from .notifications_consumer import NotificationsConsumer

websocket_urlpatterns = [
    re_path(r'ws/gecko-energy/$', GeckoEnergyConsumer.as_asgi()),
    re_path(r'ws/notifications/$', NotificationsConsumer.as_asgi()),
]
