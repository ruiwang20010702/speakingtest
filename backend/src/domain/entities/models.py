"""
Domain Entities - Core Business Objects
Pure Python objects with no external dependencies.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    TEACHER = "teacher"
    STUDENT = "student"
    ADMIN = "admin"


class TestStatus(str, Enum):
    """Test status enumeration."""
    PENDING = "pending"
    PART1_DONE = "part1_done"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class User:
    """User entity."""
    id: int
    role: UserRole
    email: Optional[str] = None
    status: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == 1

    def is_teacher(self) -> bool:
        """Check if user is a teacher."""
        return self.role == UserRole.TEACHER


@dataclass
class StudentProfile:
    """Student profile entity."""
    user_id: int
    student_name: str
    teacher_id: int
    external_user_id: Optional[str] = None
    cur_grade: Optional[str] = None
    cur_level_desc: Optional[str] = None


@dataclass
class Test:
    """Test (assessment) entity."""
    id: int
    student_id: int
    level: str
    unit: str
    status: TestStatus = TestStatus.PENDING
    total_score: Optional[float] = None
    part1_score: Optional[float] = None
    part2_score: Optional[float] = None
    star_level: Optional[int] = None
    part2_transcript: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def is_completed(self) -> bool:
        """Check if test is completed."""
        return self.status == TestStatus.COMPLETED

    def calculate_star_level(self) -> int:
        """Calculate star level based on total score (0-44)."""
        if self.total_score is None:
            return 0
        score = self.total_score
        if score >= 40:
            return 5
        elif score >= 32:
            return 4
        elif score >= 24:
            return 3
        elif score >= 16:
            return 2
        else:
            return 1


@dataclass
class TestItem:
    """Test item (single question result) entity."""
    id: int
    test_id: int
    question_no: int
    score: int  # 0, 1, or 2
    feedback: Optional[str] = None
    evidence: Optional[str] = None
