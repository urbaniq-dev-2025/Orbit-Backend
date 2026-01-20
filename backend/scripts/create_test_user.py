"""
Script to create a test user for dashboard testing.

This script creates a test user with:
- Email: test@orbit.dev
- Password: test123456
- Full name: Test User
- Verified and active

Usage:
    python -m scripts.create_test_user
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import User


async def create_test_user(session: AsyncSession):
    """Create a test user for dashboard testing using raw SQL to avoid ORM issues."""
    import uuid
    from datetime import datetime, timezone
    
    test_email = "test@orbit.dev"
    test_password = "test123456"
    test_name = "Test User"
    
    # Check if user already exists using raw SQL
    check_stmt = text("SELECT id, email, full_name, role, is_verified, is_active FROM users WHERE email = :email")
    result = await session.execute(check_stmt, {"email": test_email})
    existing = result.fetchone()
    
    if existing:
        user_id, email, full_name, role, is_verified, is_active = existing
        print(f"⚠️  User already exists: {email}")
        print(f"\n{'='*60}")
        print(f"   USER CREDENTIALS")
        print(f"{'='*60}")
        print(f"   Email:    {email}")
        print(f"   Password: {test_password}")
        print(f"   User ID:  {user_id}")
        print(f"   Full Name: {full_name}")
        print(f"   Role:     {role}")
        print(f"   Verified: {is_verified}")
        print(f"   Active:   {is_active}")
        print(f"{'='*60}\n")
        return {"id": str(user_id), "email": email}
    
    # Create new test user using raw SQL
    print(f"📝 Creating test user...")
    user_id = uuid.uuid4()
    hashed_pw = hash_password(test_password)
    now = datetime.now(timezone.utc)
    
    insert_stmt = text("""
        INSERT INTO users (id, email, hashed_password, full_name, role, is_active, is_verified, 
                          onboarding_completed, onboarding_step, created_at, updated_at)
        VALUES (:id, :email, :hashed_password, :full_name, :role, :is_active, :is_verified,
                :onboarding_completed, :onboarding_step, :created_at, :updated_at)
    """)
    
    await session.execute(insert_stmt, {
        "id": user_id,
        "email": test_email,
        "hashed_password": hashed_pw,
        "full_name": test_name,
        "role": "user",
        "is_active": True,
        "is_verified": True,
        "onboarding_completed": True,
        "onboarding_step": "completed",
        "created_at": now,
        "updated_at": now,
    })
    await session.commit()
    
    print(f"\n✅ Test user created successfully!")
    print(f"\n{'='*60}")
    print(f"   USER CREDENTIALS")
    print(f"{'='*60}")
    print(f"   Email:    {test_email}")
    print(f"   Password: {test_password}")
    print(f"   User ID:  {user_id}")
    print(f"   Full Name: {test_name}")
    print(f"   Role:     user")
    print(f"{'='*60}\n")
    
    return {"id": str(user_id), "email": test_email}


async def main():
    """Main function to create test user."""
    async with AsyncSessionLocal() as session:
        try:
            user_info = await create_test_user(session)
            print(f"✅ Success! You can now login with:")
            print(f"   Email: {user_info['email']}")
            print(f"   Password: test123456")
            print(f"   User ID: {user_info['id']}")
        except Exception as e:
            print(f"❌ Error creating test user: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
