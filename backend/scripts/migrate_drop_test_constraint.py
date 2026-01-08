import asyncio
from sqlalchemy import text
from src.infrastructure.database import engine

async def migrate():
    async with engine.begin() as conn:
        # Drop the unique constraint
        # Note: The constraint name is 'uk_student_level_unit'
        try:
            await conn.execute(text("ALTER TABLE tests DROP CONSTRAINT uk_student_level_unit"))
            print("Successfully dropped constraint 'uk_student_level_unit'")
        except Exception as e:
            print(f"Error dropping constraint (might not exist): {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
