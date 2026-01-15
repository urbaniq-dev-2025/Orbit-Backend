"""
Script to add 5 additional clients with different company sizes and geographic locations.

Clients to be added:
1. TechCorp India (Gujarat, India) - Enterprise
2. Paris Solutions (Paris, France) - Mid-Market
3. Dubai Innovations (Dubai, UAE) - Enterprise
4. London Ventures (London, UK) - Mid-Market
5. Sydney Tech (Sydney, Australia) - SMB

Usage:
    python -m scripts.add_additional_clients
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Client, Workspace


async def add_additional_clients():
    """Add 5 additional clients with different company sizes and locations."""
    async with AsyncSessionLocal() as session:
        # Get the first workspace
        workspace_result = await session.execute(select(Workspace).limit(1))
        workspace = workspace_result.scalar_one_or_none()
        
        if not workspace:
            print("❌ No workspace found. Please create a workspace first.")
            return
        
        print(f"📦 Using workspace: {workspace.name}")
        
        # Define the 5 new clients
        new_clients = [
            {
                "name": "TechCorp India",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "country": "India",
                "industry": "Technology",
                "company_size": "Enterprise",
                "contact_name": "Rajesh Patel",
                "contact_email": "rajesh.patel@techcorpindia.com",
                "contact_phone": "+91-79-5555-1001",
                "status": "active",
                "health_score": 90,
                "source": "Website",
                "notes": "Leading technology company in Gujarat. Enterprise client with multiple projects.",
                "logo_url": "https://via.placeholder.com/150?text=TechCorp"
            },
            {
                "name": "Paris Solutions",
                "city": "Paris",
                "state": None,
                "country": "France",
                "industry": "Consulting",
                "company_size": "Mid-Market",
                "contact_name": "Marie Dubois",
                "contact_email": "marie.dubois@parissolutions.fr",
                "contact_phone": "+33-1-5555-2002",
                "status": "active",
                "health_score": 80,
                "source": "Referral",
                "notes": "Mid-market consulting firm based in Paris. Growing European presence.",
                "logo_url": "https://via.placeholder.com/150?text=Paris"
            },
            {
                "name": "Dubai Innovations",
                "city": "Dubai",
                "state": None,
                "country": "United Arab Emirates",
                "industry": "Technology",
                "company_size": "Enterprise",
                "contact_name": "Ahmed Al-Mansoori",
                "contact_email": "ahmed.almansoori@dubaiinnovations.ae",
                "contact_phone": "+971-4-5555-3003",
                "status": "active",
                "health_score": 85,
                "source": "Website",
                "notes": "Enterprise technology solutions provider in Dubai. Strong regional presence.",
                "logo_url": "https://via.placeholder.com/150?text=Dubai"
            },
            {
                "name": "London Ventures",
                "city": "London",
                "state": None,
                "country": "United Kingdom",
                "industry": "Finance",
                "company_size": "Mid-Market",
                "contact_name": "James Wilson",
                "contact_email": "james.wilson@londonventures.co.uk",
                "contact_phone": "+44-20-5555-4004",
                "status": "active",
                "health_score": 75,
                "source": "Referral",
                "notes": "Mid-market financial services company in London. Expanding operations.",
                "logo_url": "https://via.placeholder.com/150?text=London"
            },
            {
                "name": "Sydney Tech",
                "city": "Sydney",
                "state": "New South Wales",
                "country": "Australia",
                "industry": "Technology",
                "company_size": "SMB",
                "contact_name": "Emma Thompson",
                "contact_email": "emma.thompson@sydneytech.com.au",
                "contact_phone": "+61-2-5555-5005",
                "status": "active",
                "health_score": 70,
                "source": "Website",
                "notes": "Small technology startup in Sydney. Early stage company with growth potential.",
                "logo_url": "https://via.placeholder.com/150?text=Sydney"
            },
        ]
        
        # Check which clients already exist
        existing_clients_result = await session.execute(
            select(Client).where(Client.workspace_id == workspace.id)
        )
        existing_clients = existing_clients_result.scalars().all()
        existing_names = {client.name.lower() for client in existing_clients}
        
        created_count = 0
        skipped_count = 0
        
        for client_data in new_clients:
            if client_data["name"].lower() in existing_names:
                print(f"  ⏭️  Client '{client_data['name']}' already exists, skipping")
                skipped_count += 1
                continue
            
            client = Client(
                workspace_id=workspace.id,
                name=client_data["name"],
                city=client_data["city"],
                state=client_data["state"],
                country=client_data["country"],
                industry=client_data["industry"],
                company_size=client_data["company_size"],
                contact_name=client_data["contact_name"],
                contact_email=client_data["contact_email"],
                contact_phone=client_data["contact_phone"],
                status=client_data["status"],
                health_score=client_data["health_score"],
                source=client_data["source"],
                notes=client_data["notes"],
                logo_url=client_data["logo_url"],
            )
            
            session.add(client)
            await session.flush()  # Flush after each addition to avoid UUID issues
            created_count += 1
            
            print(f"  ✅ Created '{client_data['name']}': {client_data['company_size']} - {client_data['city']}, {client_data['country']}")
        
        await session.commit()
        
        print(f"\n✨ Summary:")
        print(f"  - Created: {created_count} client(s)")
        print(f"  - Skipped: {skipped_count} client(s) (already exist)")
        
        # Show company size distribution
        if created_count > 0:
            print(f"\n📊 Company Size Distribution:")
            all_clients_result = await session.execute(
                select(Client).where(Client.workspace_id == workspace.id)
            )
            all_clients = all_clients_result.scalars().all()
            
            size_counts = {}
            for client in all_clients:
                size = client.company_size or "Not Set"
                size_counts[size] = size_counts.get(size, 0) + 1
            
            for size, count in sorted(size_counts.items()):
                print(f"  - {size}: {count} client(s)")


if __name__ == "__main__":
    asyncio.run(add_additional_clients())
