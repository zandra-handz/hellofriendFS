"""
ASGI config for hfroot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hfroot.settings')

application = get_asgi_application()

# --- WebSocket routing (uncomment when ready) ---
from channels.routing import ProtocolTypeRouter, URLRouter
from users.middleware import JWTAuthMiddleware
import users.routing

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': JWTAuthMiddleware(
        URLRouter(
            users.routing.websocket_urlpatterns
        )
    ),
})
