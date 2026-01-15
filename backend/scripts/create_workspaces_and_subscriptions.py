"""
Script to create separate workspaces for clients and add subscriptions with varied revenue.

This script:
1. Gets all clients
2. Creates a new workspace for each client (or groups clients by company size)
3. Moves clients to their new workspaces
4. Creates subscriptions with varied plans based on company size
5. Ensures all segments have multiple entries with varied revenue

Usage:
    python -m scripts.create_workspaces_and_subscriptions
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Client, Subscription, User, Workspace, WorkspaceMember
from app.services.workspaces import create_workspace


async def create_workspaces_and_subscriptions():
    """Create workspaces for clients and add subscriptions."""
    async with AsyncSessionLocal() as session:
        # Get admin user (or first user)
        user_result = await session.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            print("❌ No user found. Please create a user first.")
            return
        
        print(f"👤 Using user: {user.email}")
        
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
        
        # Company size to plan mapping
        company_size_plans = {
            "Enterprise": [
                ("enterprise", 0.5),
                ("team", 0.4),
                ("pro", 0.1),
            ],
            "Mid-Market": [
                ("team", 0.3),
                ("pro", 0.6),
                ("starter", 0.1),
            ],
            "SMB": [
                ("pro", 0.5),
                ("starter", 0.4),
                ("free", 0.1),
            ],
        }
        
        created_workspaces = 0
        created_subscriptions = 0
        
        # Group clients by company size for better distribution
        clients_by_size = {}
        for client in all_clients:
            size = client.company_size or "SMB"
            if size not in clients_by_size:
                clients_by_size[size] = []
            clients_by_size[size].append(client)
        
        # Create workspaces and subscriptions
        for company_size, clients in clients_by_size.items():
            print(f"\n🏢 Processing {company_size} clients ({len(clients)}):")
            
            for client in clients:
                # Check if client already has a workspace with subscription
                existing_subs_result = await session.execute(
                    select(Subscription)
                    .join(Workspace, Subscription.workspace_id == Workspace.id)
                    .where(Workspace.id == client.workspace_id)
                    .where(Subscription.status == "active")
                )
                existing_subs = existing_subs_result.scalars().all()
                
                if existing_subs:
                    print(f"  ⏭️  '{client.name}' already has {len(existing_subs)} active subscription(s), skipping")
                    continue
                
                # Create a new workspace for this client
                workspace_name = f"{client.name} Workspace"
                workspace = await create_workspace(
                    session,
                    owner_id=user.id,
                    name=workspace_name,
                )
                await session.flush()
                created_workspaces += 1
                
                # Move client to new workspace
                old_workspace_id = client.workspace_id
                client.workspace_id = workspace.id
                await session.flush()
                
                # Create workspace membership if needed
                member_result = await session.execute(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == workspace.id,
                        WorkspaceMember.user_id == user.id
                    )
                )
                if not member_result.scalar_one_or_none():
                    member = WorkspaceMember(
                        workspace_id=workspace.id,
                        user_id=user.id,
                        role="owner",
                        status="active",
                        joined_at=datetime.now(timezone.utc),
                    )
                    session.add(member)
                
                # Determine number of subscriptions (Enterprise gets more)
                if company_size == "Enterprise":
                    num_subs = random.randint(1, 2)  # 1-2 subscriptions
                elif company_size == "Mid-Market":
                    num_subs = 1
                else:  # SMB
                    num_subs = 1
                
                # Get plan distribution for this company size
                plan_options = company_size_plans.get(company_size, company_size_plans["SMB"])
                plans = [plan for plan, _ in plan_options]
                weights = [weight for _, weight in plan_options]
                
                # Create subscriptions
                total_mrr = 0.0
                for i in range(num_subs):
                    plan = random.choices(plans, weights=weights)[0]
                    status = "active"
                    billing_cycle = "monthly" if random.random() < 0.8 else "annual"
                    
                    now = datetime.now(timezone.utc)
                    period_start = now - timedelta(days=random.randint(0, 30))
                    period_end = period_start + timedelta(days=30 if billing_cycle == "monthly" else 365)
                    
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
                
                print(f"  ✅ Created workspace + {num_subs} subscription(s) for '{client.name}': ${total_mrr:.0f} MRR")
        
        await session.commit()
        
        print(f"\n✨ Summary:")
        print(f"  - Created: {created_workspaces} workspace(s)")
        print(f"  - Created: {created_subscriptions} subscription(s)")
        
        # Show revenue distribution
        if created_subscriptions > 0:
            print(f"\n📊 Revenue Distribution:")
            from app.services.admin import get_revenue_by_segment
            result = await get_revenue_by_segment(session)
            print(f"  - Total Revenue: ${result['totalRevenue']}")
            print(f"  - Revenue by Company Size:")
            for segment in result.get("revenueByCompanySize", []):
                print(f"    • {segment['segment']}: ${segment['revenue']} ({segment['count']} customers)")


if __name__ == "__main__":
    asyncio.run(create_workspaces_and_subscriptions())
