"""
Script to create subscriptions for all clients with varied plans and revenue.

This script:
1. Gets all clients grouped by workspace
2. Creates subscriptions with plans appropriate to their company size:
   - Enterprise: enterprise, team plans (higher revenue)
   - Mid-Market: team, pro plans (medium revenue)
   - SMB: pro, starter plans (lower revenue)
3. Creates multiple subscriptions per workspace to show varied distribution
4. Ensures all company size segments have multiple entries

Usage:
    python -m scripts.seed_subscriptions_for_all_clients
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
from app.models import Client, Subscription, Workspace


async def seed_subscriptions_for_all_clients():
    """Create subscriptions for all clients with varied plans based on company size."""
    async with AsyncSessionLocal() as session:
        # Get all clients with their workspaces
        clients_result = await session.execute(
            select(Client, Workspace)
            .join(Workspace, Client.workspace_id == Workspace.id)
            .order_by(Client.company_size, Client.name)
        )
        client_workspace_pairs = clients_result.all()
        
        if not client_workspace_pairs:
            print("❌ No clients found.")
            return
        
        print(f"📦 Found {len(client_workspace_pairs)} client(s)")
        
        # Plan pricing mapping
        plan_pricing = {
            "free": 0.0,
            "starter": 24.0,
            "pro": 48.0,
            "team": 120.0,
            "enterprise": 500.0,
        }
        
        # Company size to plan mapping (with weights for variety)
        company_size_plans = {
            "Enterprise": [
                ("enterprise", 0.4),  # 40% enterprise
                ("team", 0.5),        # 50% team
                ("pro", 0.1),         # 10% pro
            ],
            "Mid-Market": [
                ("team", 0.3),        # 30% team
                ("pro", 0.6),         # 60% pro
                ("starter", 0.1),     # 10% starter
            ],
            "SMB": [
                ("pro", 0.4),         # 40% pro
                ("starter", 0.5),     # 50% starter
                ("free", 0.1),        # 10% free
            ],
        }
        
        # Group clients by workspace
        workspace_clients = {}
        for client, workspace in client_workspace_pairs:
            if workspace.id not in workspace_clients:
                workspace_clients[workspace.id] = {
                    "workspace": workspace,
                    "clients": [],
                }
            workspace_clients[workspace.id]["clients"].append(client)
        
        created_count = 0
        skipped_count = 0
        
        # Create subscriptions for each workspace
        for workspace_id, ws_data in workspace_clients.items():
            workspace = ws_data["workspace"]
            clients = ws_data["clients"]
            
            # Get primary client (first active, or first client)
            active_clients = [c for c in clients if c.status == "active"]
            primary_client = active_clients[0] if active_clients else clients[0]
            company_size = primary_client.company_size or "SMB"
            
            # Check existing subscriptions
            existing_result = await session.execute(
                select(Subscription).where(Subscription.workspace_id == workspace_id)
            )
            existing_subs = existing_result.scalars().all()
            
            if existing_subs:
                print(f"  ⏭️  Workspace '{workspace.name}' already has {len(existing_subs)} subscription(s), skipping")
                skipped_count += 1
                continue
            
            # Determine how many subscriptions to create for this workspace
            # Enterprise: 2-3 subscriptions, Mid-Market: 1-2, SMB: 1
            if company_size == "Enterprise":
                num_subs = random.randint(2, 3)
            elif company_size == "Mid-Market":
                num_subs = random.randint(1, 2)
            else:  # SMB
                num_subs = 1
            
            # Get plan distribution for this company size
            plan_options = company_size_plans.get(company_size, company_size_plans["SMB"])
            plans = [plan for plan, _ in plan_options]
            weights = [weight for _, weight in plan_options]
            
            # Create subscriptions
            for i in range(num_subs):
                # Select plan based on weights
                plan = random.choices(plans, weights=weights)[0]
                
                # Set status (90% active, 10% trialing)
                status = "active" if random.random() < 0.9 else "trialing"
                
                # Set billing cycle (80% monthly, 20% annual)
                billing_cycle = "monthly" if random.random() < 0.8 else "annual"
                
                # Set period dates
                now = datetime.now(timezone.utc)
                period_start = now - timedelta(days=random.randint(0, 30))
                
                if billing_cycle == "monthly":
                    period_end = period_start + timedelta(days=30)
                else:
                    period_end = period_start + timedelta(days=365)
                
                subscription = Subscription(
                    workspace_id=workspace_id,
                    plan=plan,
                    billing_cycle=billing_cycle,
                    status=status,
                    current_period_start=period_start,
                    current_period_end=period_end,
                    cancel_at_period_end=False,
                )
                
                session.add(subscription)
                await session.flush()
                created_count += 1
            
            mrr_total = sum(plan_pricing.get(plan, 0.0) for plan in [random.choices(plans, weights=weights)[0] for _ in range(num_subs)])
            print(f"  ✅ Created {num_subs} subscription(s) for '{workspace.name}' ({company_size}): Total MRR ~${mrr_total:.0f}")
        
        await session.commit()
        
        print(f"\n✨ Summary:")
        print(f"  - Created: {created_count} subscription(s)")
        print(f"  - Skipped: {skipped_count} workspace(s) (already have subscriptions)")
        
        # Show revenue distribution by company size
        if created_count > 0:
            print(f"\n📊 Revenue Distribution Preview:")
            from app.services.admin import get_revenue_by_segment
            result = await get_revenue_by_segment(session)
            print(f"  - Total Revenue: ${result['totalRevenue']}")
            print(f"  - Revenue by Company Size:")
            for segment in result.get("revenueByCompanySize", []):
                print(f"    • {segment['segment']}: ${segment['revenue']} ({segment['count']} customers)")


if __name__ == "__main__":
    asyncio.run(seed_subscriptions_for_all_clients())
