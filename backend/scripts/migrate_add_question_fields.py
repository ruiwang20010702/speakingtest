"""
Database migration script to add translation and image_url columns to questions table.
Run this script to update the database schema.
"""
import asyncio
from sqlalchemy import text
from src.infrastructure.database import engine


async def migrate():
    """Add new columns to questions table."""
    async with engine.begin() as conn:
        # Check if columns exist first
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'questions' AND column_name IN ('translation', 'image_url')
        """))
        existing_columns = [row[0] for row in result.fetchall()]
        
        if 'translation' not in existing_columns:
            print("Adding 'translation' column...")
            await conn.execute(text("""
                ALTER TABLE questions 
                ADD COLUMN translation VARCHAR(100) NULL
            """))
            print("✅ Added 'translation' column")
        else:
            print("⏭️ 'translation' column already exists")
        
        if 'image_url' not in existing_columns:
            print("Adding 'image_url' column...")
            await conn.execute(text("""
                ALTER TABLE questions 
                ADD COLUMN image_url VARCHAR(500) NULL
            """))
            print("✅ Added 'image_url' column")
        else:
            print("⏭️ 'image_url' column already exists")
        
        print("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
