"""
Script to reset subscriptions and create new ones with varied plans for all clients.

This script:
1. Deletes all existing subscriptions
2. Creates separate workspaces for each client
3. Moves clients to their workspaces
4. Creates subscriptions with varied plans based on company size
5. Ensures all segments have multiple entries

Usage:
    python -m scripts.reset_and_seed_subscriptions
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete

from app.db.session import AsyncSessionLocal
from app.models import Client, Subscription, User, Workspace, WorkspaceMember
from app.services.workspaces import create_workspace


async def reset_and_seed_subscriptions():
    """Reset subscriptions and create new ones with varied plans."""
    async with AsyncSessionLocal() as session:
        # Get admin user
        user_result = await session.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            print("❌ No user found.")
            return
        
        print(f"👤 Using user: {user.email}")
        
        # Delete all existing subscriptions
        print("🗑️  Deleting existing subscriptions...")
        await session.execute(delete(Subscription))
        await session.commit()
        print("  ✅ Deleted all subscriptions")
        
        # Get all clients
        clients_result = await session.execute(
            select(Client).order_by(Client.company_size, Client.name)
        )
        all_clients = clients_result.scalars().all()
        
        if not all_clients:
            print("❌ No clients found.")
            return
        
        print(f"📦 Found {len(all_clients)} client(s)")
        
        # Plan pricing mapping
        plan_pricing = {
            "free": 0.0,
            "starter": 24.0,
            "pro": 48.0,
            "team": 120.0,
            "enterprise": 500.0,
        }
        
        # Company size to plan mapping with varied distribution
        company_size_plans = {
            "Enterprise": [
                ("enterprise", 0.4),  # 40% enterprise ($500)
                ("team", 0.5),       # 50% team ($120)
                ("pro", 0.1),        # 10% pro ($48)
            ],
            "Mid-Market": [
                ("team", 0.3),       # 30% team ($120)
                ("pro", 0.6),        # 60% pro ($48)
                ("starter", 0.1),    # 10% starter ($24)
            ],
            "SMB": [
                ("pro", 0.4),        # 40% pro ($48)
                ("starter", 0.5),    # 50% starter ($24)
                ("free", 0.1),       # 10% free ($0)
            ],
        }
        
        created_workspaces = 0
        created_subscriptions = 0
        
        # Group clients by company size
        clients_by_size = {}
        for client in all_clients:
            size = client.company_size or "SMB"
            if size not in clients_by_size:
                clients_by_size[size] = []
            clients_by_size[size].append(client)
        
        # Process each client
        for company_size, clients in clients_by_size.items():
            print(f"\n🏢 Processing {company_size} clients ({len(clients)}):")
            
            for client in clients:
                # Get or create workspace for this client
                # Check if client's current workspace has other clients
                workspace_result = await session.execute(
                    select(Workspace, Client)
                    .join(Client, Workspace.id == Client.workspace_id)
                    .where(Workspace.id == client.workspace_id)
                )
                workspace_clients = workspace_result.all()
                
                # If workspace has multiple clients, create a new one
                if len(workspace_clients) > 1:
                    workspace_name = f"{client.name} Workspace"
                    workspace = await create_workspace(
                        session,
                        owner_id=user.id,
                        name=workspace_name,
                    )
                    await session.flush()
                    created_workspaces += 1
                    
                    # Move client to new workspace
                    client.workspace_id = workspace.id
                    await session.flush()
                    print(f"  📦 Created workspace for '{client.name}'")
                else:
                    # Use existing workspace
                    workspace_result = await session.execute(
                        select(Workspace).where(Workspace.id == client.workspace_id)
                    )
                    workspace = workspace_result.scalar_one()
                
                # Determine number of subscriptions
                if company_size == "Enterprise":
                    num_subs = random.randint(1, 2)
                else:
                    num_subs = 1
                
                # Get plan distribution
                plan_options = company_size_plans.get(company_size, company_size_plans["SMB"])
                plans = [plan for plan, _ in plan_options]
                weights = [weight for _, weight in plan_options]
                
                # Create subscriptions
                total_mrr = 0.0
                for i in range(num_subs):
                    plan = random.choices(plans, weights=weights)[0]
                    status = "active"
                    billing_cycle = "monthly"
                    
                    now = datetime.now(timezone.utc)
                    period_start = now - timedelta(days=random.randint(0, 30))
                    period_end = period_start + timedelta(days=30)
                    
                    subscription = Subscription(
                        workspace_id=workspace.id,
                        plan=plan,
                        billing_cycle=billing_cycle,
                        status=status,
                        current_period_start=period_start,
                        current_period_end=period_end,
                        cancel_at_period_end=False,
                    )
                    
                    session.add(subscription)
                    await session.flush()
                    created_subscriptions += 1
                    total_mrr += plan_pricing.get(plan, 0.0)
                
                print(f"  ✅ Created {num_subs} subscription(s) for '{client.name}': ${total_mrr:.0f} MRR ({plan})")
        
        await session.commit()
        
        print(f"\n✨ Summary:")
        print(f"  - Created: {created_workspaces} new workspace(s)")
        print(f"  - Created: {created_subscriptions} subscription(s)")
        
        # Show revenue distribution
        if created_subscriptions > 0:
            print(f"\n📊 Revenue Distribution:")
            from app.services.admin import get_revenue_by_segment
            result = await get_revenue_by_segment(session)
            print(f"  - Total Revenue: ${result['totalRevenue']}")
            print(f"  - Revenue by Plan:")
            for segment in result.get("revenueByPlan", []):
                print(f"    • {segment['segment']}: ${segment['revenue']} ({segment['count']} subscriptions)")
            print(f"  - Revenue by Company Size:")
            for segment in result.get("revenueByCompanySize", []):
                print(f"    • {segment['segment']}: ${segment['revenue']} ({segment['count']} customers)")


if __name__ == "__main__":
    asyncio.run(reset_and_seed_subscriptions())
