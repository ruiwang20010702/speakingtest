-- 迁移脚本：添加报告解读状态字段
-- 日期：2026-01-16
-- 说明：添加 interpretation_status 和 interpretation_retry_count 字段

-- 1. 添加 interpretation_status 列
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tests' AND column_name = 'interpretation_status'
    ) THEN
        ALTER TABLE tests ADD COLUMN interpretation_status VARCHAR(20);
        RAISE NOTICE '已添加 interpretation_status 列';
    ELSE
        RAISE NOTICE 'interpretation_status 列已存在，跳过';
    END IF;
END $$;

-- 2. 添加 interpretation_retry_count 列
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tests' AND column_name = 'interpretation_retry_count'
    ) THEN
        ALTER TABLE tests ADD COLUMN interpretation_retry_count SMALLINT DEFAULT 0;
        RAISE NOTICE '已添加 interpretation_retry_count 列';
    ELSE
        RAISE NOTICE 'interpretation_retry_count 列已存在，跳过';
    END IF;
END $$;

-- 3. 验证结果
DO $$
DECLARE
    col_count INT;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns 
    WHERE table_name = 'tests' 
    AND column_name IN ('interpretation_status', 'interpretation_retry_count');
    
    RAISE NOTICE '迁移完成！已验证 % 个新列', col_count;
END $$;
