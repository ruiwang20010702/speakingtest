"""
Domain Ports - Abstract Interfaces
Defines contracts for external dependencies (Repositories, Gateways).
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.models import User, StudentProfile, Test, TestItem


class IUserRepository(ABC):
    """User repository interface."""

    @abstractmethod
    async def find_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        pass


class IStudentProfileRepository(ABC):
    """Student profile repository interface."""

    @abstractmethod
    async def find_by_user_id(self, user_id: int) -> Optional[StudentProfile]:
        pass

    @abstractmethod
    async def find_by_teacher_id(self, teacher_id: int, limit: int = 100, offset: int = 0) -> List[StudentProfile]:
        pass

    @abstractmethod
    async def save(self, profile: StudentProfile) -> StudentProfile:
        pass


class ITestRepository(ABC):
    """Test repository interface."""

    @abstractmethod
    async def find_by_id(self, test_id: int) -> Optional[Test]:
        pass

    @abstractmethod
    async def find_by_student_id(self, student_id: int) -> List[Test]:
        pass

    @abstractmethod
    async def save(self, test: Test) -> Test:
        pass

    @abstractmethod
    async def update_status(self, test_id: int, status: str) -> bool:
        pass


class IXunfeiGateway(ABC):
    """Xunfei speech evaluation gateway interface."""

    @abstractmethod
    async def evaluate_reading(self, audio_data: bytes, text: str) -> dict:
        """
        Evaluate reading audio against reference text.
        Returns raw evaluation result from Xunfei API.
        """
        pass


class IQwenGateway(ABC):
    """Qwen-Omni gateway interface."""

    @abstractmethod
    async def evaluate_speech(self, audio_url: str, questions: List[dict]) -> dict:
        """
        Evaluate speech audio for Part 2 questions.
        Returns transcript and per-question scores.
        """
        pass
