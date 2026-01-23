"""
SQLAlchemy ORM Models
Maps domain entities to database tables.

Index Strategy:
- Primary keys and unique constraints create implicit indexes
- Additional indexes are created for:
  1. Foreign keys used in JOINs
  2. Columns frequently used in WHERE clauses
  3. Composite indexes for common query patterns
  4. Columns used in ORDER BY with LIMIT

Performance Notes:
- Composite indexes should have most selective column first
- Use INCLUDE columns for covering indexes (PostgreSQL 11+)
- Monitor pg_stat_user_indexes for unused indexes
"""
from datetime import datetime
from typing import Optional

from src.infrastructure.timezone import now as china_now, CHINA_TZ

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Index,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

# Use JSONB for PostgreSQL, generic JSON for others (SQLite)
JSON_TYPE = JSON().with_variant(JSONB, "postgresql")

# Use Integer for SQLite (to support autoincrement), BigInteger for others
BigIntegerType = BigInteger().with_variant(Integer, "sqlite")


from src.infrastructure.database import Base


class UserModel(Base):
    """User table ORM model."""
    __tablename__ = "users"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    status = Column(SmallInteger, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())
    updated_at = Column(DateTime(timezone=True), default=lambda: china_now(), onupdate=lambda: china_now())
    is_deleted = Column(Boolean, default=False)
    
    # CRM 相关字段
    ss_crm_name = Column(String(100), nullable=True)     # CRM 显示名
    ss_name = Column(String(100), nullable=True)         # 员工姓名
    ss_sm_name = Column(String(100), nullable=True)      # SM 姓名
    ss_dept4_name = Column(String(100), nullable=True)   # 部门名称
    ss_group = Column(String(100), nullable=True)        # 组别
    crm_synced_at = Column(DateTime(timezone=True), nullable=True)  # CRM 信息最后同步时间

    # Relationships
    student_profile = relationship(
        "StudentProfileModel",
        back_populates="user",
        uselist=False,
        foreign_keys="[StudentProfileModel.user_id]"
    )
    tests = relationship("TestModel", back_populates="student")
    
    __table_args__ = (
        # 后台教师/学生列表筛选优化
        Index("idx_users_role_status", "role", "status"),
    )


class StudentProfileModel(Base):
    """Student profile table ORM model."""
    __tablename__ = "student_profiles"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    student_name = Column(String(100), nullable=False)
    external_source = Column(String(20), default="crm_domestic_ss")
    external_user_id = Column(String(50), nullable=True)
    teacher_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    
    # SS Info
    ss_email_addr = Column(String(100), nullable=True)
    ss_crm_name = Column(String(100), nullable=True)
    ss_name = Column(String(100), nullable=True)      # New
    ss_sm_name = Column(String(100), nullable=True)   # New
    ss_dept4_name = Column(String(100), nullable=True)# New
    ss_group = Column(String(100), nullable=True)     # New
    
    # Student Info
    cur_age = Column(Integer, nullable=True)
    cur_grade = Column(String(20), nullable=True)
    cur_level_desc = Column(String(50), nullable=True)
    main_last_buy_unit_name = Column(String(100), nullable=True)
    is_upgrade = Column(Integer, default=0)           # New
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())
    updated_at = Column(DateTime(timezone=True), default=lambda: china_now(), onupdate=lambda: china_now())

    # Relationships
    user = relationship("UserModel", back_populates="student_profile", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_student_profiles_teacher_id", "teacher_id"),
        Index("idx_student_profiles_external_user_id", "external_user_id"),
    )


