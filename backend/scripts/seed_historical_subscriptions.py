"""
Script to seed historical subscription data for revenue breakdown.

This script creates subscriptions with historical dates to populate:
- Revenue by Plan (current)
- MRR Breakdown (last 6 months)
- Revenue Trend (last 6 months)

It creates subscriptions with varied start dates over the past 6 months
to show growth trends in the revenue breakdown API.

Usage:
    python -m scripts.seed_historical_subscriptions
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
from app.models import Client, Subscription, User, Workspace


async def seed_historical_subscriptions():
    """Create historical subscriptions for revenue breakdown visualization."""
    async with AsyncSessionLocal() as session:
        # Get admin user
        user_result = await session.execute(select(User).limit(1))
        user = user_result.scalar_one_or_none()
        
        if not user:
            print("❌ No user found.")
            return
        
        print(f"👤 Using user: {user.email}")
        
        # Get all workspaces
        workspaces_result = await session.execute(select(Workspace))
        workspaces = workspaces_result.scalars().all()
        
        if not workspaces:
            print("❌ No workspaces found.")
            return
        
        print(f"📦 Found {len(workspaces)} workspace(s)")
        
        # Plan pricing mapping
        plan_pricing = {
            "free": 0.0,
            "starter": 24.0,
            "pro": 48.0,
            "team": 120.0,
            "enterprise": 500.0,
        }
        
        # Plans distribution
        plans = ["free", "starter", "pro", "team", "enterprise"]
        plan_weights = [0.1, 0.2, 0.4, 0.2, 0.1]  # More pro plans
        
        # Get current date
        now = datetime.now(timezone.utc)
        
        # Create subscriptions for each of the last 6 months
        created_count = 0
        
        for month_offset in range(6):
            # Calculate month start and end (timezone-aware)
            month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc) - timedelta(days=30 * month_offset)
            month_end = month_start + timedelta(days=30)
            
            # Number of subscriptions to create for this month (growing over time)
            # More recent months have more subscriptions (showing growth)
            base_count = 2
            subscriptions_for_month = base_count + (5 - month_offset)  # 7, 6, 5, 4, 3, 2
            
            print(f"\n📅 Creating subscriptions for {month_start.strftime('%Y-%m')}:")
            
            for i in range(subscriptions_for_month):
                # Select a workspace (cycle through them)
                workspace = workspaces[i % len(workspaces)]
                
                # Check if subscription already exists for this workspace in this period
                existing_result = await session.execute(
                    select(Subscription).where(
                        Subscription.workspace_id == workspace.id,
                        Subscription.created_at >= month_start,
                        Subscription.created_at < month_end,
                    )
                )
                if existing_result.scalar_one_or_none():
                    continue
                
                # Select plan
                plan = random.choices(plans, weights=plan_weights)[0]
                
                # Set status (most should be active, some cancelled for churn)
                if month_offset == 0:  # Current month - all active
                    status = "active"
                elif random.random() < 0.85:  # 85% active for past months
                    status = "active"
                else:
                    status = "cancelled"
                
                # Set billing cycle
                billing_cycle = "monthly" if random.random() < 0.8 else "annual"
                
                # Set period dates
                # Subscription created sometime during this month
                days_into_month = random.randint(0, 29)
                created_at = month_start.replace(tzinfo=timezone.utc) + timedelta(days=days_into_month)
                
                if billing_cycle == "monthly":
                    period_start = created_at
                    period_end = period_start + timedelta(days=30)
                else:
                    period_start = created_at
                    period_end = period_start + timedelta(days=365)
                
                # If cancelled, set period_end to sometime in the past
                if status == "cancelled" and month_offset > 0:
                    # Cancelled sometime after creation but before now
                    days_diff = (now - created_at).total_seconds() / 86400  # Convert to days
                    cancelled_days_after = random.randint(1, min(180, int(days_diff)))
                    period_end = created_at + timedelta(days=cancelled_days_after)
                
                subscription = Subscription(
                    workspace_id=workspace.id,
                    plan=plan,
                    billing_cycle=billing_cycle,
                    status=status,
                    current_period_start=period_start,
                    current_period_end=period_end if status == "active" else None,
                    cancel_at_period_end=False,
                    created_at=created_at,
                    updated_at=created_at if status == "active" else period_end,
                )
                
                session.add(subscription)
                await session.flush()
                created_count += 1
                
                mrr = plan_pricing.get(plan, 0.0)
                print(f"  ✅ Created {plan} subscription for '{workspace.name}': ${mrr}/month ({status}) - {created_at.strftime('%Y-%m-%d')}")
        
        await session.commit()
        
        print(f"\n✨ Summary:")
        print(f"  - Created: {created_count} historical subscription(s)")
        
        # Show revenue breakdown preview
        if created_count > 0:
            print(f"\n📊 Revenue Breakdown Preview:")
            from app.services.admin import get_revenue_breakdown
            result = await get_revenue_breakdown(session)
            print(f"  - Total MRR: ${result['totalMrr']}")
            print(f"  - Total ARR: ${result['totalArr']}")
            print(f"  - Revenue by Plan:")
            for plan_data in result.get("revenueByPlan", []):
                print(f"    • {plan_data['plan']}: ${plan_data['revenue']} ({plan_data['count']} subscriptions)")
            print(f"  - MRR Breakdown (last 6 months):")
            for month_data in result.get("mrrBreakdown", []):
                print(f"    • {month_data['month']}: ${month_data['mrr']}")


if __name__ == "__main__":
    asyncio.run(seed_historical_subscriptions())
