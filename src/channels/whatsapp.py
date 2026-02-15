"""
WhatsApp channel for Gulama.

Uses the WhatsApp Business API (Cloud API) for integration.
Supports text messages, media, and interactive buttons.

Requires:
- WhatsApp Business API access
- Meta Developer account
- Webhook URL for receiving messages
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from typing import Any

import httpx

from src.channels.base import BaseChannel
from src.utils.logging import get_logger

logger = get_logger("whatsapp_channel")

WHATSAPP_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppChannel(BaseChannel):
    """
    WhatsApp Business API channel.

    Configuration required:
    - WHATSAPP_PHONE_NUMBER_ID: Your phone number ID from Meta
    - WHATSAPP_ACCESS_TOKEN: Permanent access token
    - WHATSAPP_VERIFY_TOKEN: Webhook verification token
    - WHATSAPP_APP_SECRET: App secret for signature verification
    - WHATSAPP_ALLOWED_NUMBERS: Comma-separated allowed phone numbers
    """

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        verify_token: str,
        app_secret: str | None = None,
        allowed_numbers: list[str] | None = None,
    ):
        super().__init__(channel_name="whatsapp")
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.verify_token = verify_token
        self.app_secret = app_secret
        self.allowed_numbers = set(allowed_numbers) if allowed_numbers else None
        self._agent_brain = None
        self._message_handler = None
        self._http_client: httpx.AsyncClient | None = None

    def set_agent(self, agent_brain: Any) -> None:
        """Set the agent brain for processing messages."""
        self._agent_brain = agent_brain

    def set_message_handler(self, handler: Any) -> None:
        """Set an external message handler."""
        self._message_handler = handler

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=WHATSAPP_API_BASE,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._http_client

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str | None:
        """Verify the webhook subscription (GET request from Meta)."""
        if mode == "subscribe" and token == self.verify_token:
            logger.info("whatsapp_webhook_verified")
            return challenge
        logger.warning("whatsapp_webhook_verification_failed", mode=mode)
        return None

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify the webhook payload signature."""
        if not self.app_secret:
            logger.warning("whatsapp_no_app_secret", msg="Skipping signature verification")
            return True

        expected = hmac.new(self.app_secret.encode(), payload, hashlib.sha256).hexdigest()
        provided = signature.replace("sha256=", "")
        return hmac.compare_digest(expected, provided)

    async def handle_webhook(self, payload: dict[str, Any]) -> None:
        """Handle incoming webhook payload from Meta."""
        try:
            entry = payload.get("entry", [])
            for e in entry:
                changes = e.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for message in messages:
                        await self._process_incoming(message, value)
        except Exception as e:
            logger.error("whatsapp_webhook_error", error=str(e))

    async def _process_incoming(self, message: dict[str, Any], value: dict[str, Any]) -> None:
        """Process a single incoming WhatsApp message."""
        msg_type = message.get("type")
        sender = message.get("from", "")
        msg_id = message.get("id", "")

        # Check authorization
        if not self._is_authorized(sender):
            logger.warning("whatsapp_unauthorized", sender=sender)
            return

        # Extract text content
        text = ""
        if msg_type == "text":
            text = message.get("text", {}).get("body", "")
        elif msg_type == "interactive":
            interactive = message.get("interactive", {})
            if interactive.get("type") == "button_reply":
                text = interactive.get("button_reply", {}).get("title", "")
            elif interactive.get("type") == "list_reply":
                text = interactive.get("list_reply", {}).get("title", "")
        elif msg_type == "image":
            text = message.get("image", {}).get("caption", "[Image received]")
        elif msg_type == "document":
            text = f"[Document: {message.get('document', {}).get('filename', 'unknown')}]"
        elif msg_type == "audio":
            text = "[Audio message received]"
        elif msg_type == "location":
            loc = message.get("location", {})
            text = f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"
        else:
            text = f"[Unsupported message type: {msg_type}]"

        if not text:
            return

        logger.info(
            "whatsapp_message_received",
            sender=sender[:6] + "***",
            type=msg_type,
        )

        # Mark as read
        await self._mark_read(msg_id)

        # Get response
        response = await self._get_response(text, sender)

        # Send response
        await self.send_message(sender, response)

    async def _get_response(self, content: str, user_id: str) -> str:
        """Get a response from the agent."""
        try:
            if self._message_handler:
                return await self._message_handler(content, user_id, "whatsapp")
            elif self._agent_brain:
                result = await self._agent_brain.process_message(content, channel="whatsapp")
                return result.get("response", "No response.")
            return "Bot is not configured."
        except Exception as e:
            logger.error("whatsapp_response_failed", error=str(e))
            return "Sorry, I encountered an error processing your request."

    async def send_message(self, user_id: str, content: str, **kwargs: Any) -> None:
        """Send a text message to a WhatsApp number."""
        client = await self._get_http_client()

        # Split long messages (WhatsApp limit: 4096 chars)
        chunks = self._split_message(content, 4096)

        for chunk in chunks:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": user_id,
                "type": "text",
                "text": {"body": chunk},
            }

            try:
                response = await client.post(
                    f"/{self.phone_number_id}/messages",
                    json=payload,
                )
                if response.status_code != 200:
                    logger.error(
                        "whatsapp_send_failed",
                        status=response.status_code,
                        body=response.text[:200],
                    )
            except Exception as e:
                logger.error("whatsapp_send_error", error=str(e))

    async def send_interactive(
        self,
        user_id: str,
        body_text: str,
        buttons: list[dict[str, str]],
    ) -> None:
        """Send an interactive button message."""
        client = await self._get_http_client()

        button_items = [
            {
                "type": "reply",
                "reply": {"id": btn.get("id", str(i)), "title": btn["title"][:20]},
            }
            for i, btn in enumerate(buttons[:3])  # Max 3 buttons
        ]

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": user_id,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": button_items},
            },
        }

        try:
            await client.post(f"/{self.phone_number_id}/messages", json=payload)
        except Exception as e:
            logger.error("whatsapp_interactive_failed", error=str(e))

    async def _mark_read(self, message_id: str) -> None:
        """Mark a message as read."""
        client = await self._get_http_client()
        try:
            await client.post(
                f"/{self.phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id,
                },
            )
        except Exception:
            pass  # Non-critical

    def _is_authorized(self, phone_number: str) -> bool:
        """Check if a phone number is authorized."""
        if self.allowed_numbers is None:
            return True
        return phone_number in self.allowed_numbers

    def run(self) -> None:
        """
        Start the WhatsApp channel.

        Note: WhatsApp uses webhooks, so this registers the webhook
        endpoints on the gateway rather than running a standalone loop.
        """
        self._running = True
        logger.info("whatsapp_channel_ready", msg="Webhook endpoints registered")

    def stop(self) -> None:
        """Stop the WhatsApp channel."""
        self._running = False
        if self._http_client:
            asyncio.get_event_loop().create_task(self._http_client.aclose())
        logger.info("whatsapp_stopped")

    @staticmethod
    def _split_message(text: str, max_length: int) -> list[str]:
        """Split a long message into chunks."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break
            split_at = text.rfind("\n", 0, max_length)
            if split_at == -1:
                split_at = text.rfind(" ", 0, max_length)
            if split_at == -1:
                split_at = max_length
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()
        return chunks


def register_whatsapp_routes(app: Any, channel: WhatsAppChannel) -> None:
    """Register WhatsApp webhook routes on the FastAPI app."""
    from fastapi import Request, Response

    @app.get("/webhook/whatsapp")
    async def whatsapp_verify(request: Request):
        """Webhook verification endpoint."""
        mode = request.query_params.get("hub.mode", "")
        token = request.query_params.get("hub.verify_token", "")
        challenge = request.query_params.get("hub.challenge", "")

        result = channel.verify_webhook(mode, token, challenge)
        if result:
            return Response(content=result, media_type="text/plain")
        return Response(status_code=403)

    @app.post("/webhook/whatsapp")
    async def whatsapp_webhook(request: Request):
        """Incoming message webhook."""
        body = await request.body()

        # Verify signature
        signature = request.headers.get("x-hub-signature-256", "")
        if not channel.verify_signature(body, signature):
            return Response(status_code=403)

        payload = await request.json()
        await channel.handle_webhook(payload)
        return Response(status_code=200)
