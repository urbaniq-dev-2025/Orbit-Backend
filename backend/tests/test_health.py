from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    res = await client.get("/api/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    res = await client.get("/api/health/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


