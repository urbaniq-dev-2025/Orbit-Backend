from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    email = unique_email()
    signup_payload = {"email": email, "password": "testpassword", "full_name": "Workspace Owner"}
    res = await client.post("/api/auth/signup", json=signup_payload)
    assert res.status_code == 201
    tokens = res.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_create_and_list_workspaces(client: AsyncClient):
    headers = await _auth_headers(client)

    create_payload = {
        "name": "Acme Space",
        "primaryColor": "#112233",
        "secondaryColor": "#445566",
        "website": "https://acme.example.com",
    }
    res = await client.post("/api/workspaces", json=create_payload, headers=headers)
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == create_payload["name"]
    assert body["role"] == "owner"
    assert body["slug"].startswith("acme-space")
    workspace_id = body["id"]

    list_res = await client.get("/api/workspaces", headers=headers)
    assert list_res.status_code == 200
    list_body = list_res.json()
    assert len(list_body) == 1
    assert list_body[0]["id"] == workspace_id
    assert list_body[0]["role"] == "owner"

    detail_res = await client.get(f"/api/workspaces/{workspace_id}?includeMembers=true", headers=headers)
    assert detail_res.status_code == 200
    detail_body = detail_res.json()
    assert detail_body["id"] == workspace_id
    assert detail_body["role"] == "owner"
    assert detail_body["members"] is not None
    assert len(detail_body["members"]) == 1
    member = detail_body["members"][0]
    assert member["role"] == "owner"
    assert member["status"] == "active"


@pytest.mark.asyncio
async def test_update_workspace_requires_admin_or_owner(client: AsyncClient):
    headers = await _auth_headers(client)

    res = await client.post("/api/workspaces", json={"name": "Beta Org"}, headers=headers)
    assert res.status_code == 201
    workspace_id = res.json()["id"]

    update_payload = {"name": "Beta Org Updated", "primaryColor": "#abcdef"}
    update_res = await client.put(f"/api/workspaces/{workspace_id}", json=update_payload, headers=headers)
    assert update_res.status_code == 200
    update_body = update_res.json()
    assert update_body["name"] == update_payload["name"]
    assert update_body["role"] == "owner"
    assert update_body["brand_color"] == "#abcdef"



