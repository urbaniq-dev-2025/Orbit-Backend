"""
Script to seed subscriptions for existing workspaces to enable geographic revenue tracking.

This script creates subscriptions for all existing workspaces with:
- Realistic plan distribution (more free/starter, fewer enterprise)
- Active status for most subscriptions
- Proper billing cycles and period dates
- Links to existing clients for geographic data

Usage:
    python -m scripts.seed_subscriptions_for_revenue
"""

from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import Subscription, Workspace, Client


async def seed_subscriptions():
    """Create subscriptions for existing workspaces."""
    async with AsyncSessionLocal() as session:
        # Get all workspaces
        workspaces_result = await session.execute(select(Workspace))
        workspaces = workspaces_result.scalars().all()
        
        if not workspaces:
            print("❌ No workspaces found. Please create a workspace first.")
            return
        
        print(f"📦 Found {len(workspaces)} workspace(s)")
        
        # Plan distribution weights (more free/starter, fewer enterprise)
        plans = ['free', 'starter', 'pro', 'team', 'enterprise']
        plan_weights = [0.3, 0.3, 0.2, 0.15, 0.05]  # 30% free, 30% starter, etc.
        
        created_count = 0
        skipped_count = 0
        
        for workspace in workspaces:
            # Check if subscription already exists
            existing_result = await session.execute(
                select(Subscription).where(Subscription.workspace_id == workspace.id)
            )
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                print(f"  ⏭️  Workspace '{workspace.name}' already has a subscription")
                skipped_count += 1
                continue
            
            # Randomly assign plan based on weights
            plan = random.choices(plans, weights=plan_weights)[0]
            
            # Set status (90% active, 10% cancelled/trialing)
            status_roll = random.random()
            if status_roll < 0.9:
                status = 'active'
            elif status_roll < 0.95:
                status = 'trialing'
            else:
                status = 'cancelled'
            
            # Set billing cycle (80% monthly, 20% annual)
            billing_cycle = 'monthly' if random.random() < 0.8 else 'annual'
            
            # Set period dates
            now = datetime.now(timezone.utc)
            period_start = now - timedelta(days=random.randint(0, 30))
            
            if billing_cycle == 'monthly':
                period_end = period_start + timedelta(days=30)
            else:
                period_end = period_start + timedelta(days=365)
            
            # Create subscription
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
            created_count += 1
            
            # Get clients for this workspace to show location
            clients_result = await session.execute(
                select(Client).where(Client.workspace_id == workspace.id)
            )
            clients = clients_result.scalars().all()
            client_info = f" ({len(clients)} client(s))" if clients else " (no clients)"
            
            print(f"  ✅ Created subscription for '{workspace.name}': {plan} plan, {status} status{client_info}")
        
        await session.commit()
        
        print(f"\n✨ Summary:")
        print(f"  - Created: {created_count} subscription(s)")
        print(f"  - Skipped: {skipped_count} workspace(s) (already have subscriptions)")
        
        # Show geographic distribution
        if created_count > 0:
            print(f"\n🌍 Geographic Revenue Preview:")
            from app.services.admin import get_geographic_revenue
            result = await get_geographic_revenue(session)
            print(f"  - Total Revenue: ${result['totalRevenue']}")
            print(f"  - Countries: {len(result['revenueByCountry'])}")
            if result['revenueByCountry']:
                print(f"  - Top Countries:")
                for country_data in result['revenueByCountry'][:3]:
                    print(f"    • {country_data['country']} ({country_data.get('countryCode', 'N/A')}): ${country_data['revenue']}")


if __name__ == "__main__":
    asyncio.run(seed_subscriptions())
