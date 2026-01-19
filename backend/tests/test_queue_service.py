"""
Tests for Queue Service
Covers: Task dataclasses, serialization/deserialization
"""
import pytest

from src.infrastructure.queue_service import (
    Part1Task,
    Part2Task,
    InterpretationTask
)


class TestPart2Task:
    """Tests for Part2Task dataclass."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        task = Part2Task(
            task_id="abc123",
            test_id=42,
            audio_url="https://oss.example.com/audio.mp3",
            questions=[{"no": 1, "question": "What?"}]
        )
        result = task.to_dict()

        assert result["task_id"] == "abc123"
        assert result["test_id"] == 42
        assert result["audio_url"] == "https://oss.example.com/audio.mp3"
        assert len(result["questions"]) == 1

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "task_id": "xyz789",
            "test_id": 100,
            "audio_url": "https://oss.example.com/test.wav",
            "questions": [{"no": 1}, {"no": 2}]
        }
        task = Part2Task.from_dict(data)

        assert task.task_id == "xyz789"
        assert task.test_id == 100
        assert task.audio_url == "https://oss.example.com/test.wav"
        assert len(task.questions) == 2

    def test_roundtrip(self):
        """Test serialization/deserialization roundtrip."""
        original = Part2Task(
            task_id="test",
            test_id=1,
            audio_url="url",
            questions=[{"no": 1}]
        )
        roundtrip = Part2Task.from_dict(original.to_dict())

        assert roundtrip.task_id == original.task_id
        assert roundtrip.test_id == original.test_id
        assert roundtrip.audio_url == original.audio_url
        assert roundtrip.questions == original.questions


class TestPart1Task:
    """Tests for Part1Task dataclass."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        task = Part1Task(
            task_id="task123",
            test_id=50,
            audio_url="https://oss.example.com/part1.mp3",
            reference_text="Hello, world!"
        )
        result = task.to_dict()

        assert result["task_id"] == "task123"
        assert result["test_id"] == 50
        assert result["audio_url"] == "https://oss.example.com/part1.mp3"
        assert result["reference_text"] == "Hello, world!"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "task_id": "part1task",
            "test_id": 25,
            "audio_url": "https://oss.example.com/reading.wav",
            "reference_text": "Test reference text"
        }
        task = Part1Task.from_dict(data)

        assert task.task_id == "part1task"
        assert task.test_id == 25
        assert task.reference_text == "Test reference text"

    def test_roundtrip(self):
        """Test serialization/deserialization roundtrip."""
        original = Part1Task(
            task_id="round",
            test_id=99,
            audio_url="url",
            reference_text="text"
        )
        roundtrip = Part1Task.from_dict(original.to_dict())

        assert roundtrip.task_id == original.task_id
        assert roundtrip.reference_text == original.reference_text


class TestInterpretationTask:
    """Tests for InterpretationTask dataclass."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        task = InterpretationTask(
            task_id="interp123",
            test_id=30,
            student_name="小明",
            level="L2",
            total_score=85.0,
            part1_score=80.0,
            part2_score=90.0,
            star_level=4,
            part1_details={"words": []},
            part2_items=[],
            radar_data=[]
        )
        result = task.to_dict()

        assert result["task_id"] == "interp123"
        assert result["student_name"] == "小明"
        assert result["total_score"] == 85.0
        assert result["star_level"] == 4

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "task_id": "interpret",
            "test_id": 10,
            "student_name": "小红",
            "level": "L1",
            "total_score": 70.0,
            "part1_score": 65.0,
            "part2_score": 75.0,
            "star_level": 3,
            "part1_details": {},
            "part2_items": [],
            "radar_data": []
        }
        task = InterpretationTask.from_dict(data)

        assert task.task_id == "interpret"
        assert task.student_name == "小红"
        assert task.level == "L1"

    def test_roundtrip(self):
        """Test serialization/deserialization roundtrip."""
        original = InterpretationTask(
            task_id="round",
            test_id=5,
            student_name="Test",
            level="L3",
            total_score=50.0,
            part1_score=45.0,
            part2_score=55.0,
            star_level=2,
            part1_details={"key": "value"},
            part2_items=[{"no": 1}],
            radar_data=[{"dim": "fluency", "score": 60}]
        )
        roundtrip = InterpretationTask.from_dict(original.to_dict())

        assert roundtrip.task_id == original.task_id
        assert roundtrip.student_name == original.student_name
        assert roundtrip.part1_details == original.part1_details
        assert roundtrip.radar_data == original.radar_data


class TestTaskValidation:
    """Tests for task data validation edge cases."""

    def test_part2_empty_questions(self):
        """Test Part2Task with empty questions list."""
        task = Part2Task(
            task_id="empty",
            test_id=1,
            audio_url="url",
            questions=[]
        )
        assert task.questions == []

    def test_interpretation_with_all_data(self):
        """Test InterpretationTask with complete data."""
        task = InterpretationTask(
            task_id="full",
            test_id=100,
            student_name="完整测试",
            level="L4",
            total_score=95.5,
            part1_score=93.0,
            part2_score=98.0,
            star_level=5,
            part1_details={
                "words": [
                    {"content": "Hello", "score": 95},
                    {"content": "World", "score": 90}
                ]
            },
            part2_items=[
                {"no": 1, "score": "S", "transcript": "Answer 1"},
                {"no": 2, "score": "A", "transcript": "Answer 2"}
            ],
            radar_data=[
                {"dimension": "fluency", "score": 92},
                {"dimension": "pronunciation", "score": 88}
            ]
        )
        data = task.to_dict()

        assert len(data["part1_details"]["words"]) == 2
        assert len(data["part2_items"]) == 2
        assert len(data["radar_data"]) == 2
