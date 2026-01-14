"""
Script to update existing clients with city and country data.

This script updates the dummy clients (abc, xyz, pqr) with proper city and country values.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import Client


async def update_clients():
    """Update existing clients with city and country."""
    async with AsyncSessionLocal() as session:
        try:
            # Get clients by name
            result = await session.execute(
                select(Client).where(Client.name.in_(["abc", "xyz", "pqr"]))
            )
            clients = result.scalars().all()
            
            # Mapping of client names to city/country
            updates = {
                "abc": {"city": "Boston", "country": "United States"},
                "xyz": {"city": "Cambridge", "country": "United States"},
                "pqr": {"city": "San Francisco", "country": "United States"},
            }
            
            updated_count = 0
            for client in clients:
                if client.name.lower() in updates:
                    data = updates[client.name.lower()]
                    client.city = data["city"]
                    client.country = data["country"]
                    updated_count += 1
                    print(f"✅ Updated {client.name}: city={data['city']}, country={data['country']}")
            
            await session.commit()
            print(f"\n📊 Summary: Updated {updated_count} clients")
            print("✅ All clients updated successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(update_clients())
