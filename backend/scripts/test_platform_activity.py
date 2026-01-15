"""Test platform activity endpoint to debug errors."""
import asyncio
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.services import admin


async def test_platform_activity():
    """Test platform activity endpoint."""
    async with AsyncSessionLocal() as session:
        print("Testing get_platform_activity...")
        try:
            data = await admin.get_platform_activity(session)
            print("✅ SUCCESS")
            print(f"Keys: {list(data.keys())}")
            print(f"Total Actions: {data.get('totalActions', 'N/A')}")
            print(f"Activity Heatmap Items: {len(data.get('activityHeatmap', []))}")
            print(f"Hourly Heatmap Items: {len(data.get('hourlyActivityHeatmap', []))}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_platform_activity())
