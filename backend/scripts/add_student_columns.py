import asyncio
import sys
import os

# Add backend directory to path so we can import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.infrastructure.database import engine

async def migrate():
    print("Starting migration: Adding missing columns to student_profiles...")
    
    columns = [
        ("is_upgrade", "INTEGER DEFAULT 0"),
        ("ss_name", "VARCHAR(100)"),
        ("ss_sm_name", "VARCHAR(100)"),
        ("ss_dept4_name", "VARCHAR(100)"),
        ("ss_group", "VARCHAR(100)")
    ]
    
    async with engine.begin() as conn:
        for col_name, col_type in columns:
            try:
                # PostgreSQL 9.6+ supports IF NOT EXISTS
                sql = f"ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS {col_name} {col_type};"
                print(f"Executing: {sql}")
                await conn.execute(text(sql))
            except Exception as e:
                print(f"Error adding column {col_name}: {e}")
                
    print("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
