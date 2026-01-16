import asyncio
import sys
import os
import json
from sqlalchemy import select, desc

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.database import AsyncSessionLocal
from src.adapters.repositories.models import TestModel

async def inspect_results():
    async with AsyncSessionLocal() as session:
        # Get the latest test
        stmt = select(TestModel).order_by(desc(TestModel.created_at)).limit(1)
        result = await session.execute(stmt)
        test = result.scalar_one_or_none()
        
        if not test:
            print("No tests found in database.")
            return

        output = []
        output.append(f"Test ID: {test.id}")
        output.append(f"Student ID: {test.student_id}")
        output.append(f"Status: {test.status}")
        output.append("-" * 50)
        
        output.append("Part 1 Raw Result:")
        if test.part1_raw_result:
            output.append(json.dumps(test.part1_raw_result, indent=2, ensure_ascii=False))
        else:
            output.append("None")
            
        output.append("-" * 50)
        
        output.append("Part 2 Raw Result:")
        if test.part2_raw_result:
            output.append(json.dumps(test.part2_raw_result, indent=2, ensure_ascii=False))
        else:
            output.append("None")
            
        with open("db_results.txt", "w") as f:
            f.write("\n".join(output))
            
        print("Results written to db_results.txt")

if __name__ == "__main__":
    asyncio.run(inspect_results())
