#!/usr/bin/env python3
"""
Migration: Add summary analysis fields to tests table.

These fields store the parent-facing "测评汇总分析" generated after test completion.
"""
import asyncio
import sys
from pathlib import Path

# Add both parent and src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from src.infrastructure.database import engine


async def migrate():
    async with engine.begin() as conn:
        # Check if columns already exist
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tests' AND column_name = 'summary_highlights'
        """))
        
        if result.fetchone():
            print("Summary analysis columns already exist. Skipping.")
            return
        
        print("Adding summary analysis columns to tests table...")
        
        # Add summary_highlights
        await conn.execute(text("""
            ALTER TABLE tests 
            ADD COLUMN summary_highlights TEXT DEFAULT NULL
        """))
        print("  ✓ Added summary_highlights")
        
        # Add summary_weaknesses
        await conn.execute(text("""
            ALTER TABLE tests 
            ADD COLUMN summary_weaknesses TEXT DEFAULT NULL
        """))
        print("  ✓ Added summary_weaknesses")
        
        # Add summary_weekly_plan
        await conn.execute(text("""
            ALTER TABLE tests 
            ADD COLUMN summary_weekly_plan TEXT DEFAULT NULL
        """))
        print("  ✓ Added summary_weekly_plan")
        
        # Add summary_generated_at
        await conn.execute(text("""
            ALTER TABLE tests 
            ADD COLUMN summary_generated_at TIMESTAMPTZ DEFAULT NULL
        """))
        print("  ✓ Added summary_generated_at")
        
        print("\nMigration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
