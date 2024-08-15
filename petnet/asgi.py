"""
ASGI config for petnet project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import chat.routing
from channels.auth import AuthMiddlewareStack
import notifications.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'petnet.settings')
# when a connection request comes in. If it is a websocket, it will be passed to AuthMiddllewareStack
# AuthMiddlewareStack handles authentication
# the request then goes to URLRouter, which uses the pattern defined in chat.routing.websocket_urlpatterns
# If the URL matches our pattern, the ChatConsumer is instantiated to handle the connection

application = ProtocolTypeRouter({
    'http':get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns+
            notifications.routing.websocket_urlpatterns
        )
    ),
})
