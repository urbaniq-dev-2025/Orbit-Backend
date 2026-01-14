"""Test admin endpoints to debug errors."""
import asyncio
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.services import admin


async def test_endpoints():
    """Test admin endpoints."""
    async with AsyncSessionLocal() as session:
        print("Testing get_revenue_breakdown...")
        try:
            data = await admin.get_revenue_breakdown(session)
            print("✅ SUCCESS")
            print(f"Keys: {list(data.keys())}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            traceback.print_exc()
        
        print("\nTesting get_subscriptions_list...")
        try:
            data = await admin.get_subscriptions_list(session, page=1, page_size=20)
            print("✅ SUCCESS")
            print(f"Keys: {list(data.keys())}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            traceback.print_exc()
        
        print("\nTesting get_conversion_funnel...")
        try:
            data = await admin.get_conversion_funnel(session)
            print("✅ SUCCESS")
            print(f"Keys: {list(data.keys())}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_endpoints())
