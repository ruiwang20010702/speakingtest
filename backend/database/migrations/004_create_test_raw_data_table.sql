-- Migration: 004_create_test_raw_data_table.sql
-- Description: 将大 JSON/Text 字段从 tests 表分离到独立表
-- Author: Performance Review
-- Date: 2026-01-23
--
-- 目的：
-- 1. 减少 tests 表 IO 压力（列表/统计查询不再读取大字段）
-- 2. 提高查询性能（主表更紧凑，缓存命中率更高）
-- 3. 便于归档和清理历史数据
--
-- 策略：
-- - test_raw_data: 存储 part1_raw_result, part2_raw_result, tokens_used 等原始数据
-- - tests 表保留精简字段用于列表/统计
-- - 通过 test_id 关联，按需查询详情

-- ============================================
-- 1. 创建 test_raw_data 表（大 JSON 存储）
-- ============================================

CREATE TABLE IF NOT EXISTS test_raw_data (
    test_id BIGINT PRIMARY KEY REFERENCES tests(id) ON DELETE CASCADE,
    
    -- Part1 原始评测数据
    part1_raw_result JSONB,
    
    -- Part2 原始评测数据  
    part2_raw_result JSONB,
    
    -- Token 使用统计
    tokens_used JSONB DEFAULT '{}',
    
    -- 报告解读内容（按页面组织）
    interpretation_pages JSONB,
    interpretation_parent_script TEXT,
    
    -- 用户编辑覆盖
    report_override JSONB,
    
    -- 元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 添加注释
COMMENT ON TABLE test_raw_data IS '测评原始数据表 - 存储大 JSON 字段，与 tests 表分离以提升性能';
COMMENT ON COLUMN test_raw_data.part1_raw_result IS 'Part1 单词朗读的 AI 评测原始结果';
COMMENT ON COLUMN test_raw_data.part2_raw_result IS 'Part2 问答的 AI 评测原始结果';
COMMENT ON COLUMN test_raw_data.tokens_used IS 'AI API 调用的 token 消耗统计';
COMMENT ON COLUMN test_raw_data.interpretation_pages IS '报告解读内容（6页结构化数据）';
COMMENT ON COLUMN test_raw_data.interpretation_parent_script IS '家长沟通话术';
COMMENT ON COLUMN test_raw_data.report_override IS '用户手动编辑的内容覆盖';


-- ============================================
-- 2. 创建 audit_logs_archive 表（审计日志归档）
-- ============================================

CREATE TABLE IF NOT EXISTS audit_logs_archive (
    id BIGSERIAL PRIMARY KEY,
    original_id BIGINT NOT NULL,
    operator_id BIGINT NOT NULL,
    action VARCHAR(50) NOT NULL,
    target_type VARCHAR(30),
    target_id BIGINT,
    client_ip VARCHAR(45),
    user_agent VARCHAR(500),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 归档表索引（用于审计查询）
CREATE INDEX IF NOT EXISTS idx_audit_logs_archive_created 
    ON audit_logs_archive (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_archive_target 
    ON audit_logs_archive (target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_archive_operator 
    ON audit_logs_archive (operator_id);

COMMENT ON TABLE audit_logs_archive IS '审计日志归档表 - 存储超过保留期的历史记录';


-- ============================================
-- 3. 数据迁移（将现有数据复制到新表）
-- ============================================

-- 迁移 tests 表的大 JSON 字段到 test_raw_data
INSERT INTO test_raw_data (
    test_id,
    part1_raw_result,
    part2_raw_result,
    tokens_used,
    interpretation_pages,
    interpretation_parent_script,
    report_override,
    created_at,
    updated_at
)
SELECT 
    id,
    part1_raw_result,
    part2_raw_result,
    tokens_used,
    interpretation_pages,
    interpretation_parent_script,
    report_override,
    created_at,
    updated_at
FROM tests
WHERE part1_raw_result IS NOT NULL 
   OR part2_raw_result IS NOT NULL 
   OR tokens_used IS NOT NULL
   OR interpretation_pages IS NOT NULL
   OR report_override IS NOT NULL
ON CONFLICT (test_id) DO UPDATE SET
    part1_raw_result = EXCLUDED.part1_raw_result,
    part2_raw_result = EXCLUDED.part2_raw_result,
    tokens_used = EXCLUDED.tokens_used,
    interpretation_pages = EXCLUDED.interpretation_pages,
    interpretation_parent_script = EXCLUDED.interpretation_parent_script,
    report_override = EXCLUDED.report_override,
    updated_at = NOW();


-- ============================================
-- 4. 创建触发器（自动同步新数据）
-- ============================================

-- 创建触发器函数：当 tests 表插入/更新时，自动同步到 test_raw_data
CREATE OR REPLACE FUNCTION sync_test_raw_data()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO test_raw_data (
        test_id,
        part1_raw_result,
        part2_raw_result,
        tokens_used,
        interpretation_pages,
        interpretation_parent_script,
        report_override,
        created_at,
        updated_at
    ) VALUES (
        NEW.id,
        NEW.part1_raw_result,
        NEW.part2_raw_result,
        NEW.tokens_used,
        NEW.interpretation_pages,
        NEW.interpretation_parent_script,
        NEW.report_override,
        NEW.created_at,
        NEW.updated_at
    )
    ON CONFLICT (test_id) DO UPDATE SET
        part1_raw_result = EXCLUDED.part1_raw_result,
        part2_raw_result = EXCLUDED.part2_raw_result,
        tokens_used = EXCLUDED.tokens_used,
        interpretation_pages = EXCLUDED.interpretation_pages,
        interpretation_parent_script = EXCLUDED.interpretation_parent_script,
        report_override = EXCLUDED.report_override,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
DROP TRIGGER IF EXISTS trg_sync_test_raw_data ON tests;
CREATE TRIGGER trg_sync_test_raw_data
    AFTER INSERT OR UPDATE OF 
        part1_raw_result, part2_raw_result, tokens_used,
        interpretation_pages, interpretation_parent_script, report_override
    ON tests
    FOR EACH ROW
    EXECUTE FUNCTION sync_test_raw_data();

COMMENT ON FUNCTION sync_test_raw_data IS '自动同步 tests 表的大 JSON 字段到 test_raw_data 表';


-- ============================================
-- 5. 创建归档函数（定期归档审计日志）
-- ============================================

CREATE OR REPLACE FUNCTION archive_old_audit_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- 将超过保留期的记录移动到归档表
    WITH moved AS (
        DELETE FROM audit_logs
        WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL
        RETURNING *
    )
    INSERT INTO audit_logs_archive (
        original_id, operator_id, action, target_type, target_id,
        client_ip, user_agent, details, created_at
    )
    SELECT 
        id, operator_id, action, target_type, target_id,
        client_ip, user_agent, details, created_at
    FROM moved;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION archive_old_audit_logs IS '归档超过指定天数的审计日志到 audit_logs_archive 表';


-- ============================================
-- 6. 创建视图（统一查询接口）
-- ============================================

-- 创建包含原始数据的完整测试视图
CREATE OR REPLACE VIEW v_tests_full AS
SELECT 
    t.*,
    rd.part1_raw_result AS raw_part1_raw_result,
    rd.part2_raw_result AS raw_part2_raw_result,
    rd.tokens_used AS raw_tokens_used,
    rd.interpretation_pages AS raw_interpretation_pages,
    rd.interpretation_parent_script AS raw_interpretation_parent_script,
    rd.report_override AS raw_report_override
FROM tests t
LEFT JOIN test_raw_data rd ON t.id = rd.test_id;

COMMENT ON VIEW v_tests_full IS '测试完整视图 - 包含主表和原始数据表的所有字段';


-- ============================================
-- 验证
-- ============================================

-- 检查表创建
SELECT 'test_raw_data' AS table_name, COUNT(*) AS row_count FROM test_raw_data
UNION ALL
SELECT 'audit_logs_archive', COUNT(*) FROM audit_logs_archive;
