import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import TestModel
from sqlalchemy import select, desc

async def check_db_time():
    print("Querying latest test records...")
    async with AsyncSessionLocal() as session:
        # Get last 5 tests
        stmt = select(TestModel).order_by(desc(TestModel.created_at)).limit(5)
        result = await session.execute(stmt)
        tests = result.scalars().all()
        
        if not tests:
            print("No test records found.")
            return

        print(f"{'ID':<5} | {'Status':<12} | {'Created At (UTC)':<20} | {'Created At (UTC+8)':<20}")
        print("-" * 65)
        
        for test in tests:
            created_at_utc = test.created_at
            # Manual conversion to UTC+8
            created_at_cn = created_at_utc + timedelta(hours=8) if created_at_utc else None
            
            utc_str = created_at_utc.strftime('%Y-%m-%d %H:%M:%S') if created_at_utc else "N/A"
            cn_str = created_at_cn.strftime('%Y-%m-%d %H:%M:%S') if created_at_cn else "N/A"
            
            print(f"{test.id:<5} | {test.status:<12} | {utc_str:<20} | {cn_str:<20}")

if __name__ == "__main__":
    asyncio.run(check_db_time())
