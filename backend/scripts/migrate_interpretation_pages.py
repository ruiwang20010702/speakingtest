#!/usr/bin/env python3
"""
Migration: Refactor interpretation fields to page-based structure.

Changes:
- Add interpretation_pages (JSONB) column
- Remove old columns: interpretation_highlights, interpretation_weaknesses, 
  interpretation_evidence, interpretation_suggestions
- Clear interpretation_generated_at to avoid false "already generated" status
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
        print("=" * 50)
        print("迁移：重构报告解读为按页组织")
        print("=" * 50)
        
        # Step 1: Add interpretation_pages column if not exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tests' AND column_name = 'interpretation_pages'
        """))
        
        if not result.fetchone():
            print("\n[1/4] 添加 interpretation_pages 列...")
            await conn.execute(text("""
                ALTER TABLE tests 
                ADD COLUMN interpretation_pages JSONB DEFAULT NULL
            """))
            print("  ✓ 已添加 interpretation_pages (JSONB)")
        else:
            print("\n[1/4] interpretation_pages 列已存在，跳过")
        
        # Step 2: Drop old columns if they exist
        old_columns = [
            'interpretation_highlights',
            'interpretation_weaknesses', 
            'interpretation_evidence',
            'interpretation_suggestions'
        ]
        
        print("\n[2/4] 删除旧的 interpretation 列...")
        for col in old_columns:
            result = await conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tests' AND column_name = '{col}'
            """))
            
            if result.fetchone():
                await conn.execute(text(f"""
                    ALTER TABLE tests DROP COLUMN {col}
                """))
                print(f"  ✓ 已删除 {col}")
            else:
                print(f"  - {col} 不存在，跳过")
        
        # Step 3: Clear interpretation_generated_at to avoid false positives
        print("\n[3/4] 清空 interpretation_generated_at...")
        result = await conn.execute(text("""
            UPDATE tests 
            SET interpretation_generated_at = NULL 
            WHERE interpretation_generated_at IS NOT NULL
            RETURNING id
        """))
        count = len(result.fetchall())
        print(f"  ✓ 已清空 {count} 条记录的 interpretation_generated_at")
        
        # Step 4: Verify final structure
        print("\n[4/4] 验证最终结构...")
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tests' 
            AND column_name LIKE 'interpretation%'
            ORDER BY column_name
        """))
        columns = [row[0] for row in result.fetchall()]
        print(f"  现有 interpretation 相关列: {columns}")
        
        print("\n" + "=" * 50)
        print("迁移完成！")
        print("=" * 50)
        print('\n注意：历史已生成的解读已被清空，需要在教师端重新点击"生成报告解读"')


if __name__ == "__main__":
    asyncio.run(migrate())
