"""
Script to add dummy client data to the database.

Usage:
    python -m scripts.add_dummy_clients

Or from project root:
    python -m backend.scripts.add_dummy_clients
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models import Client, User, Workspace, WorkspaceMember


async def get_first_workspace(session: AsyncSession) -> Workspace:
    """Get the first workspace from the database."""
    stmt = select(Workspace).order_by(Workspace.created_at.asc()).limit(1)
    result = await session.execute(stmt)
    workspace = result.scalar_one_or_none()
    
    if workspace is None:
        raise ValueError("No workspace found in database. Please create a workspace first.")
    
    return workspace


async def add_dummy_clients():
    """Add 3 dummy clients to the first workspace."""
    settings = get_settings()
    
    async with AsyncSessionLocal() as session:
        try:
            # Get first workspace
            workspace = await get_first_workspace(session)
            print(f"Found workspace: {workspace.name} (ID: {workspace.id})")
            
            # Check if clients already exist
            existing_clients_stmt = select(Client).where(Client.workspace_id == workspace.id)
            existing_result = await session.execute(existing_clients_stmt)
            existing_clients = existing_result.scalars().all()
            
            client_names = {client.name.lower() for client in existing_clients}
            
            # Define dummy clients
            dummy_clients = [
                {
                    "name": "abc",
                    "city": "Boston",
                    "state": "Massachusetts",
                    "country": "United States",
                    "industry": "Technology",
                    "contact_name": "John Smith",
                    "contact_email": "john.smith@abc.com",
                    "contact_phone": "+1-617-555-0101",
                    "status": "active",
                    "health_score": 85,
                    "source": "Referral",
                    "notes": "Long-term technology partner. Strong relationship with multiple successful projects.",
                    "logo_url": "https://via.placeholder.com/150?text=ABC"
                },
                {
                    "name": "xyz",
                    "city": "Cambridge",
                    "state": "Massachusetts",
                    "country": "United States",
                    "industry": "Healthcare",
                    "contact_name": "Sarah Johnson",
                    "contact_email": "sarah.johnson@xyz.com",
                    "contact_phone": "+1-617-555-0202",
                    "status": "active",
                    "health_score": 75,
                    "source": "Website",
                    "notes": "Healthcare technology company. Interested in digital transformation solutions.",
                    "logo_url": "https://via.placeholder.com/150?text=XYZ"
                },
                {
                    "name": "pqr",
                    "city": "San Francisco",
                    "country": "United States",
                    "industry": "Finance",
                    "contact_name": "Michael Chen",
                    "contact_email": "michael.chen@pqr.com",
                    "contact_phone": "+1-415-555-0303",
                    "status": "prospect",
                    "health_score": 60,
                    "source": "LinkedIn",
                    "notes": "Financial services firm. Initial contact made. Exploring partnership opportunities.",
                    "logo_url": "https://via.placeholder.com/150?text=PQR"
                }
            ]
            
            created_count = 0
            skipped_count = 0
            
            for client_data in dummy_clients:
                # Skip if client with this name already exists
                if client_data["name"].lower() in client_names:
                    print(f"⚠️  Client '{client_data['name']}' already exists. Skipping...")
                    skipped_count += 1
                    continue
                
                # Create client
                client = Client(
                    workspace_id=workspace.id,
                    name=client_data["name"],
                    logo_url=client_data["logo_url"],
                    status=client_data["status"],
                    industry=client_data["industry"],
                    contact_name=client_data["contact_name"],
                    contact_email=client_data["contact_email"],
                    contact_phone=client_data["contact_phone"],
                    health_score=client_data["health_score"],
                    source=client_data["source"],
                    notes=client_data["notes"],
                    city=client_data["city"],
                    state=client_data.get("state"),
                    country=client_data["country"],
                    last_activity=datetime.now(timezone.utc),
                )
                
                session.add(client)
                created_count += 1
                location_str = f"{client_data['city']}, {client_data['country']}" if client_data.get('city') and client_data.get('country') else client_data.get('city') or client_data.get('country') or 'N/A'
                print(f"✅ Created client: {client_data['name']} ({location_str})")
            
            # Commit all clients
            await session.commit()
            
            print(f"\n📊 Summary:")
            print(f"   Created: {created_count} clients")
            print(f"   Skipped: {skipped_count} clients (already exist)")
            print(f"   Workspace: {workspace.name}")
            print(f"\n✅ Dummy clients added successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(add_dummy_clients())
