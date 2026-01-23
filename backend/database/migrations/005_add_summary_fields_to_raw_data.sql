-- Migration: 005_add_summary_fields_to_raw_data.sql
-- Description: 将 summary_* 字段添加到 test_raw_data 表，完成大 JSON 分离
-- Author: AI Assistant
-- Date: 2026-01-23

-- ============================================
-- 1. 添加 summary_* 字段到 test_raw_data 表
-- ============================================
ALTER TABLE test_raw_data 
ADD COLUMN IF NOT EXISTS summary_highlights TEXT,
ADD COLUMN IF NOT EXISTS summary_weaknesses TEXT,
ADD COLUMN IF NOT EXISTS summary_weekly_plan TEXT,
ADD COLUMN IF NOT EXISTS summary_dimension_feedback JSONB;

-- ============================================
-- 2. 更新触发器函数，同步 summary_* 字段
-- ============================================
CREATE OR REPLACE FUNCTION sync_test_raw_data()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO test_raw_data (
        test_id, 
        part1_raw_result, part2_raw_result, tokens_used,
        interpretation_pages, interpretation_parent_script, report_override,
        summary_highlights, summary_weaknesses, summary_weekly_plan, summary_dimension_feedback,
        created_at, updated_at
    ) VALUES (
        NEW.id, 
        NEW.part1_raw_result, NEW.part2_raw_result, NEW.tokens_used,
        NEW.interpretation_pages, NEW.interpretation_parent_script, NEW.report_override,
        NEW.summary_highlights, NEW.summary_weaknesses, NEW.summary_weekly_plan, NEW.summary_dimension_feedback,
        NEW.created_at, NOW()
    )
    ON CONFLICT (test_id) DO UPDATE SET
        part1_raw_result = EXCLUDED.part1_raw_result,
        part2_raw_result = EXCLUDED.part2_raw_result,
        tokens_used = EXCLUDED.tokens_used,
        interpretation_pages = EXCLUDED.interpretation_pages,
        interpretation_parent_script = EXCLUDED.interpretation_parent_script,
        report_override = EXCLUDED.report_override,
        summary_highlights = EXCLUDED.summary_highlights,
        summary_weaknesses = EXCLUDED.summary_weaknesses,
        summary_weekly_plan = EXCLUDED.summary_weekly_plan,
        summary_dimension_feedback = EXCLUDED.summary_dimension_feedback,
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 3. 重新创建触发器，监听更多字段
-- ============================================
DROP TRIGGER IF EXISTS trg_sync_test_raw_data ON tests;

CREATE TRIGGER trg_sync_test_raw_data
    AFTER INSERT OR UPDATE OF 
        part1_raw_result, part2_raw_result, tokens_used,
        interpretation_pages, interpretation_parent_script, report_override,
        summary_highlights, summary_weaknesses, summary_weekly_plan, summary_dimension_feedback
    ON tests
    FOR EACH ROW
    EXECUTE FUNCTION sync_test_raw_data();

-- ============================================
-- 4. 迁移现有数据：从 tests 同步 summary_* 到 test_raw_data
-- ============================================
UPDATE test_raw_data rd
SET 
    summary_highlights = t.summary_highlights,
    summary_weaknesses = t.summary_weaknesses,
    summary_weekly_plan = t.summary_weekly_plan,
    summary_dimension_feedback = t.summary_dimension_feedback
FROM tests t
WHERE rd.test_id = t.id
  AND (t.summary_highlights IS NOT NULL 
       OR t.summary_weaknesses IS NOT NULL 
       OR t.summary_weekly_plan IS NOT NULL
       OR t.summary_dimension_feedback IS NOT NULL);

-- 对于 test_raw_data 中不存在的 tests 记录，插入新行
INSERT INTO test_raw_data (
    test_id, 
    part1_raw_result, part2_raw_result, tokens_used,
    interpretation_pages, interpretation_parent_script, report_override,
    summary_highlights, summary_weaknesses, summary_weekly_plan, summary_dimension_feedback,
    created_at, updated_at
)
SELECT 
    t.id,
    t.part1_raw_result, t.part2_raw_result, t.tokens_used,
    t.interpretation_pages, t.interpretation_parent_script, t.report_override,
    t.summary_highlights, t.summary_weaknesses, t.summary_weekly_plan, t.summary_dimension_feedback,
    t.created_at, NOW()
FROM tests t
WHERE NOT EXISTS (SELECT 1 FROM test_raw_data rd WHERE rd.test_id = t.id)
  AND (t.part1_raw_result IS NOT NULL 
       OR t.part2_raw_result IS NOT NULL 
       OR t.tokens_used IS NOT NULL
       OR t.interpretation_pages IS NOT NULL
       OR t.summary_highlights IS NOT NULL
       OR t.summary_weaknesses IS NOT NULL
       OR t.summary_weekly_plan IS NOT NULL
       OR t.summary_dimension_feedback IS NOT NULL);

-- ============================================
-- 5. 更新视图 v_tests_full，包含 summary_* 字段
-- ============================================
CREATE OR REPLACE VIEW v_tests_full AS
SELECT 
    t.*,
    rd.part1_raw_result AS raw_part1_raw_result,
    rd.part2_raw_result AS raw_part2_raw_result,
    rd.tokens_used AS raw_tokens_used,
    rd.interpretation_pages AS raw_interpretation_pages,
    rd.interpretation_parent_script AS raw_interpretation_parent_script,
    rd.report_override AS raw_report_override,
    rd.summary_highlights AS raw_summary_highlights,
    rd.summary_weaknesses AS raw_summary_weaknesses,
    rd.summary_weekly_plan AS raw_summary_weekly_plan,
    rd.summary_dimension_feedback AS raw_summary_dimension_feedback
FROM tests t
LEFT JOIN test_raw_data rd ON t.id = rd.test_id;

-- ============================================
-- 完成提示
-- ============================================
-- 迁移完成后，summary_* 字段会同时存在于 tests 和 test_raw_data 表
-- 代码应优先从 test_raw_data 读取，fallback 到 tests 表
-- 未来可以考虑从 tests 表移除这些字段（需要代码全面适配后）
