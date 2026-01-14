"""
Script to set up dummy workspace and clients.

This script will:
1. Create a dummy admin user (if it doesn't exist)
2. Create a dummy workspace for that user
3. Add 3 dummy clients (abc, xyz, pqr) to the workspace

Usage:
    python -m scripts.setup_dummy_data
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
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models import Client, User, Workspace, WorkspaceMember
from app.services.workspaces import create_workspace
from app.utils.slugify import slugify


async def get_or_create_admin_user(session: AsyncSession) -> User:
    """Get or create an admin user."""
    admin_email = "admin@orbit.dev"
    
    # Check if user exists
    stmt = select(User).where(User.email == admin_email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # Ensure existing admin user has admin role
        if user.role != "admin":
            print(f"⚠️  Updating existing user to admin role: {user.email}")
            user.role = "admin"
            await session.flush()
        print(f"✅ Found existing admin user: {user.email}")
        return user
    
    # Create new admin user
    print(f"📝 Creating admin user: {admin_email}")
    user = User(
        email=admin_email,
        hashed_password=hash_password("admin123"),  # Dummy password
        full_name="Orbit Admin",
        role="admin",  # Set as admin
        is_active=True,
        is_verified=True,
        onboarding_completed=True,
    )
    session.add(user)
    await session.flush()
    print(f"✅ Created admin user: {user.email} (ID: {user.id})")
    return user


async def get_or_create_workspace(session: AsyncSession, owner: User) -> Workspace:
    """Get or create a workspace for the user."""
    # Check if user already has a workspace
    stmt = (
        select(Workspace)
        .where(Workspace.owner_id == owner.id)
        .order_by(Workspace.created_at.asc())
        .limit(1)
    )
    result = await session.execute(stmt)
    workspace = result.scalar_one_or_none()
    
    if workspace:
        print(f"✅ Found existing workspace: {workspace.name} (ID: {workspace.id})")
        return workspace
    
    # Create new workspace
    workspace_name = "Orbit Workspace"
    print(f"📝 Creating workspace: {workspace_name}")
    workspace = await create_workspace(
        session,
        owner_id=owner.id,
        name=workspace_name,
        logo_url=None,
        brand_color="#ff6b35",
        secondary_color="#1a1a1a",
        website_url=None,
        team_size="1-10",
        data_handling="standard",
    )
    print(f"✅ Created workspace: {workspace.name} (ID: {workspace.id}, Slug: {workspace.slug})")
    return workspace


async def add_dummy_clients(session: AsyncSession, workspace: Workspace):
    """Add 3 dummy clients to the workspace."""
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
        await session.flush()  # Flush to get the ID
        created_count += 1
        location_str = f"{client_data['city']}, {client_data['country']}" if client_data.get('city') and client_data.get('country') else client_data.get('city') or client_data.get('country') or 'N/A'
        print(f"✅ Created client: {client_data['name']} ({location_str})")
    
    # Commit all clients
    await session.commit()
    
    print(f"\n📊 Summary:")
    print(f"   Created: {created_count} clients")
    print(f"   Skipped: {skipped_count} clients (already exist)")
    print(f"   Workspace: {workspace.name}")
    print(f"\n✅ Dummy data setup completed successfully!")


async def setup_dummy_data():
    """Main function to set up dummy workspace and clients."""
    settings = get_settings()
    
    async with AsyncSessionLocal() as session:
        try:
            # Step 1: Get or create admin user
            print("🔧 Step 1: Setting up admin user...")
            admin_user = await get_or_create_admin_user(session)
            await session.commit()
            
            # Step 2: Get or create workspace
            print("\n🔧 Step 2: Setting up workspace...")
            workspace = await get_or_create_workspace(session, admin_user)
            await session.commit()
            
            # Step 3: Add dummy clients
            print("\n🔧 Step 3: Adding dummy clients...")
            await add_dummy_clients(session, workspace)
            
            print("\n" + "="*50)
            print("🎉 All done! Your dummy data is ready:")
            print(f"   Admin Email: {admin_user.email}")
            print(f"   Admin Password: admin123 (dummy password)")
            print(f"   Workspace: {workspace.name}")
            print(f"   Clients: abc, xyz, pqr")
            print("="*50)
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(setup_dummy_data())
