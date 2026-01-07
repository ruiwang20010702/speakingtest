import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.infrastructure.database import engine

async def migrate():
    async with engine.begin() as conn:
        print("Adding view_count column to report_share_tokens table...")
        try:
            await conn.execute(text("ALTER TABLE report_share_tokens ADD COLUMN view_count INTEGER DEFAULT 0"))
            print("Migration successful!")
        except Exception as e:
            if "duplicate column" in str(e):
                print("Column already exists.")
            else:
                print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
