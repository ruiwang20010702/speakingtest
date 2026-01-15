-- 迁移脚本：重构报告解读为按页组织
-- 日期：2025-01-15
-- 说明：将旧的 interpretation_* 字段替换为 interpretation_pages JSONB 字段

-- 1. 添加新列 interpretation_pages（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tests' AND column_name = 'interpretation_pages'
    ) THEN
        ALTER TABLE tests ADD COLUMN interpretation_pages JSONB;
        RAISE NOTICE '已添加 interpretation_pages 列';
    ELSE
        RAISE NOTICE 'interpretation_pages 列已存在，跳过';
    END IF;
END $$;

-- 2. 删除旧列（如果存在）
DO $$ 
BEGIN
    -- 删除 interpretation_highlights
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tests' AND column_name = 'interpretation_highlights'
    ) THEN
        ALTER TABLE tests DROP COLUMN interpretation_highlights;
        RAISE NOTICE '已删除 interpretation_highlights 列';
    END IF;
    
    -- 删除 interpretation_weaknesses
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tests' AND column_name = 'interpretation_weaknesses'
    ) THEN
        ALTER TABLE tests DROP COLUMN interpretation_weaknesses;
        RAISE NOTICE '已删除 interpretation_weaknesses 列';
    END IF;
    
    -- 删除 interpretation_evidence
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tests' AND column_name = 'interpretation_evidence'
    ) THEN
        ALTER TABLE tests DROP COLUMN interpretation_evidence;
        RAISE NOTICE '已删除 interpretation_evidence 列';
    END IF;
    
    -- 删除 interpretation_suggestions
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tests' AND column_name = 'interpretation_suggestions'
    ) THEN
        ALTER TABLE tests DROP COLUMN interpretation_suggestions;
        RAISE NOTICE '已删除 interpretation_suggestions 列';
    END IF;
END $$;

-- 3. 清空 interpretation_generated_at，避免系统误判"已生成但无内容"
UPDATE tests 
SET interpretation_generated_at = NULL 
WHERE interpretation_generated_at IS NOT NULL;

-- 4. 验证结果
DO $$
DECLARE
    col_count INT;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns 
    WHERE table_name = 'tests' 
    AND column_name IN ('interpretation_pages', 'interpretation_parent_script', 'interpretation_generated_at');
    
    RAISE NOTICE '迁移完成！tests 表现有 % 个 interpretation 相关列', col_count;
END $$;
