#!/usr/bin/env python3
"""
Migration script to add report_override column to tests table.

Usage:
    cd backend
    python scripts/migrate_add_report_override.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from src.infrastructure.database import engine


async def migrate():
    """Add report_override column to tests table."""
    async with engine.begin() as conn:
        # Check if column already exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tests' AND column_name = 'report_override'
        """))
        
        if result.fetchone():
            print("Column 'report_override' already exists. Skipping.")
            return
        
        # Add the column
        print("Adding 'report_override' column to tests table...")
        await conn.execute(text("""
            ALTER TABLE tests 
            ADD COLUMN report_override JSONB DEFAULT NULL
        """))
        
        print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
