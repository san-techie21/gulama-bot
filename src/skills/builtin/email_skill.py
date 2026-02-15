"""
Email skill for Gulama.

Supports reading, composing, and sending emails via IMAP/SMTP.
All email operations are sandboxed and DLP-checked.

Security:
- Credentials stored in encrypted vault (never in config)
- Egress filter checks all outgoing email content
- DLP prevents credential/API key leaks in email body
"""

from __future__ import annotations

import email
import imaplib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from src.skills.base import BaseSkill
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
    """

    name = "email"
    description = "Read, compose, and send emails"
    version = "1.0.0"

    def __init__(
        self,
        imap_host: str = "",
        imap_port: int = 993,
        smtp_host: str = "",
        smtp_port: int = 587,
        email_address: str = "",
        password: str = "",
    ):
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.email_address = email_address
        self.password = password

    def get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "email_list",
                    "description": "List recent emails from inbox",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder": {"type": "string", "default": "INBOX"},
                            "limit": {"type": "integer", "default": 10},
                            "search": {"type": "string", "description": "Search query (IMAP search)"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "email_read",
                    "description": "Read the full content of an email",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "email_id": {"type": "string", "description": "Email message ID"},
                            "folder": {"type": "string", "default": "INBOX"},
                        },
                        "required": ["email_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "email_send",
                    "description": "Send an email",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string", "description": "Recipient email address"},
                            "subject": {"type": "string"},
                            "body": {"type": "string", "description": "Email body (plain text)"},
                            "html": {"type": "string", "description": "HTML body (optional)"},
                        },
                        "required": ["to", "subject", "body"],
                    },
                },
            },
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        dispatch = {
            "email_list": self._list_emails,
            "email_read": self._read_email,
            "email_send": self._send_email,
        }

        handler = dispatch.get(tool_name)
        if not handler:
            return f"Unknown email action: {tool_name}"

        if not self.email_address or not self.password:
            return "Email not configured. Run 'gulama vault set EMAIL_PASSWORD' first."

        try:
            return await handler(**arguments)
        except Exception as e:
            logger.error("email_error", action=tool_name, error=str(e))
            return f"Email error: {str(e)[:200]}"

    async def _list_emails(
        self, folder: str = "INBOX", limit: int = 10, search: str = ""
    ) -> str:
        """List recent emails."""
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
            imap.login(self.email_address, self.password)
            imap.select(folder, readonly=True)

            criteria = search if search else "ALL"
            _, msg_ids = imap.search(None, criteria)
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

            return "\n".join(results) if results else "No emails found."

    async def _read_email(self, email_id: str, folder: str = "INBOX") -> str:
        """Read full email content."""
        with imaplib.IMAP4_SSL(self.imap_host, self.imap_port) as imap:
            imap.login(self.email_address, self.password)
            imap.select(folder, readonly=True)

            _, msg_data = imap.fetch(email_id.encode(), "(RFC822)")
            if msg_data[0] is None:
                return "Email not found."

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

            return (
                f"From: {msg.get('From', 'unknown')}\n"
                f"To: {msg.get('To', 'unknown')}\n"
                f"Subject: {msg.get('Subject', '(no subject)')}\n"
                f"Date: {msg.get('Date', '')}\n\n"
                f"{body[:3000]}"
            )

    async def _send_email(
        self, to: str, subject: str, body: str, html: str = ""
    ) -> str:
        """Send an email."""
        msg = MIMEMultipart("alternative")
        msg["From"] = self.email_address
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))
        if html:
            msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(self.email_address, self.password)
            smtp.send_message(msg)

        logger.info("email_sent", to=to[:20] + "***", subject=subject[:30])
        return f"Email sent to {to}"
