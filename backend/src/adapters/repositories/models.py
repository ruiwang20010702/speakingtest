"""
SQLAlchemy ORM Models
Maps domain entities to database tables.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, Index,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from src.infrastructure.database import Base


class UserModel(Base):
    """User table ORM model."""
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    status = Column(SmallInteger, default=1)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    student_profile = relationship(
        "StudentProfileModel",
        back_populates="user",
        uselist=False,
        foreign_keys="[StudentProfileModel.user_id]"
    )
    tests = relationship("TestModel", back_populates="student")


class StudentProfileModel(Base):
    """Student profile table ORM model."""
    __tablename__ = "student_profiles"

    user_id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    student_name = Column(String(100), nullable=False)
    external_source = Column(String(20), default="crm_domestic_ss")
    external_user_id = Column(String(50), nullable=True)
    teacher_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    ss_email_addr = Column(String(100), nullable=True)
    ss_crm_name = Column(String(100), nullable=True)
    cur_age = Column(Integer, nullable=True)
    cur_grade = Column(String(20), nullable=True)
    cur_level_desc = Column(String(50), nullable=True)
    main_last_buy_unit_name = Column(String(100), nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("UserModel", back_populates="student_profile", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_student_profiles_teacher_id", "teacher_id"),
        Index("idx_student_profiles_external_user_id", "external_user_id"),
    )


class TestModel(Base):
    """Test (assessment) table ORM model."""
    __tablename__ = "tests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
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
    part1_audio_url = Column(String(500), nullable=True)
    part1_raw_result = Column(JSONB, nullable=True)
    failure_reason = Column(String(255), nullable=True)
    retry_count = Column(SmallInteger, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    student = relationship("UserModel", back_populates="tests")
    items = relationship("TestItemModel", back_populates="test", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("student_id", "level", "unit", name="uk_student_level_unit"),
        Index("idx_tests_student_id", "student_id"),
        Index("idx_tests_status", "status"),
        Index("idx_tests_created_at", "created_at"),
    )


class TestItemModel(Base):
    """Test item (Part 2 question) table ORM model."""
    __tablename__ = "test_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    test_id = Column(BigInteger, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    question_no = Column(Integer, nullable=False)
    score = Column(SmallInteger, nullable=False)
    feedback = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    test = relationship("TestModel", back_populates="items")

    __table_args__ = (
        UniqueConstraint("test_id", "question_no", name="uk_test_question"),
    )


class StudentEntryTokenModel(Base):
    """Student entry token table ORM model."""
    __tablename__ = "student_entry_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token = Column(String(64), unique=True, nullable=False)
    student_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    level = Column(String(20), nullable=False)
    unit = Column(String(20), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_student_entry_tokens_student_id", "student_id"),
    )


class ReportShareTokenModel(Base):
    """Report share token table ORM model."""
    __tablename__ = "report_share_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token = Column(String(64), unique=True, nullable=False)
    test_id = Column(BigInteger, ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_revoked = Column(Boolean, default=False)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_report_share_tokens_test_id", "test_id"),
    )


class AuditLogModel(Base):
    """Audit log table ORM model."""
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    operator_id = Column(BigInteger, nullable=False)
    action = Column(String(50), nullable=False)
    target_type = Column(String(30), nullable=True)
    target_id = Column(BigInteger, nullable=True)
    client_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_audit_logs_operator_id", "operator_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_created_at", "created_at"),
    )


class VerificationCodeModel(Base):
    """Verification code table for email login."""
    __tablename__ = "verification_codes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False)
    code = Column(String(6), nullable=False)
    purpose = Column(String(20), default="login")  # 'login', 'reset_password'
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_verification_codes_email", "email"),
        Index("idx_verification_codes_expires", "expires_at"),
    )


class QuestionModel(Base):
    """Question bank for Part 2 evaluation."""
    __tablename__ = "questions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)  # e.g., "L1", "L2"
    unit = Column(String(50), nullable=False)   # e.g., "Unit 1", "Food"
    part = Column(Integer, nullable=False, default=2) # 1=Read, 2=Q&A
    type = Column(String(20), nullable=False, default="question_answer") # word_reading, question_answer
    question_no = Column(Integer, nullable=False)  # 1-12
    question = Column(Text, nullable=False)  # The question text
    reference_answer = Column(Text, nullable=True)  # Expected answer pattern
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("level", "unit", "part", "question_no", name="uk_level_unit_part_question"),
        Index("idx_questions_level_unit", "level", "unit"),
    )
