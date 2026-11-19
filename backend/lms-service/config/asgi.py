"""
ASGI config for CampusOS LMS service.
Integrates Django HTTP handling with Django Channels WebSockets and JWT Authentication.
"""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir / "apps"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django ASGI application early to ensure the AppRegistry is populated
# before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.notifications.middleware import JwtAuthMiddlewareStack
import apps.notifications.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddlewareStack(
        URLRouter(apps.notifications.routing.websocket_urlpatterns)
    ),
})
