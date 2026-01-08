-- ============================================
-- Speaking Test System - Database Schema (PostgreSQL)
-- Version: 1.0.0
-- Created: 2026-01-05
-- Standard: /database-design-patterns (PostgreSQL)
-- ============================================

-- ============================================
-- Helper Function: Auto-Update updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';


-- ============================================
-- 1. Users (用户基础表)
-- ============================================
-- Roles: teacher, student, admin

CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    role            VARCHAR(20) NOT NULL, -- teacher, student, admin
    email           VARCHAR(255) UNIQUE,  -- 仅老师/管理员有
    password_hash   VARCHAR(255),         -- 仅老师/管理员有
    status          SMALLINT DEFAULT 1,   -- 1:active, 0:disabled
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    is_deleted      BOOLEAN DEFAULT FALSE
);

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE users IS '用户基础表 (Teacher/Student/Admin)';
COMMENT ON COLUMN users.role IS 'teacher, student, admin';


-- ============================================
-- 2. StudentProfiles (学生档案)
-- ============================================
-- 1:1 with users table

CREATE TABLE student_profiles (
    user_id             BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
    student_name        VARCHAR(100) NOT NULL,
    external_source     VARCHAR(20) DEFAULT 'crm_domestic_ss',
    external_user_id    VARCHAR(50),  -- CRM 中的学生 ID
    teacher_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    ss_email_addr       VARCHAR(100), -- 冗余字段，用于快速校验
    -- CRM 冗余字段
    cur_age             INT,
    cur_grade           VARCHAR(20),
    cur_level_desc      VARCHAR(50),
    last_synced_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_student_profiles_teacher_id ON student_profiles(teacher_id);
CREATE INDEX idx_student_profiles_external_user_id ON student_profiles(external_user_id);

CREATE TRIGGER update_student_profiles_updated_at
    BEFORE UPDATE ON student_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE student_profiles IS '学生详情 (1:1 关联 users)';


-- ============================================
-- 3. Tests (测评记录主表)
-- ============================================

CREATE TABLE tests (
    id                  BIGSERIAL PRIMARY KEY,
    student_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    level               VARCHAR(20) NOT NULL, -- 教材级别
    unit                VARCHAR(20) NOT NULL, -- 单元
    status              VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, part1_done, processing, completed, failed
    -- Scores
    total_score         NUMERIC(5,2),  -- Part1 + Part2 (0-44)
    part1_score         NUMERIC(5,2),  -- 0-20
    part2_score         NUMERIC(5,2),  -- 0-24 (12 questions * 2)
    star_level          SMALLINT,      -- 1-5 星
    -- Part 2 Details
    part2_transcript    TEXT,          -- Qwen 转写结果 (Full)
    part2_audio_url     VARCHAR(500),  -- OSS 存储路径
    part2_raw_result    JSONB,         -- Qwen 原始返回 (含建议)
    -- Part 1 Details
    part1_audio_url     VARCHAR(500),  -- OSS 存储路径
    part1_raw_result    JSONB,         -- 讯飞原始返回
    -- Failure Info
    failure_reason      VARCHAR(255),
    retry_count         SMALLINT DEFAULT 0,
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    UNIQUE (student_id, level, unit) -- 同一学生同一任务只能有一个有效测评
);

CREATE INDEX idx_tests_student_id ON tests(student_id);
CREATE INDEX idx_tests_status ON tests(status);
CREATE INDEX idx_tests_created_at ON tests(created_at);

CREATE TRIGGER update_tests_updated_at
    BEFORE UPDATE ON tests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE tests IS '测评主表 (Part1/Part2 成绩、状态、音频链接)';


-- ============================================
-- 4. TestItems (Part2 题目明细)
-- ============================================
-- 12 questions per test (question_no 1-12)

CREATE TABLE test_items (
    id                  BIGSERIAL PRIMARY KEY,
    test_id             BIGINT NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    question_no         INT NOT NULL,      -- 1-12
    score               SMALLINT NOT NULL, -- 0, 1, 2
    feedback            TEXT,              -- 单题评语
    evidence            TEXT,              -- 评分依据 (转写片段)
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (test_id, question_no)
);

COMMENT ON TABLE test_items IS 'Part2 逐题明细 (12 题 × 0/1/2 分)';


-- ============================================
-- 5. StudentEntryTokens (学生入口令牌)
-- ============================================

CREATE TABLE student_entry_tokens (
    id                  BIGSERIAL PRIMARY KEY,
    token               VARCHAR(64) UNIQUE NOT NULL, -- URL-safe random string
    student_id          BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    level               VARCHAR(20) NOT NULL, -- 绑定的任务级别
    unit                VARCHAR(20) NOT NULL, -- 绑定的任务单元
    expires_at          TIMESTAMPTZ NOT NULL,
    is_used             BOOLEAN DEFAULT FALSE,
    used_at             TIMESTAMPTZ,
    created_by          BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_student_entry_tokens_student_id ON student_entry_tokens(student_id);

COMMENT ON TABLE student_entry_tokens IS '学生入口令牌 (一次性，有有效期)';


-- ============================================
-- 6. ReportShareTokens (家长分享令牌)
-- ============================================

CREATE TABLE report_share_tokens (
    id                  BIGSERIAL PRIMARY KEY,
    token               VARCHAR(64) UNIQUE NOT NULL, -- URL-safe random string
    test_id             BIGINT NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    expires_at          TIMESTAMPTZ,       -- NULL = 永久有效
    is_revoked          BOOLEAN DEFAULT FALSE, -- 老师可手动撤回
    created_by          BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_report_share_tokens_test_id ON report_share_tokens(test_id);

COMMENT ON TABLE report_share_tokens IS '家长分享链接 (可撤回)';


-- ============================================
-- 7. AuditLogs (审计日志)
-- ============================================

CREATE TABLE audit_logs (
    id                  BIGSERIAL PRIMARY KEY,
    operator_id         BIGINT NOT NULL,   -- FK to users.id (not enforced for perf)
    action              VARCHAR(50) NOT NULL, -- e.g., GENERATE_TOKEN, VIEW_REPORT
    target_type         VARCHAR(30),       -- e.g., student, test, token
    target_id           BIGINT,            -- 被操作对象 ID
    client_ip           VARCHAR(45),       -- IPv4 or IPv6
    user_agent          VARCHAR(500),
    details             JSONB,             -- 变更详情
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_operator_id ON audit_logs(operator_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

COMMENT ON TABLE audit_logs IS '审计日志';


-- ============================================
-- END OF SCHEMA
-- ============================================
