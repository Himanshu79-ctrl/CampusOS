"""
WebSocket consumers for real-time notifications in CampusOS LMS.
"""

import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer handling personal real-time notification streams.
    Secured by user-specific group channels (user_<user_id>).
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            # Unauthorized connection attempt: close with code 4001 (Unauthorized)
            logger.warning(
                "WebSocket connection rejected: Unauthenticated client (error: %s)",
                self.scope.get("auth_error"),
            )
            await self.close(code=4001)
            return

        self.user_id = str(user.user_id)
        self.user_group = f"user_{self.user_id}"

        # Join personal user channel group
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

        logger.info("WebSocket connected: user %s to group %s", self.user_id, self.user_group)

        # Send initial confirmation payload
        await self.send_json({
            "type": "connection_established",
            "user_id": self.user_id,
            "message": f"Connected to real-time notification stream for user {self.user_id}",
        })

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
            logger.info("WebSocket disconnected: user %s (code %s)", self.user_id, close_code)

    async def receive_json(self, content):
        """
        Handle incoming messages from client.
        Supports heartbeat 'ping', while preventing arbitrary group subscriptions.
        """
        msg_type = content.get("type")
        if msg_type == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self.send_json({
                "type": "ack",
                "received": msg_type,
            })

    async def notification_message(self, event):
        """
        Handler for real-time notifications dispatched to the user group.
        """
        await self.send_json({
            "type": "notification",
            "data": event.get("notification", {}),
        })

    async def announcement_message(self, event):
        """
        Handler for real-time announcements broadcast to the user group.
        """
        await self.send_json({
            "type": "announcement",
            "data": event.get("announcement", {}),
        })