class TestModel(Base):
    """Test (assessment) table ORM model."""
    __tablename__ = "tests"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    student_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    level = Column(String(20), nullable=False)
    unit = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    total_score = Column(Numeric(5, 2), nullable=True)
    part1_score = Column(Numeric(5, 2), nullable=True)
    part2_score = Column(Numeric(5, 2), nullable=True)
    star_level = Column(SmallInteger, nullable=True)
    part2_transcript = Column(Text, nullable=True)
    part2_audio_url = Column(String(500), nullable=True)
    part2_raw_result = Column(JSON_TYPE, nullable=True)
    part1_audio_url = Column(String(500), nullable=True)
    part1_raw_result = Column(JSON_TYPE, nullable=True)
    failure_reason = Column(String(255), nullable=True)
    retry_count = Column(SmallInteger, default=0)
    cost = Column(Numeric(10, 6), nullable=True)
    tokens_used = Column(JSON_TYPE, nullable=True, default={})
    # Summary Analysis (测评汇总分析，给家长端 H5 用，学生完成测试后自动生成)
    summary_highlights = Column(Text, nullable=True)      # JSON array: 亮点
    summary_weaknesses = Column(Text, nullable=True)      # JSON array: 短板
    summary_weekly_plan = Column(Text, nullable=True)     # JSON array: 周计划
    summary_dimension_feedback = Column(JSON_TYPE, nullable=True)  # AI 生成的五维评语 {"fluency": {"comment": "...", "tags": [...]}, ...}
    summary_generated_at = Column(DateTime(timezone=True), nullable=True)
    # Interpretation (报告解读，按页面组织，给班主任用，手动触发生成)
    interpretation_pages = Column(JSON_TYPE, nullable=True)  # 按6页组织的解读内容
    interpretation_parent_script = Column(Text, nullable=True)  # 家长沟通话术
    interpretation_generated_at = Column(DateTime(timezone=True), nullable=True)  # 生成时间
    interpretation_status = Column(String(20), nullable=True, default=None)  # pending/generating/completed/failed
    interpretation_retry_count = Column(SmallInteger, default=0)  # 生成重试次数
    # Report Override (用户手动编辑的内容，优先于原始数据)
    report_override = Column(JSON_TYPE, nullable=True)
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())
    updated_at = Column(DateTime(timezone=True), default=lambda: china_now(), onupdate=lambda: china_now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    student = relationship("UserModel", back_populates="tests")
    items = relationship("TestItemModel", back_populates="test", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("student_id", "level", "unit", name="uk_student_level_unit"),
        # 基础索引
        Index("idx_tests_student_id", "student_id"),
        Index("idx_tests_status", "status"),
        Index("idx_tests_created_at", "created_at"),
        # 组合索引：列表/统计常用查询
        Index("idx_tests_student_status", "student_id", "status"),
        Index("idx_tests_student_status_created", "student_id", "status", "created_at"),
    )


class TestItemModel(Base):
    """Test item (Part 2 question) table ORM model."""
    __tablename__ = "test_items"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    test_id = Column(BigInteger, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    question_no = Column(Integer, nullable=False)
    score = Column(SmallInteger, nullable=False)
    feedback = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())

    # Relationships
    test = relationship("TestModel", back_populates="items")

    __table_args__ = (
        UniqueConstraint("test_id", "question_no", name="uk_test_question"),
        # 显式索引：虽然 unique 约束会创建索引，但显式声明更清晰
        Index("idx_test_items_test_id", "test_id"),
        Index("idx_test_items_test_question", "test_id", "question_no"),
    )


class TestArchiveModel(Base):
    """
    Archived tests table - stores historical test records.
    
    Records older than retention period (default 90 days) are moved here.
    Preserves all original data for compliance and historical queries.
    """
    __tablename__ = "tests_archive"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    original_id = Column(BigInteger, nullable=False)  # 原始 tests.id
    student_id = Column(BigInteger, nullable=False)  # 不设外键，允许学生删除后归档仍存在
    level = Column(String(20), nullable=False)
    unit = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    total_score = Column(Numeric(5, 2), nullable=True)
    part1_score = Column(Numeric(5, 2), nullable=True)
    part2_score = Column(Numeric(5, 2), nullable=True)
    star_level = Column(SmallInteger, nullable=True)
    part2_transcript = Column(Text, nullable=True)
    part2_audio_url = Column(String(500), nullable=True)
    part1_audio_url = Column(String(500), nullable=True)
    failure_reason = Column(String(255), nullable=True)
    retry_count = Column(SmallInteger, default=0)
    cost = Column(Numeric(10, 6), nullable=True)
    # 大 JSON 字段也归档（从 test_raw_data 复制）
    part1_raw_result = Column(JSON_TYPE, nullable=True)
    part2_raw_result = Column(JSON_TYPE, nullable=True)
    tokens_used = Column(JSON_TYPE, nullable=True)
    summary_highlights = Column(Text, nullable=True)
    summary_weaknesses = Column(Text, nullable=True)
    summary_weekly_plan = Column(Text, nullable=True)
    summary_dimension_feedback = Column(JSON_TYPE, nullable=True)
    summary_generated_at = Column(DateTime(timezone=True), nullable=True)
    interpretation_pages = Column(JSON_TYPE, nullable=True)
    interpretation_parent_script = Column(Text, nullable=True)
    interpretation_generated_at = Column(DateTime(timezone=True), nullable=True)
    report_override = Column(JSON_TYPE, nullable=True)
    # 原始时间戳
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # 归档时间
    archived_at = Column(DateTime(timezone=True), default=lambda: china_now())

    # Relationships
    items = relationship("TestItemArchiveModel", back_populates="test", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tests_archive_student", "student_id"),
        Index("idx_tests_archive_original", "original_id"),
        Index("idx_tests_archive_created", "created_at"),
        Index("idx_tests_archive_archived", "archived_at"),
    )


class TestItemArchiveModel(Base):
    """Archived test items - stores historical Part 2 question scores."""
    __tablename__ = "test_items_archive"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    original_id = Column(BigInteger, nullable=False)  # 原始 test_items.id
    test_archive_id = Column(BigInteger, ForeignKey("tests_archive.id", ondelete="CASCADE"), nullable=False)
    original_test_id = Column(BigInteger, nullable=False)  # 原始 tests.id
    question_no = Column(Integer, nullable=False)
    score = Column(SmallInteger, nullable=False)
    feedback = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    archived_at = Column(DateTime(timezone=True), default=lambda: china_now())

    # Relationships
    test = relationship("TestArchiveModel", back_populates="items")

    __table_args__ = (
        Index("idx_test_items_archive_test", "test_archive_id"),
        Index("idx_test_items_archive_original_test", "original_test_id"),
    )


class StudentEntryTokenModel(Base):
    """Student entry token table ORM model."""
    __tablename__ = "student_entry_tokens"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    token = Column(String(64), unique=True, nullable=False)  # unique 约束已隐式创建索引
    student_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    level = Column(String(20), nullable=False)
    unit = Column(String(20), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())

    __table_args__ = (
        Index("idx_student_entry_tokens_student_id", "student_id"),
        # 组合索引：验证入口时用
        Index("idx_student_entry_tokens_student_used_expires", "student_id", "is_used", "expires_at"),
        # 过期清理用
        Index("idx_student_entry_tokens_expires", "expires_at"),
    )


class ReportShareTokenModel(Base):
    """Report share token table ORM model."""
    __tablename__ = "report_share_tokens"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    token = Column(String(64), unique=True, nullable=False)  # unique 约束已隐式创建索引
    test_id = Column(BigInteger, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, default=False)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())

    __table_args__ = (
        Index("idx_report_share_tokens_test_id", "test_id"),
        # 组合索引：查询有效分享
        Index("idx_report_share_tokens_test_revoked", "test_id", "is_revoked"),
        # 家长查看验证：token + is_revoked + expires_at
        Index("idx_report_share_tokens_token_valid", "token", "is_revoked", "expires_at"),
        # 过期清理用
        Index("idx_report_share_tokens_expires", "expires_at"),
    )


