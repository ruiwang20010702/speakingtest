import asyncio
import sys
import os

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from src.infrastructure.database import AsyncSessionLocal

async def migrate_questions():
    async with AsyncSessionLocal() as session:
        try:
            print("Migrating questions table...")
            
            # 1. Add columns
            print("Adding 'part' column...")
            await session.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS part INTEGER DEFAULT 2 NOT NULL;"))
            
            print("Adding 'type' column...")
            await session.execute(text("ALTER TABLE questions ADD COLUMN IF NOT EXISTS type VARCHAR(20) DEFAULT 'question_answer' NOT NULL;"))
            
            # 2. Update constraints
            # Drop old constraint if exists
            print("Dropping old constraint...")
            try:
                await session.execute(text("ALTER TABLE questions DROP CONSTRAINT IF EXISTS uk_level_unit_question;"))
            except Exception as e:
                print(f"Warning dropping constraint: {e}")

            # Add new constraint
            print("Adding new constraint...")
            try:
                await session.execute(text("ALTER TABLE questions ADD CONSTRAINT uk_level_unit_part_question UNIQUE (level, unit, part, question_no);"))
            except Exception as e:
                print(f"Warning adding constraint (might already exist): {e}")

            await session.commit()
            print("Migration completed successfully!")
        except Exception as e:
            print(f"Error: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate_questions())
