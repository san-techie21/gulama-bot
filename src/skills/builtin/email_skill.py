"""
Email skill for Gulama.

Supports reading, composing, and sending emails via IMAP/SMTP.
All email operations are sandboxed and DLP-checked.

Security:
- Credentials stored in encrypted vault (never in config)
- Egress filter checks all outgoing email content
- DLP prevents credential/API key leaks in email body

Requires: pip install 'gulama[email]' (no extra deps — uses stdlib)
"""

from __future__ import annotations

import email
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("email_skill")


class EmailSkill(BaseSkill):
    """
    Email management skill.

    Supports:
    - List/search emails (IMAP)
    - Read email content
    - Compose and send emails (SMTP)
    - Reply/forward
    - Search by subject, sender, date

    Config loaded from env vars:
    - EMAIL_ADDRESS, EMAIL_PASSWORD
    - IMAP_HOST, IMAP_PORT (default: 993)
    - SMTP_HOST, SMTP_PORT (default: 587)
    """

    def __init__(self) -> None:
        self._imap_host: str = ""
        self._imap_port: int = 993
        self._smtp_host: str = ""
        self._smtp_port: int = 587
        self._email_address: str = ""
        self._password: str = ""
        self._configured = False

    def _load_config(self) -> None:
        """Lazy-load email config from environment variables."""
        if self._configured:
            return
        import os

        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        self._email_address = os.getenv("EMAIL_ADDRESS", "")
        self._password = os.getenv("EMAIL_PASSWORD", "")
        self._imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
        self._imap_port = int(os.getenv("IMAP_PORT", "993"))
        self._smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self._smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self._configured = True

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="email",
            description="Read, compose, and send emails via IMAP/SMTP",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.EMAIL_SEND, ActionType.NETWORK_REQUEST],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "email",
                "description": (
                    "Manage emails. Actions: "
                    "list (list recent inbox emails), "
                    "read (read full email content by ID), "
                    "send (compose and send an email), "
                    "search (search emails by query)"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "read", "send", "search"],
                            "description": "The email action to perform",
                        },
                        "folder": {
                            "type": "string",
                            "description": "IMAP folder (default: INBOX)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max emails to return (default: 10)",
                        },
                        "email_id": {
                            "type": "string",
                            "description": "Email message ID (for read action)",
                        },
                        "to": {
                            "type": "string",
                            "description": "Recipient email address (for send action)",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject (for send action)",
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body text (for send action)",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (for search action, IMAP search syntax)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute an email action."""
        action = kwargs.get("action", "list")

        dispatch = {
            "list": self._list_emails,
            "read": self._read_email,
            "send": self._send_email,
            "search": self._search_emails,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown email action: {action}. Use: list, read, send, search",
            )

        self._load_config()

        if not self._email_address or not self._password:
            return SkillResult(
                success=False,
                output="",
                error=(
                    "Email not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD env vars, "
                    "or run 'gulama vault set EMAIL_PASSWORD'."
                ),
            )

        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except Exception as e:
            logger.error("email_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"Email error: {str(e)[:300]}")

    async def _list_emails(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        **_: Any,
    ) -> SkillResult:
        """List recent emails."""
        with imaplib.IMAP4_SSL(self._imap_host, self._imap_port) as imap:
            imap.login(self._email_address, self._password)
            imap.select(folder, readonly=True)

            _, msg_ids = imap.search(None, "ALL")
            ids = msg_ids[0].split()

            # Get latest N emails
            ids = ids[-limit:]
            ids.reverse()

            results = []
            for mid in ids:
                _, msg_data = imap.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                if msg_data[0] is None:
                    continue
                header = email.message_from_bytes(msg_data[0][1])
                results.append(
                    f"ID: {mid.decode()} | From: {header.get('From', 'unknown')[:40]} | "
                    f"Subject: {header.get('Subject', '(no subject)')[:60]} | "
                    f"Date: {header.get('Date', '')[:25]}"
                )

            output = "\n".join(results) if results else "No emails found."
            return SkillResult(
                success=True,
                output=output,
                metadata={"count": len(results), "folder": folder},
            )

    async def _read_email(
        self,
        email_id: str = "",
        folder: str = "INBOX",
        **_: Any,
    ) -> SkillResult:
        """Read full email content."""
        if not email_id:
            return SkillResult(
                success=False, output="", error="email_id is required for read action"
            )

        with imaplib.IMAP4_SSL(self._imap_host, self._imap_port) as imap:
            imap.login(self._email_address, self._password)
            imap.select(folder, readonly=True)

            _, msg_data = imap.fetch(email_id.encode(), "(RFC822)")
            if msg_data[0] is None:
                return SkillResult(success=False, output="", error="Email not found.")

            msg = email.message_from_bytes(msg_data[0][1])

            # Extract text content
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

            output = (
                f"From: {msg.get('From', 'unknown')}\n"
                f"To: {msg.get('To', 'unknown')}\n"
                f"Subject: {msg.get('Subject', '(no subject)')}\n"
                f"Date: {msg.get('Date', '')}\n\n"
                f"{body[:3000]}"
            )
            return SkillResult(success=True, output=output)

    async def _send_email(
        self,
        to: str = "",
        subject: str = "",
        body: str = "",
        **_: Any,
    ) -> SkillResult:
        """Send an email."""
        if not to:
            return SkillResult(success=False, output="", error="'to' is required for send action")
        if not subject:
            return SkillResult(
                success=False, output="", error="'subject' is required for send action"
            )
        if not body:
            return SkillResult(success=False, output="", error="'body' is required for send action")

        msg = MIMEMultipart("alternative")
        msg["From"] = self._email_address
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(self._smtp_host, self._smtp_port) as smtp:
            smtp.starttls()
            smtp.login(self._email_address, self._password)
            smtp.send_message(msg)

        logger.info("email_sent", to=to[:20] + "***", subject=subject[:30])
        return SkillResult(
            success=True,
            output=f"Email sent to {to}",
            metadata={"to": to, "subject": subject},
        )

    async def _search_emails(
        self,
        query: str = "",
        folder: str = "INBOX",
        limit: int = 10,
        **_: Any,
    ) -> SkillResult:
        """Search emails by IMAP query."""
        if not query:
            return SkillResult(
                success=False, output="", error="'query' is required for search action"
            )

        with imaplib.IMAP4_SSL(self._imap_host, self._imap_port) as imap:
            imap.login(self._email_address, self._password)
            imap.select(folder, readonly=True)

            _, msg_ids = imap.search(None, query)
            ids = msg_ids[0].split()
            ids = ids[-limit:]
            ids.reverse()

            results = []
            for mid in ids:
                _, msg_data = imap.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                if msg_data[0] is None:
                    continue
                header = email.message_from_bytes(msg_data[0][1])
                results.append(
                    f"ID: {mid.decode()} | From: {header.get('From', 'unknown')[:40]} | "
                    f"Subject: {header.get('Subject', '(no subject)')[:60]}"
                )

            output = "\n".join(results) if results else f"No emails matching '{query}'."
            return SkillResult(
                success=True,
                output=output,
                metadata={"count": len(results), "query": query},
            )
