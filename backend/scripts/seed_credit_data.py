"""
Script to seed credit packages and credit data for existing clients/workspaces.

This script:
1. Creates default credit packages
2. Creates credit balances for existing workspaces
3. Creates credit purchase history for existing workspaces
4. Updates credit balances based on purchases

Usage:
    python -m scripts.seed_credit_data
"""

from __future__ import annotations

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models import CreditPackage, CreditPurchase, Subscription, Workspace, WorkspaceCreditBalance


async def seed_credit_data():
    """Seed credit packages and purchase data."""
    async with AsyncSessionLocal() as session:
        print("🔄 Seeding credit data...")
        
        # 1. Create credit packages if they don't exist
        packages_data = [
            {"name": "Starter Pack", "credits": 100, "price": 10.0},
            {"name": "Growth Pack", "credits": 500, "price": 40.0},
            {"name": "Pro Pack", "credits": 2000, "price": 120.0},
            {"name": "Enterprise Pack", "credits": 10000, "price": 500.0},
        ]
        
        existing_packages_stmt = select(CreditPackage.name)
        existing_packages_result = await session.execute(existing_packages_stmt)
        existing_package_names = {row[0] for row in existing_packages_result.all()}
        
        packages_created = 0
        for pkg_data in packages_data:
            if pkg_data["name"] not in existing_package_names:
                package = CreditPackage(
                    name=pkg_data["name"],
                    credits=pkg_data["credits"],
                    price=pkg_data["price"],
                    is_active=True,
                    description=f"{pkg_data['credits']} credits for ${pkg_data['price']}",
                )
                session.add(package)
                await session.flush()  # Flush after each package
                packages_created += 1
                print(f"  ✅ Created package: {pkg_data['name']} ({pkg_data['credits']} credits, ${pkg_data['price']})")
        
        await session.commit()  # Commit packages before proceeding
        
        # Get all packages (including newly created)
        all_packages_stmt = select(CreditPackage)
        all_packages_result = await session.execute(all_packages_stmt)
        all_packages = {pkg.name: pkg for pkg in all_packages_result.scalars().all()}
        
        # 2. Get all workspaces
        workspaces_stmt = select(Workspace)
        workspaces_result = await session.execute(workspaces_stmt)
        workspaces = list(workspaces_result.scalars().all())
        
        if not workspaces:
            print("❌ No workspaces found.")
            return
        
        print(f"\n📦 Found {len(workspaces)} workspace(s)")
        
        # 3. Create credit balances and purchases for each workspace
        now = datetime.now(timezone.utc)
        purchases_created = 0
        balances_created = 0
        
        for workspace in workspaces:
            # Check if credit balance already exists
            balance_stmt = select(WorkspaceCreditBalance).where(
                WorkspaceCreditBalance.workspace_id == workspace.id
            )
            balance_result = await session.execute(balance_stmt)
            existing_balance = balance_result.scalar_one_or_none()
            
            # Create credit balance if it doesn't exist
            if not existing_balance:
                balance = WorkspaceCreditBalance(
                    workspace_id=workspace.id,
                    balance=0,
                    total_purchased=0,
                    total_consumed=0,
                )
                session.add(balance)
                balances_created += 1
                await session.flush()
                
                # Re-fetch to get the created balance
                balance_stmt = select(WorkspaceCreditBalance).where(
                    WorkspaceCreditBalance.workspace_id == workspace.id
                )
                balance_result = await session.execute(balance_stmt)
                balance = balance_result.scalar_one()
            else:
                balance = existing_balance
            
            # Create 1-3 credit purchases for this workspace (historical)
            num_purchases = random.randint(1, 3)
            total_credits_purchased = 0
            total_amount = 0.0
            
            for i in range(num_purchases):
                # Select a random package (weighted towards smaller packages)
                package_weights = [0.3, 0.4, 0.2, 0.1]  # Starter, Growth, Pro, Enterprise
                package = random.choices(
                    list(all_packages.values()),
                    weights=package_weights,
                )[0]
                
                # Purchase date: random date in last 6 months
                days_ago = random.randint(0, 180)
                purchase_date = now - timedelta(days=days_ago)
                
                # Payment method
                payment_methods = [
                    "Card •••• 4242",
                    "Card •••• 8888",
                    "PayPal",
                    "Wire Transfer",
                ]
                payment_method = random.choice(payment_methods)
                
                # Transaction ID
                transaction_id = f"txn_{random.randint(100000, 999999)}"
                
                # Status (mostly completed, some pending)
                status = "completed" if random.random() < 0.9 else "pending"
                
                purchase = CreditPurchase(
                    workspace_id=workspace.id,
                    package_id=package.id,
                    credits=package.credits,
                    amount=float(package.price),
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    status=status,
                    purchase_date=purchase_date,
                )
                session.add(purchase)
                await session.flush()  # Flush after each purchase
                purchases_created += 1
                
                if status == "completed":
                    total_credits_purchased += package.credits
                    total_amount += float(package.price)
            
            # Calculate consumed credits (random amount, less than purchased)
            consumed = random.randint(0, int(total_credits_purchased * 0.7)) if total_credits_purchased > 0 else 0
            remaining = total_credits_purchased - consumed
            
            balance.total_purchased += total_credits_purchased
            balance.total_consumed += consumed
            balance.balance = remaining
            balance.updated_at = now
            await session.flush()  # Flush balance update
        
        await session.commit()
        
        print(f"\n✨ Summary:")
        print(f"  - Packages created: {packages_created}")
        print(f"  - Credit balances created: {balances_created}")
        print(f"  - Credit purchases created: {purchases_created}")
        
        # Show summary
        summary_stmt = select(
            func.sum(WorkspaceCreditBalance.total_purchased).label("total_sold"),
            func.sum(WorkspaceCreditBalance.total_consumed).label("total_consumed"),
            func.sum(WorkspaceCreditBalance.balance).label("total_remaining"),
        )
        summary_result = await session.execute(summary_stmt)
        summary = summary_result.one()
        
        print(f"\n📊 Credit Summary:")
        print(f"  - Total Credits Sold: {summary[0] or 0:,}")
        print(f"  - Total Credits Consumed: {summary[1] or 0:,}")
        print(f"  - Total Credits Remaining: {summary[2] or 0:,}")


if __name__ == "__main__":
    asyncio.run(seed_credit_data())
