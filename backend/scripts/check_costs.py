import asyncio
import sys
import os
import json
from sqlalchemy import select, desc
from decimal import Decimal

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import TestModel

async def check_costs():
    async with AsyncSessionLocal() as session:
        # Get tests with cost, ordered by creation time desc
        stmt = select(TestModel).where(TestModel.cost.isnot(None)).order_by(desc(TestModel.created_at)).limit(20)
        result = await session.execute(stmt)
        tests = result.scalars().all()
        
        # Check total count
        count_stmt = select(TestModel)
        count_result = await session.execute(count_stmt)
        total_count = len(count_result.scalars().all())
        
        if not tests:
            print(f"No tests with cost data found in database. (Total tests in DB: {total_count})")
            print("Note: Cost tracking is a new feature. Older records have NULL cost.")
            return

        print(f"{'ID':<5} | {'Status':<12} | {'Cost (RMB)':<12} | {'Tokens Used':<50}")
        print("-" * 90)
        
        total_cost = Decimal(0)
        
        for test in tests:
            cost = test.cost or Decimal(0)
            total_cost += cost
            
            # Format tokens_used for display
            tokens_str = ""
            if test.tokens_used:
                # Just show total tokens for brevity if available, or a summary
                try:
                    usage = test.tokens_used
                    p1 = usage.get("part1", {}).get("total_tokens", 0)
                    p2 = usage.get("part2", {}).get("total_tokens", 0)
                    tokens_str = f"P1: {p1}, P2: {p2}"
                except:
                    tokens_str = "Invalid JSON"
            
            print(f"{test.id:<5} | {test.status:<12} | {cost:<12.6f} | {tokens_str:<50}")

        print("-" * 90)
        print(f"Total Cost (Last {len(tests)} records): {total_cost:.6f} RMB")

if __name__ == "__main__":
    asyncio.run(check_costs())
