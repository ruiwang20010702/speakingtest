-- Migration: 006_create_tests_archive_tables.sql
-- Description: 创建 tests 归档表，用于存储历史测评记录
-- Author: AI Assistant
-- Date: 2026-01-23

-- ============================================
-- 1. 创建 tests_archive 表
-- ============================================
CREATE TABLE IF NOT EXISTS tests_archive (
    id BIGSERIAL PRIMARY KEY,
    original_id BIGINT NOT NULL,              -- 原始 tests.id
    student_id BIGINT NOT NULL,               -- 不设外键，允许学生删除后归档仍存在
    level VARCHAR(20) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_score NUMERIC(5, 2),
    part1_score NUMERIC(5, 2),
    part2_score NUMERIC(5, 2),
    star_level SMALLINT,
    part2_transcript TEXT,
    part2_audio_url VARCHAR(500),
    part1_audio_url VARCHAR(500),
    failure_reason VARCHAR(255),
    retry_count SMALLINT DEFAULT 0,
    cost NUMERIC(10, 6),
    -- 大 JSON 字段（从 test_raw_data 复制）
    part1_raw_result JSONB,
    part2_raw_result JSONB,
    tokens_used JSONB,
    summary_highlights TEXT,
    summary_weaknesses TEXT,
    summary_weekly_plan TEXT,
    summary_dimension_feedback JSONB,
    summary_generated_at TIMESTAMP WITH TIME ZONE,
    interpretation_pages JSONB,
    interpretation_parent_script TEXT,
    interpretation_generated_at TIMESTAMP WITH TIME ZONE,
    report_override JSONB,
    -- 原始时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    -- 归档时间
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tests_archive_student ON tests_archive (student_id);
CREATE INDEX IF NOT EXISTS idx_tests_archive_original ON tests_archive (original_id);
CREATE INDEX IF NOT EXISTS idx_tests_archive_created ON tests_archive (created_at);
CREATE INDEX IF NOT EXISTS idx_tests_archive_archived ON tests_archive (archived_at);

-- ============================================
-- 2. 创建 test_items_archive 表
-- ============================================
CREATE TABLE IF NOT EXISTS test_items_archive (
    id BIGSERIAL PRIMARY KEY,
    original_id BIGINT NOT NULL,              -- 原始 test_items.id
    test_archive_id BIGINT NOT NULL REFERENCES tests_archive(id) ON DELETE CASCADE,
    original_test_id BIGINT NOT NULL,         -- 原始 tests.id
    question_no INTEGER NOT NULL,
    score SMALLINT NOT NULL,
    feedback TEXT,
    evidence TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_test_items_archive_test ON test_items_archive (test_archive_id);
CREATE INDEX IF NOT EXISTS idx_test_items_archive_original_test ON test_items_archive (original_test_id);

-- ============================================
-- 3. 创建归档函数
-- ============================================
CREATE OR REPLACE FUNCTION archive_old_tests(retention_days INTEGER DEFAULT 90)
RETURNS TABLE (
    archived_tests INTEGER,
    archived_items INTEGER
) AS $$
DECLARE
    cutoff_date TIMESTAMP WITH TIME ZONE;
    tests_count INTEGER := 0;
    items_count INTEGER := 0;
BEGIN
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;
    
    -- 1. 归档 tests 表的数据
    WITH archived AS (
        INSERT INTO tests_archive (
            original_id, student_id, level, unit, status,
            total_score, part1_score, part2_score, star_level,
            part2_transcript, part2_audio_url, part1_audio_url,
            failure_reason, retry_count, cost,
            part1_raw_result, part2_raw_result, tokens_used,
            summary_highlights, summary_weaknesses, summary_weekly_plan,
            summary_dimension_feedback, summary_generated_at,
            interpretation_pages, interpretation_parent_script,
            interpretation_generated_at, report_override,
            created_at, updated_at, completed_at
        )
        SELECT 
            t.id, t.student_id, t.level, t.unit, t.status,
            t.total_score, t.part1_score, t.part2_score, t.star_level,
            t.part2_transcript, t.part2_audio_url, t.part1_audio_url,
            t.failure_reason, t.retry_count, t.cost,
            COALESCE(rd.part1_raw_result, t.part1_raw_result),
            COALESCE(rd.part2_raw_result, t.part2_raw_result),
            COALESCE(rd.tokens_used, t.tokens_used),
            COALESCE(rd.summary_highlights, t.summary_highlights),
            COALESCE(rd.summary_weaknesses, t.summary_weaknesses),
            COALESCE(rd.summary_weekly_plan, t.summary_weekly_plan),
            COALESCE(rd.summary_dimension_feedback, t.summary_dimension_feedback),
            t.summary_generated_at,
            COALESCE(rd.interpretation_pages, t.interpretation_pages),
            COALESCE(rd.interpretation_parent_script, t.interpretation_parent_script),
            t.interpretation_generated_at,
            COALESCE(rd.report_override, t.report_override),
            t.created_at, t.updated_at, t.completed_at
        FROM tests t
        LEFT JOIN test_raw_data rd ON rd.test_id = t.id
        WHERE t.status = 'completed'
          AND t.completed_at < cutoff_date
        RETURNING original_id, id AS archive_id
    )
    SELECT COUNT(*) INTO tests_count FROM archived;
    
    -- 2. 归档 test_items 表的数据
    WITH items_archived AS (
        INSERT INTO test_items_archive (
            original_id, test_archive_id, original_test_id,
            question_no, score, feedback, evidence, created_at
        )
        SELECT 
            ti.id, ta.id, ti.test_id,
            ti.question_no, ti.score, ti.feedback, ti.evidence, ti.created_at
        FROM test_items ti
        INNER JOIN tests_archive ta ON ta.original_id = ti.test_id
        WHERE ta.archived_at > NOW() - INTERVAL '1 minute'  -- 只处理刚归档的
        RETURNING id
    )
    SELECT COUNT(*) INTO items_count FROM items_archived;
    
    -- 3. 删除已归档的 test_raw_data
    DELETE FROM test_raw_data
    WHERE test_id IN (
        SELECT original_id FROM tests_archive 
        WHERE archived_at > NOW() - INTERVAL '1 minute'
    );
    
    -- 4. 删除已归档的 test_items
    DELETE FROM test_items
    WHERE test_id IN (
        SELECT original_id FROM tests_archive 
        WHERE archived_at > NOW() - INTERVAL '1 minute'
    );
    
    -- 5. 删除已归档的 tests
    DELETE FROM tests
    WHERE id IN (
        SELECT original_id FROM tests_archive 
        WHERE archived_at > NOW() - INTERVAL '1 minute'
    );
    
    RETURN QUERY SELECT tests_count, items_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 完成说明
-- ============================================
-- 
-- 使用方法：
--   SELECT * FROM archive_old_tests(90);  -- 归档 90 天前的测评
--
-- 注意事项：
-- 1. 只归档 status='completed' 的测评
-- 2. 归档包含 test_raw_data 的大 JSON 字段
-- 3. 归档后自动删除原表数据
-- 4. 建议通过 Python 脚本调用，便于日志记录
--
