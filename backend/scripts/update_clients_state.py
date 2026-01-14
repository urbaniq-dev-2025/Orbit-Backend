"""
Script to update existing clients (abc and xyz) with state information.
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


async def update_clients_state():
    """Update existing clients (abc and xyz) with state information."""
    async with AsyncSessionLocal() as session:
        try:
            # Get clients by name
            result = await session.execute(
                select(Client).where(Client.name.in_(["abc", "xyz"]))
            )
            clients = result.scalars().all()
            
            # Mapping of client names to state
            updates = {
                "abc": "Massachusetts",
                "xyz": "Massachusetts",
            }
            
            updated_count = 0
            for client in clients:
                if client.name.lower() in updates:
                    client.state = updates[client.name.lower()]
                    updated_count += 1
                    print(f"✅ Updated {client.name}: state={updates[client.name.lower()]}")
            
            await session.commit()
            print(f"\n📊 Summary: Updated {updated_count} clients with state information")
            print("✅ All clients updated successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(update_clients_state())
