#!/usr/bin/env python3
"""
Migration: Add summary_dimension_feedback field to tests table.

This field stores AI-generated dimension feedback for the radar chart.
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
        # Check if column already exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tests' AND column_name = 'summary_dimension_feedback'
        """))
        
        if result.fetchone():
            print("summary_dimension_feedback column already exists. Skipping.")
            return
        
        print("Adding summary_dimension_feedback column to tests table...")
        
        # Add summary_dimension_feedback
        await conn.execute(text("""
            ALTER TABLE tests 
            ADD COLUMN summary_dimension_feedback JSONB DEFAULT NULL
        """))
        print("  ✓ Added summary_dimension_feedback (JSONB)")
        
        print("\nMigration completed successfully!")
        print("此字段用于存储 AI 生成的五维能力评语，将显示在家长端雷达图中")


if __name__ == "__main__":
    asyncio.run(migrate())
