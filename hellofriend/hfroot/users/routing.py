from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/gecko-energy/$', consumers.GeckoEnergyConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.NotificationsConsumer.as_asgi()),
]
