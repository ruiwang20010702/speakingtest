import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import TestModel
from sqlalchemy import select

async def verify_schema():
    print("Verifying TestModel schema...")
    async with AsyncSessionLocal() as session:
        # Check if we can query the new column
        try:
            stmt = select(TestModel).limit(1)
            result = await session.execute(stmt)
            print("✅ Successfully queried TestModel with new column.")
        except Exception as e:
            print(f"❌ Failed to query TestModel: {e}")

if __name__ == "__main__":
    asyncio.run(verify_schema())
