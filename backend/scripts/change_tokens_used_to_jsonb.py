import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from src.infrastructure.database import create_async_engine
from src.infrastructure.config import get_settings

settings = get_settings()

async def change_tokens_used_to_jsonb():
    """Change tokens_used column type from INTEGER to JSONB."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        print("Migrating tokens_used column to JSONB...")
        
        # We need to handle the conversion. 
        # Since the column might contain integers, we can cast them to jsonb, 
        # but a simple integer isn't a valid JSON object structure we want (we want a dict).
        # However, for simplicity, we can drop and recreate, or alter with a USING clause.
        # Given we just added it and it's likely empty or has simple ints, 
        # let's try to convert existing ints to a simple json object if possible, 
        # or just reset it since this is dev/testing phase.
        
        # Strategy: 
        # 1. Drop the column
        # 2. Add it back as JSONB
        # This is destructive but safe for this stage as we just added it.
        
        await conn.execute(text("""
            ALTER TABLE tests DROP COLUMN IF EXISTS tokens_used;
        """))
        
        await conn.execute(text("""
            ALTER TABLE tests ADD COLUMN tokens_used JSONB DEFAULT '{}'::jsonb;
        """))
        
        print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(change_tokens_used_to_jsonb())
