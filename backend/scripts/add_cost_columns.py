import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from src.infrastructure.database import create_async_engine
from src.infrastructure.config import get_settings

settings = get_settings()

async def add_cost_columns():
    """Add cost and tokens_used columns to tests table."""
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Check if columns exist
        print("Checking for existing columns...")
        
        # Add cost column
        await conn.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='tests' AND column_name='cost') THEN
                    ALTER TABLE tests ADD COLUMN cost NUMERIC(10, 6);
                    RAISE NOTICE 'Added cost column';
                END IF;
            END $$;
        """))
        
        # Add tokens_used column
        await conn.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                             WHERE table_name='tests' AND column_name='tokens_used') THEN
                    ALTER TABLE tests ADD COLUMN tokens_used INTEGER;
                    RAISE NOTICE 'Added tokens_used column';
                END IF;
            END $$;
        """))
        
        print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(add_cost_columns())
