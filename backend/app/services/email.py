from __future__ import annotations

import asyncio
import smtplib
import ssl
import time
from collections import deque
from email.message import EmailMessage
from typing import Deque, Dict

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailRateLimitError(Exception):
    """Raised when the in-process rate limiter blocks an email."""


class _SimpleRateLimiter:
    def __init__(self, max_events: int, window_seconds: int) -> None:
        self._max_events = max_events
        self._window = window_seconds
        self._events: Dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    async def hit(self, key: str) -> None:
        async with self._lock:
            now = time.monotonic()
            queue = self._events.setdefault(key, deque())
            # Drop expired entries
            while queue and now - queue[0] > self._window:
                queue.popleft()
            if len(queue) >= self._max_events:
                raise EmailRateLimitError(f"Rate limit exceeded for {key}")
            queue.append(now)


class EmailDispatcher:
    """Minimal SMTP-based dispatcher with simple rate limiting."""

    WINDOW_SECONDS = 60 * 60  # 1 hour

    def __init__(self) -> None:
        settings = get_settings()
        reset_limit = max(1, settings.password_reset_emails_per_hour)
        invite_limit = max(1, settings.invite_emails_per_hour)
        self._password_reset_limiter = _SimpleRateLimiter(
            reset_limit, self.WINDOW_SECONDS
        )
        self._invite_limiter = _SimpleRateLimiter(invite_limit, self.WINDOW_SECONDS)
        self._settings = settings

    async def send_password_reset_code(self, email: str, code: str) -> None:
        key = f"password_reset:{email.lower()}"
        await self._password_reset_limiter.hit(key)
        await self._send_email(
            to_address=email,
            subject="Your Orbit password reset code",
            body=(
                "Here is your Orbit password reset code:\n\n"
                f"{code}\n\n"
                "This code expires in 15 minutes. If you did not request this, please ignore."
            ),
        )

    async def send_workspace_invite(
        self,
        email: str,
        *,
        workspace_name: str,
        inviter_name: str | None = None,
        invite_message: str | None = None,
    ) -> None:
        key = f"workspace_invite:{email.lower()}"
        await self._invite_limiter.hit(key)
        display_inviter = inviter_name or "A teammate"
        body_lines = [
            f"{display_inviter} invited you to collaborate on the workspace '{workspace_name}' in Orbit.",
            "",
            "Sign in to accept the invitation and continue onboarding.",
        ]
        if invite_message:
            body_lines.extend(["", "Message:", invite_message])
        body_lines.append("")
        body_lines.append("See you soon!")
        await self._send_email(
            to_address=email,
            subject=f"You're invited to join {workspace_name} on Orbit",
            body="\n".join(body_lines),
        )

    async def _send_email(self, to_address: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["To"] = to_address
        message["Subject"] = subject

        if not self._settings.smtp_from or not self._settings.smtp_host:
            logger.warning(
                "SMTP not configured; logging email instead of sending",
                extra={"to": to_address, "subject": subject},
            )
            message["From"] = "no-reply@localhost"
            logger.info("Email payload:\n%s", body)
            return

        message["From"] = self._settings.smtp_from
        message.set_content(body)

        await asyncio.to_thread(self._send_via_smtp, message)

    def _send_via_smtp(self, message: EmailMessage) -> None:
        host = self._settings.smtp_host
        assert host is not None
        port = self._settings.smtp_port
        username = self._settings.smtp_user
        password = self._settings.smtp_password
        use_tls = self._settings.smtp_use_tls

        logger.debug(
            "Sending email via SMTP",
            extra={"host": host, "port": port, "to": message["To"]},
        )

        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls(context=context)
                if username and password:
                    server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                if username and password:
                    server.login(username, password)
                server.send_message(message)


_dispatcher = EmailDispatcher()


def get_email_dispatcher() -> EmailDispatcher:
    return _dispatcher