class AuditLogModel(Base):
    """
    Audit log table ORM model.
    
    Security:
    - Hash chain: Each record contains hash of previous record (prev_hash)
    - Record hash: SHA-256 hash of all record fields for integrity verification
    - Tamper detection: Any modification breaks the hash chain
    """
    __tablename__ = "audit_logs"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    operator_id = Column(BigInteger, nullable=False)
    action = Column(String(50), nullable=False)
    target_type = Column(String(30), nullable=True)
    target_id = Column(BigInteger, nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())
    
    # Hash chain fields for tamper detection
    prev_hash = Column(String(64), nullable=True)   # SHA-256 hash of previous record (null for first record)
    record_hash = Column(String(64), nullable=True)  # SHA-256 hash of this record's content

    __table_args__ = (
        Index("idx_audit_logs_operator_id", "operator_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_created_at", "created_at"),
        # 组合索引：按目标追溯审计记录
        Index("idx_audit_logs_target", "target_type", "target_id", "created_at"),
        # IP 追溯
        Index("idx_audit_logs_ip", "client_ip"),
    )


class VerificationCodeModel(Base):
    """Verification code table for email login."""
    __tablename__ = "verification_codes"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    code = Column(String(6), nullable=False)
    purpose = Column(String(20), default="login")  # 'login', 'reset_password'
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())

    __table_args__ = (
        Index("idx_verification_codes_email", "email"),
        Index("idx_verification_codes_expires", "expires_at"),
        # 组合索引：登录验证查询
        Index("idx_verification_codes_verify", "email", "code", "is_used", "expires_at"),
        # IP 防刷/审计
        Index("idx_verification_codes_ip", "ip_address"),
        # 清理过期/已用验证码
        Index("idx_verification_codes_cleanup", "is_used", "expires_at"),
    )


