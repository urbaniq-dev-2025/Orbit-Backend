from __future__ import annotations

from typing import Iterable, Sequence
from urllib.parse import urlencode

import httpx
from pydantic import AnyUrl, BaseModel

from app.core.config import get_settings

DEFAULT_SCOPES: tuple[str, ...] = ("openid", "email", "profile")


class GoogleOAuthError(Exception):
    """Raised when Google OAuth operations fail."""


class GoogleUserInfo(BaseModel):
    sub: str
    email: str
    email_verified: bool = False
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: AnyUrl | None = None
    locale: str | None = None


class GoogleOAuthClient:
    """Lightweight client for Google OAuth 2.0 (Authorization Code flow)."""

    def __init__(self) -> None:
        self._settings = get_settings()
        if not self._settings.google_oauth_enabled:
            raise ValueError("Google OAuth is not configured")
        self._authorize_url = str(self._settings.google_authorize_url)
        self._token_url = str(self._settings.google_token_url)
        self._userinfo_url = str(self._settings.google_userinfo_url)
        self._client_id = self._settings.google_client_id  # type: ignore[assignment]
        self._client_secret = self._settings.google_client_secret  # type: ignore[assignment]
        self._timeout = httpx.Timeout(30.0, connect=10.0)

    def build_authorization_url(
        self,
        *,
        redirect_uri: str,
        state: str,
        scopes: Sequence[str] | None = None,
        prompt: str | None = None,
        include_granted_scopes: bool = True,
        access_type: str = "offline",
    ) -> str:
        scope_values: Iterable[str] = scopes or DEFAULT_SCOPES
        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "scope": " ".join(scope_values),
            "redirect_uri": redirect_uri,
            "state": state,
        }
        if prompt:
            params["prompt"] = prompt
        if include_granted_scopes:
            params["include_granted_scopes"] = "true"
        if access_type:
            params["access_type"] = access_type
        query = urlencode(params, doseq=True)
        return f"{self._authorize_url}?{query}"

    async def exchange_code(self, *, code: str, redirect_uri: str) -> GoogleUserInfo:
        """Exchange an authorization code for Google user information."""
        data = {
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                token_response = await client.post(self._token_url, data=data, headers=headers)
                token_response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - wrapped below
                raise GoogleOAuthError(
                    f"Google token exchange failed with status {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:  # pragma: no cover - wrapped below
                raise GoogleOAuthError("Failed to reach Google token endpoint") from exc

            token_payload = token_response.json()
            access_token = token_payload.get("access_token")
            if not access_token:
                raise GoogleOAuthError("Google token response missing access_token")

            try:
                userinfo_response = await client.get(
                    self._userinfo_url, headers={"Authorization": f"Bearer {access_token}"}
                )
                userinfo_response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - wrapped below
                raise GoogleOAuthError(
                    f"Google userinfo fetch failed with status {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:  # pragma: no cover - wrapped below
                raise GoogleOAuthError("Failed to reach Google userinfo endpoint") from exc

        return GoogleUserInfo(**userinfo_response.json())





