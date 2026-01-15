"""
Script to update existing dummy clients with company sizes.

This script sets company_size for the three dummy clients:
- abc: Enterprise
- xyz: Mid-Market
- pqr: SMB

Usage:
    python -m scripts.update_client_company_sizes
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Client


async def update_company_sizes():
    """Update company sizes for dummy clients."""
    async with AsyncSessionLocal() as session:
        # Get the three dummy clients
        clients_result = await session.execute(
            select(Client).where(Client.name.in_(["abc", "xyz", "pqr"]))
        )
        clients = clients_result.scalars().all()
        
        if not clients:
            print("❌ No clients found with names 'abc', 'xyz', or 'pqr'")
            return
        
        print(f"📦 Found {len(clients)} client(s) to update")
        
        # Mapping of client names to company sizes
        company_size_mapping = {
            "abc": "Enterprise",
            "xyz": "Mid-Market",
            "pqr": "SMB",
        }
        
        updated_count = 0
        
        for client in clients:
            new_size = company_size_mapping.get(client.name)
            if new_size:
                old_size = client.company_size or "Not Set"
                client.company_size = new_size
                updated_count += 1
                print(f"  ✅ Updated '{client.name}': {old_size} → {new_size}")
            else:
                print(f"  ⚠️  Skipped '{client.name}' (not in mapping)")
        
        await session.commit()
        
        print(f"\n✨ Summary:")
        print(f"  - Updated: {updated_count} client(s)")
        
        # Verify the updates
        print(f"\n🔍 Verification:")
        clients_result = await session.execute(
            select(Client).where(Client.name.in_(["abc", "xyz", "pqr"]))
        )
        clients = clients_result.scalars().all()
        
        for client in clients:
            size_display = client.company_size or "Not Set"
            print(f"  - {client.name}: {size_display}")


if __name__ == "__main__":
    asyncio.run(update_company_sizes())
