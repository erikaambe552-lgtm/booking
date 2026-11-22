"""ASGI entry point for HTTP (Django + DRF) and WebSockets (Channels)."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi_app = get_asgi_application()  # must load before importing consumers/models

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler  # noqa: E402
from django.conf import settings  # noqa: E402

from core.bookings.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # Only accept WebSocket handshakes from the server's own hosts or the configured
    # frontend origins (CORS_ALLOWED_ORIGINS). Prevents cross-site WebSocket hijacking.
    "websocket": OriginValidator(URLRouter(websocket_urlpatterns), settings.WS_ALLOWED_ORIGINS),
})

if settings.DEBUG:
    application = ASGIStaticFilesHandler(application)
