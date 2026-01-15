"""Test script for geographic revenue endpoint."""
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.subscription import Subscription
from app.models.client import Client
from app.models.workspace import Workspace
from sqlalchemy import select, func
from app.services.admin import get_geographic_revenue


async def test_geographic_revenue():
    """Test the geographic revenue endpoint."""
    async with AsyncSessionLocal() as session:
        # Check counts
        sub_count = await session.scalar(select(func.count()).select_from(Subscription))
        active_sub_count = await session.scalar(
            select(func.count()).select_from(Subscription).where(Subscription.status == "active")
        )
        client_count = await session.scalar(select(func.count()).select_from(Client))
        workspace_count = await session.scalar(select(func.count()).select_from(Workspace))
        
        print(f"📊 Database Stats:")
        print(f"  - Total Subscriptions: {sub_count}")
        print(f"  - Active Subscriptions: {active_sub_count}")
        print(f"  - Total Clients: {client_count}")
        print(f"  - Total Workspaces: {workspace_count}")
        
        # Check clients with location data
        clients_with_location = await session.execute(
            select(Client).where(
                (Client.country.isnot(None)) | (Client.city.isnot(None))
            )
        )
        clients_with_location_list = clients_with_location.scalars().all()
        print(f"\n📍 Clients with Location Data: {len(clients_with_location_list)}")
        for client in clients_with_location_list[:5]:
            print(f"  - {client.name}: {client.city}, {client.state}, {client.country}")
        
        # Check subscriptions with workspace and clients
        if active_sub_count > 0:
            subs_with_workspace = await session.execute(
                select(Subscription, Workspace)
                .join(Workspace, Subscription.workspace_id == Workspace.id)
                .where(Subscription.status == "active")
                .limit(5)
            )
            print(f"\n🔗 Sample Active Subscriptions:")
            for sub, workspace in subs_with_workspace.all():
                clients = await session.execute(
                    select(Client).where(Client.workspace_id == workspace.id)
                )
                client_list = clients.scalars().all()
                print(f"  - Subscription {sub.id[:8]}... (Plan: {sub.plan})")
                print(f"    Workspace: {workspace.name} ({workspace.id[:8]}...)")
                print(f"    Clients: {len(client_list)}")
                for c in client_list[:2]:
                    print(f"      - {c.name}: {c.city}, {c.state}, {c.country}")
        
        # Test the geographic revenue function
        print(f"\n🌍 Testing Geographic Revenue Function:")
        result = await get_geographic_revenue(session)
        print(f"  Total Revenue: ${result['totalRevenue']}")
        print(f"  Countries: {len(result['revenueByCountry'])}")
        print(f"  States: {len(result['revenueByState'])}")
        print(f"  Cities: {len(result['revenueByCity'])}")
        
        if result['revenueByCountry']:
            print(f"\n  Top Countries:")
            for country_data in result['revenueByCountry'][:5]:
                print(f"    - {country_data['country']} ({country_data.get('countryCode', 'N/A')}): ${country_data['revenue']} ({country_data.get('subscriptionCount', 0)} subscriptions)")


if __name__ == "__main__":
    asyncio.run(test_geographic_revenue())
