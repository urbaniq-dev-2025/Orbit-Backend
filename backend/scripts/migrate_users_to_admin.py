"""
Script to migrate existing users to admin role based on ADMIN_EMAILS configuration.

This script should be run after the migration 20260120_0007_add_user_role.py
to set admin role for users whose emails are in ADMIN_EMAILS.

Usage:
    python -m scripts.migrate_users_to_admin
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models import User


async def migrate_users_to_admin():
    """Migrate users to admin role based on ADMIN_EMAILS config."""
    settings = get_settings()
    
    # Get admin emails from config
    admin_emails = settings.admin_emails
    if isinstance(admin_emails, str):
        admin_emails = [email.strip() for email in admin_emails.split(",") if email.strip()]
    elif not isinstance(admin_emails, list):
        admin_emails = []
    
    if not admin_emails:
        print("⚠️  No admin emails configured in ADMIN_EMAILS environment variable.")
        print("   Add ADMIN_EMAILS=admin@orbit.dev to your .env file")
        return
    
    async with AsyncSessionLocal() as session:
        try:
            # Find users with admin emails
            stmt = select(User).where(User.email.in_(admin_emails))
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            updated_count = 0
            for user in users:
                if user.role != "admin":
                    print(f"📝 Updating {user.email} to admin role...")
                    user.role = "admin"
                    updated_count += 1
                else:
                    print(f"✅ {user.email} already has admin role")
            
            # Check for emails in config that don't exist as users
            found_emails = {user.email.lower() for user in users}
            missing_emails = [email for email in admin_emails if email.lower() not in found_emails]
            
            if missing_emails:
                print(f"\n⚠️  Warning: These admin emails are configured but don't exist as users:")
                for email in missing_emails:
                    print(f"   - {email}")
            
            if updated_count > 0:
                await session.commit()
                print(f"\n✅ Updated {updated_count} user(s) to admin role")
            else:
                print("\n✅ All admin users already have admin role")
            
            print(f"\n📊 Summary:")
            print(f"   Admin emails configured: {len(admin_emails)}")
            print(f"   Users found: {len(users)}")
            print(f"   Updated to admin: {updated_count}")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(migrate_users_to_admin())