class TestRawDataModel(Base):
    """
    Test raw data table - stores large JSON fields separated from tests table.
    
    Performance optimization:
    - Reduces I/O on tests table for list/stats queries
    - Keeps main table compact for better cache hit rate
    - Enables easier archiving of historical data
    
    Note: A trigger on tests table automatically syncs data to this table.
    For read operations, prefer querying this table directly for raw data.
    """
    __tablename__ = "test_raw_data"

    test_id = Column(BigInteger, ForeignKey("tests.id", ondelete="CASCADE"), primary_key=True)
    
    # Part1 原始评测数据
    part1_raw_result = Column(JSON_TYPE, nullable=True)
    
    # Part2 原始评测数据
    part2_raw_result = Column(JSON_TYPE, nullable=True)
    
    # Token 使用统计
    tokens_used = Column(JSON_TYPE, nullable=True, default={})
    
    # 报告解读内容
    interpretation_pages = Column(JSON_TYPE, nullable=True)
    interpretation_parent_script = Column(Text, nullable=True)
    
    # 用户编辑覆盖
    report_override = Column(JSON_TYPE, nullable=True)
    
    # Summary Analysis (测评汇总分析) - 从 tests 表分离
    summary_highlights = Column(Text, nullable=True)      # JSON array: 亮点
    summary_weaknesses = Column(Text, nullable=True)      # JSON array: 短板
    summary_weekly_plan = Column(Text, nullable=True)     # JSON array: 周计划
    summary_dimension_feedback = Column(JSON_TYPE, nullable=True)  # AI 生成的五维评语
    
    # 元数据
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())
    updated_at = Column(DateTime(timezone=True), default=lambda: china_now(), onupdate=lambda: china_now())

    # Relationship
    test = relationship("TestModel", backref="raw_data", uselist=False)


class AuditLogArchiveModel(Base):
    """
    Audit log archive table - stores historical audit records.
    
    Records older than retention period are moved here from audit_logs.
    Use archive_old_audit_logs() PostgreSQL function for archiving.
    """
    __tablename__ = "audit_logs_archive"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    original_id = Column(BigInteger, nullable=False)
    operator_id = Column(BigInteger, nullable=False)
    action = Column(String(50), nullable=False)
    target_type = Column(String(30), nullable=True)
    target_id = Column(BigInteger, nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON_TYPE, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    archived_at = Column(DateTime(timezone=True), default=lambda: china_now())

    __table_args__ = (
        Index("idx_audit_logs_archive_created", "created_at"),
        Index("idx_audit_logs_archive_target", "target_type", "target_id"),
        Index("idx_audit_logs_archive_operator", "operator_id"),
    )


class QuestionModel(Base):
    """Question bank for Part 1 (words) and Part 2 (Q&A) evaluation."""
    __tablename__ = "questions"

    id = Column(BigIntegerType, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)  # e.g., "L0", "L1", "L2"
    unit = Column(String(50), nullable=False)   # e.g., "Unit 1-4", "Unit 5-8"
    part = Column(Integer, nullable=False, default=2)  # 1=Word Reading, 2=Q&A
    type = Column(String(20), nullable=False, default="question_answer")  # word_reading, question_answer
    question_no = Column(Integer, nullable=False)  # 题目序号，从 1 开始
    question = Column(Text, nullable=False)  # The word/question text
    translation = Column(String(100), nullable=True)  # Chinese translation (for Part 1 words)
    image_url = Column(String(500), nullable=True)  # Image URL (OSS or CDN)
    reference_answer = Column(Text, nullable=True)  # Expected answer pattern (for Part 2)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: china_now())
    updated_at = Column(DateTime(timezone=True), default=lambda: china_now(), onupdate=lambda: china_now())

    __table_args__ = (
        UniqueConstraint("level", "unit", "part", "question_no", name="uk_level_unit_part_question"),
        Index("idx_questions_level_unit", "level", "unit"),
    )
