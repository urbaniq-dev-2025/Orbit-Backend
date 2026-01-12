from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.services.google_oauth import GoogleUserInfo


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


@pytest.mark.asyncio
async def test_signup_and_me(client: AsyncClient):
    email = unique_email()
    payload = {"email": email, "password": "testpassword", "full_name": "Test User"}

    res = await client.post("/api/auth/signup", json=payload)
    assert res.status_code == 201
    tokens = res.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    # Call /me with access token
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_res = await client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    body = me_res.json()
    assert body["email"] == email
    assert body["is_active"] is True
    assert body["is_verified"] is False


@pytest.mark.asyncio
async def test_signin(client: AsyncClient):
    email = unique_email()
    payload = {"email": email, "password": "testpassword"}

    # Seed user via signup
    res = await client.post("/api/auth/signup", json=payload)
    assert res.status_code == 201

    res_signin = await client.post("/api/auth/signin", json=payload)
    assert res_signin.status_code == 200
    tokens = res_signin.json()
    assert "access_token" in tokens and "refresh_token" in tokens


@pytest.mark.asyncio
async def test_signin_invalid_credentials(client: AsyncClient):
    payload = {"email": unique_email(), "password": "wrong"}
    res = await client.post("/api/auth/signin", json=payload)
    assert res.status_code == 400
    assert "Invalid credentials" in res.text


@pytest.mark.asyncio
async def test_google_oauth_flow(client: AsyncClient, monkeypatch):
    settings = get_settings()
    settings.google_client_id = "test-google-client"
    settings.google_client_secret = "test-google-secret"
    settings.google_allowed_redirects = ["https://frontend.test/auth/google"]

    init_payload = {"redirectUri": "https://frontend.test/auth/google"}
    init_res = await client.post("/api/auth/google/init", json=init_payload)
    assert init_res.status_code == 200
    init_body = init_res.json()
    assert init_body["state"]
    assert settings.google_client_id in init_body["authUrl"]

    async def fake_exchange(self, *, code: str, redirect_uri: str) -> GoogleUserInfo:
        assert code == "sample-code"
        assert redirect_uri == "https://frontend.test/auth/google"
        return GoogleUserInfo(
            sub="google-sub-123",
            email="google-user@example.com",
            email_verified=True,
            name="Google User",
        )

    monkeypatch.setattr(
        "app.services.google_oauth.GoogleOAuthClient.exchange_code",
        fake_exchange,
        raising=False,
    )

    complete_payload = {"code": "sample-code", "state": init_body["state"]}
    complete_res = await client.post("/api/auth/google/complete", json=complete_payload)
    assert complete_res.status_code == 200
    tokens = complete_res.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_res = await client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_payload = me_res.json()
    assert me_payload["email"] == "google-user@example.com"
    assert me_payload["is_verified"] is True

    # Replaying the flow with the same Google identity should succeed and return tokens again.
    second_res = await client.post("/api/auth/google/complete", json=complete_payload)
    assert second_res.status_code == 200
    second_tokens = second_res.json()
    assert second_tokens["access_token"]


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient, monkeypatch):
    email = unique_email()
    original_password = "initialPass1!"
    res_signup = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": original_password},
    )
    assert res_signup.status_code == 201

    captured: dict[str, str] = {}

    class FakeDispatcher:
        async def send_password_reset_code(self, address: str, code: str) -> None:
            captured[address] = code

    monkeypatch.setattr(
        "app.api.routes.auth.get_email_dispatcher",
        lambda: FakeDispatcher(),
        raising=False,
    )

    res_request = await client.post("/api/auth/password/request", json={"email": email})
    assert res_request.status_code == 202
    assert email in captured

    verify_payload = {"email": email, "code": captured[email]}
    res_verify = await client.post("/api/auth/password/verify", json=verify_payload)
    assert res_verify.status_code == 200
    reset_token = res_verify.json()["resetToken"]

    new_password = "UpdatedPass2!"
    res_complete = await client.post(
        "/api/auth/password/reset",
        json={"resetToken": reset_token, "newPassword": new_password},
    )
    assert res_complete.status_code == 204

    res_old_login = await client.post(
        "/api/auth/signin", json={"email": email, "password": original_password}
    )
    assert res_old_login.status_code == 400

    res_new_login = await client.post(
        "/api/auth/signin", json={"email": email, "password": new_password}
    )
    assert res_new_login.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_invalid_code(client: AsyncClient, monkeypatch):
    email = unique_email()
    await client.post("/api/auth/signup", json={"email": email, "password": "SomePass9!"})

    class NoopDispatcher:
        async def send_password_reset_code(self, *_: str) -> None:
            return None

    monkeypatch.setattr(
        "app.api.routes.auth.get_email_dispatcher",
        lambda: NoopDispatcher(),
        raising=False,
    )

    await client.post("/api/auth/password/request", json={"email": email})
    res_verify = await client.post(
        "/api/auth/password/verify", json={"email": email, "code": "000000"}
    )
    assert res_verify.status_code == 400

