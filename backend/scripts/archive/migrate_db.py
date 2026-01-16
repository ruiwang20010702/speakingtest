import asyncio
import sys
import os
from sqlalchemy import text

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from src.infrastructure.database import AsyncSessionLocal

async def migrate():
    print("Starting migration...")
    async with AsyncSessionLocal() as session:
        try:
            # Add column if not exists
            sql = text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS part2_raw_result JSONB;")
            await session.execute(sql)
            await session.commit()
            print("✅ Migration successful: Added part2_raw_result column.")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate())
