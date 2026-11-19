"""WebSocket endpoint  ws://<host>/ws/live/

Protocol (JSON messages):
  client -> {"type": "auth", "token": "<DRF token>"}     join personal / provider / admin groups
  client -> {"type": "watch", "destination": "<slug>"}   live availability for one destination
  client -> {"type": "ping"}
  server -> {"type": "hello" | "auth.ok" | "auth.error" | "watching" | "pong"
             | "reservation.status" | "reservation.new" | "availability.changed", ...}

The token is sent as the first message rather than in the URL, so it never
appears in server/proxy access logs.
"""
import os
import re

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

SLUG_RE = re.compile(r"^[a-z0-9-]{1,160}$")


@database_sync_to_async
def user_for_token(key):
    from rest_framework.authtoken.models import Token

    from accounts.permissions import role_of
    try:
        t = Token.objects.select_related("user", "user__profile").get(key=key)
    except (Token.DoesNotExist, ValueError):
        return None, None
    if not t.user.is_active:
        return None, None
    return t.user, role_of(t.user)


class LiveConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.joined = set()
        self.user = None
        self.watching = None
        await self.accept()
        await self.send_json({"type": "hello", "worker_pid": os.getpid()})

    async def _join(self, group):
        if group not in self.joined:
            await self.channel_layer.group_add(group, self.channel_name)
            self.joined.add(group)

    async def _leave(self, group):
        if group in self.joined:
            await self.channel_layer.group_discard(group, self.channel_name)
            self.joined.discard(group)

    async def receive_json(self, msg, **kwargs):
        kind = msg.get("type") if isinstance(msg, dict) else None
        if kind == "auth":
            user, role = await user_for_token(str(msg.get("token", ""))[:64])
            if not user:
                await self.send_json({"type": "auth.error", "detail": "Invalid or expired token."})
                return
            self.user = user
            await self._join(f"user_{user.id}")
            if role in ("VENUE_OPERATOR", "GUIDE", "ADMIN"):
                await self._join(f"provider_{user.id}")
            if role == "ADMIN":
                await self._join("admins")
            await self.send_json({"type": "auth.ok", "username": user.username, "role": role,
                                  "worker_pid": os.getpid()})
        elif kind == "logout":
            for g in [g for g in self.joined if not g.startswith("dest_")]:
                await self._leave(g)
            self.user = None
        elif kind == "watch":
            slug = str(msg.get("destination", ""))
            if self.watching:
                await self._leave(f"dest_{self.watching}")
                self.watching = None
            if SLUG_RE.match(slug):
                self.watching = slug
                await self._join(f"dest_{slug}")
                await self.send_json({"type": "watching", "destination": slug})
        elif kind == "ping":
            await self.send_json({"type": "pong", "worker_pid": os.getpid()})

    async def disconnect(self, code):
        for g in list(self.joined):
            await self._leave(g)

    async def push(self, event):
        """Handler for group_send(..., {"type": "push", "payload": {...}})."""
        await self.send_json({**event["payload"], "delivered_by_pid": os.getpid()})
