-- Migration: 003_add_performance_indexes.sql
-- Description: 添加性能优化组合索引
-- Author: Performance Review
-- Date: 2026-01-23
--
-- 索引策略说明：
-- 1. 为热点查询添加组合索引
-- 2. 按查询模式设计索引顺序（最选择性列在前）
-- 3. 避免重复索引（检查已有索引）
--
-- 预计影响：
-- - 写入性能略微下降（需维护更多索引）
-- - 读取性能显著提升（特别是列表/统计查询）
-- - 磁盘空间增加约 5-10%

-- ============================================
-- 1. users 表索引
-- ============================================

-- 后台教师/学生列表筛选优化
CREATE INDEX IF NOT EXISTS idx_users_role_status ON users (role, status);


-- ============================================
-- 2. tests 表索引
-- ============================================

-- 组合索引：列表/统计常用查询
-- 场景：按学生查看测评列表、统计学生测评数量
CREATE INDEX IF NOT EXISTS idx_tests_student_status ON tests (student_id, status);

-- 组合索引：带时间排序的查询
-- 场景：按学生查看最近的测评
CREATE INDEX IF NOT EXISTS idx_tests_student_status_created ON tests (student_id, status, created_at);


-- ============================================
-- 3. test_items 表索引
-- ============================================

-- 显式索引：虽然 FK 可能创建索引，但显式声明更可靠
CREATE INDEX IF NOT EXISTS idx_test_items_test_id ON test_items (test_id);

-- 组合索引：按题目序号查询
CREATE INDEX IF NOT EXISTS idx_test_items_test_question ON test_items (test_id, question_no);


-- ============================================
-- 4. student_entry_tokens 表索引
-- ============================================

-- 组合索引：验证入口时用
-- 场景：验证 token 时查询学生未使用且未过期的 token
CREATE INDEX IF NOT EXISTS idx_student_entry_tokens_student_used_expires 
    ON student_entry_tokens (student_id, is_used, expires_at);

-- 过期清理用
CREATE INDEX IF NOT EXISTS idx_student_entry_tokens_expires 
    ON student_entry_tokens (expires_at);


-- ============================================
-- 5. report_share_tokens 表索引
-- ============================================

-- 组合索引：查询有效分享
-- 场景：查看某测评的未撤销分享
CREATE INDEX IF NOT EXISTS idx_report_share_tokens_test_revoked 
    ON report_share_tokens (test_id, is_revoked);

-- 家长查看验证：token + is_revoked + expires_at
-- 场景：家长访问分享链接时验证 token 有效性
CREATE INDEX IF NOT EXISTS idx_report_share_tokens_token_valid 
    ON report_share_tokens (token, is_revoked, expires_at);

-- 过期清理用
CREATE INDEX IF NOT EXISTS idx_report_share_tokens_expires 
    ON report_share_tokens (expires_at);


-- ============================================
-- 6. audit_logs 表索引
-- ============================================

-- 组合索引：按目标追溯审计记录
-- 场景：查看某个用户/测评的操作历史
CREATE INDEX IF NOT EXISTS idx_audit_logs_target 
    ON audit_logs (target_type, target_id, created_at);

-- IP 追溯
-- 场景：安全审计，追踪某 IP 的所有操作
CREATE INDEX IF NOT EXISTS idx_audit_logs_ip ON audit_logs (client_ip);


-- ============================================
-- 7. verification_codes 表索引
-- ============================================

-- 组合索引：登录验证查询
-- 场景：验证邮箱验证码是否正确且有效
CREATE INDEX IF NOT EXISTS idx_verification_codes_verify 
    ON verification_codes (email, code, is_used, expires_at);

-- IP 防刷/审计
-- 场景：限制同一 IP 的验证码请求频率
CREATE INDEX IF NOT EXISTS idx_verification_codes_ip 
    ON verification_codes (ip_address);

-- 清理过期/已用验证码
CREATE INDEX IF NOT EXISTS idx_verification_codes_cleanup 
    ON verification_codes (is_used, expires_at);


-- ============================================
-- 验证索引创建
-- ============================================

-- 查看所有索引（可选，用于验证）
-- SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename;

-- 统计索引大小（可选，用于监控）
-- SELECT 
--     relname AS table_name,
--     indexrelname AS index_name,
--     pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
-- FROM pg_stat_user_indexes
-- ORDER BY pg_relation_size(indexrelid) DESC;
