import asyncio
import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from src.infrastructure.database import AsyncSessionLocal

async def add_column():
    async with AsyncSessionLocal() as session:
        try:
            print("Adding main_last_buy_unit_name column...")
            await session.execute(text("ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS main_last_buy_unit_name VARCHAR(100);"))
            await session.commit()
            print("Column added successfully!")
        except Exception as e:
            print(f"Error: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(add_column())
