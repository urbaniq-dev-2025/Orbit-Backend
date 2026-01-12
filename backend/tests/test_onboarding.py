from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Workspace, WorkspaceMember


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"


async def _signup(client: AsyncClient, email: str, password: str = "Testpass1!") -> str:
    res = await client.post(
        "/api/auth/signup", json={"email": email, "password": password}
    )
    assert res.status_code == 201
    tokens = res.json()
    return tokens["access_token"]


class FakeDispatcher:
    def __init__(self) -> None:
        self.reset_codes: list[tuple[str, str]] = []
        self.invites: list[tuple[str, str]] = []

    async def send_password_reset_code(self, email: str, code: str) -> None:
        self.reset_codes.append((email, code))

    async def send_workspace_invite(
        self,
        email: str,
        *,
        workspace_name: str,
        inviter_name: str | None = None,
        invite_message: str | None = None,
    ) -> None:
        self.invites.append((email, workspace_name))


@pytest.mark.asyncio
async def test_full_onboarding_flow(client: AsyncClient, monkeypatch):
    email = unique_email("onboard")
    token = await _signup(client, email)

    dispatcher = FakeDispatcher()
    monkeypatch.setattr(
        "app.api.routes.onboarding.get_email_dispatcher",
        lambda: dispatcher,
        raising=False,
    )

    headers = {"Authorization": f"Bearer {token}"}

    status_res = await client.get("/api/onboarding/status", headers=headers)
    assert status_res.status_code == 200
    body = status_res.json()
    assert body["step"] == "workspace"
    assert body["stepsCompleted"] == []
    assert body["completed"] is False

    step1_payload = {
        "name": "Acme Workspace",
        "primaryColor": "#123456",
        "secondaryColor": "#654321",
        "teamSize": "small",
        "dataHandling": "standard",
    }
    res_step1 = await client.post(
        "/api/onboarding/step1", headers=headers, json=step1_payload
    )
    assert res_step1.status_code == 200
    body = res_step1.json()
    assert body["step"] == "team"
    assert body["workspace"]["name"] == "Acme Workspace"
    workspace_id = body["workspace"]["workspaceId"]
    assert workspace_id

    invites = [unique_email("invite1"), unique_email("invite2")]
    res_step2 = await client.post(
        "/api/onboarding/step2",
        headers=headers,
        json={
            "teamSize": "small",
            "invites": invites,
            "inviteMessage": "Join us!",
        },
    )
    assert res_step2.status_code == 200
    body = res_step2.json()
    assert body["step"] == "goals"
    assert sorted(dispatcher.invites) == sorted(
        [(email, "Acme Workspace") for email in invites]
    )

    res_step3 = await client.post(
        "/api/onboarding/step3",
        headers=headers,
        json={"goals": ["deliver faster"], "customGoal": "Delight clients"},
    )
    assert res_step3.status_code == 200
    body = res_step3.json()
    assert body["step"] == "plan"
    assert body["goals"]["goals"] == ["deliver faster"]

    res_step4 = await client.post(
        "/api/onboarding/step4",
        headers=headers,
        json={
            "plan": "starter",
            "billingCountry": "US",
            "companySize": "1-10",
        },
    )
    assert res_step4.status_code == 200
    body = res_step4.json()
    assert body["step"] == "complete"
    assert body["plan"]["plan"] == "starter"
    assert body["completed"] is False

    res_complete = await client.post(
        "/api/onboarding/complete", headers=headers
    )
    assert res_complete.status_code == 200
    body = res_complete.json()
    assert body["completed"] is True
    assert body["step"] == "complete"
    assert set(body["stepsCompleted"]) == {"workspace", "team", "goals", "plan"}

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == uuid.UUID(workspace_id),
                WorkspaceMember.invited_email.in_(invites),
            )
        )
        members = result.scalars().all()
        assert len(members) == 2


@pytest.mark.asyncio
async def test_onboarding_skip_creates_workspace(client: AsyncClient, monkeypatch):
    dispatcher = FakeDispatcher()
    monkeypatch.setattr(
        "app.api.routes.onboarding.get_email_dispatcher",
        lambda: dispatcher,
        raising=False,
    )

    email = unique_email("skip")
    token = await _signup(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    res_skip = await client.post("/api/onboarding/skip", headers=headers)
    assert res_skip.status_code == 200
    body = res_skip.json()
    assert body["completed"] is True
    assert body["step"] == "complete"
    workspace_id = body["workspace"]["workspaceId"]
    assert workspace_id

    async with AsyncSessionLocal() as session:
        workspace = await session.get(Workspace, uuid.UUID(workspace_id))
        assert workspace is not None


@pytest.mark.asyncio
async def test_invalid_step_order(client: AsyncClient):
    email = unique_email("invalid")
    token = await _signup(client, email)
    headers = {"Authorization": f"Bearer {token}"}

    res_step2 = await client.post(
        "/api/onboarding/step2",
        headers=headers,
        json={"teamSize": "small", "invites": [unique_email("late")]},
    )
    assert res_step2.status_code == 409

