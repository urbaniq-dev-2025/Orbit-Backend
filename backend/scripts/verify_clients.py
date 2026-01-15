"""Verify clients and their company sizes."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.client import Client


async def verify():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Client.name, Client.company_size, Client.city, Client.country)
            .order_by(Client.name)
        )
        print("Clients in Database:")
        for row in result.all():
            size = row[1] or "Not Set"
            print(f"  - {row[0]}: {size} - {row[2]}, {row[3]}")


if __name__ == "__main__":
    asyncio.run(verify())
