"""
测试评分 API
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import UploadFile
from sqlalchemy.orm import Session
from io import BytesIO
import json

from api.scoring import router, evaluate_test, get_all_history, get_history, get_result_by_id


@pytest.fixture
def mock_db():
    """Mock 数据库会话"""
    return Mock(spec=Session)


@pytest.fixture
def mock_part1_audio():
    """Mock Part 1 音频文件"""
    audio = Mock(spec=UploadFile)
    audio.filename = "part1.webm"
    audio.read = Mock(return_value=b"fake part1 audio data")
    return audio


@pytest.fixture
def mock_part2_audio():
    """Mock Part 2 音频文件"""
    audio = Mock(spec=UploadFile)
    audio.filename = "part2.webm"
    audio.read = Mock(return_value=b"fake part2 audio data")
    return audio


@pytest.fixture
def sample_questions_data():
    """示例题目数据"""
    return {
        "levels": [
            {
                "level_id": "level1",
                "sections": [
                    {
                        "section_id": "unit1-3",
                        "parts": [
                            {
                                "part_id": 1,
                                "items": [
                                    {"word": "hello"},
                                    {"word": "world"},
                                    {"word": "test"}
                                ]
                            },
                            {
                                "part_id": 2,
                                "dialogues": [
                                    {"question": "What's your name?"},
                                    {"question": "How are you?"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }


class TestEvaluateTestWithXfyun:
    """测试使用讯飞评测的评估功能"""

    @pytest.mark.asyncio
    @patch("api.scoring.is_xfyun_configured", return_value=True)
    @patch("api.scoring.evaluate_words_with_xfyun")
    @patch("api.scoring.evaluate_part2_all_with_xfyun")
    @patch("api.scoring.cleanup_service")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("api.scoring.QUESTIONS_FILE", "/fake/questions.json")
    async def test_evaluate_with_xfyun_success(
        self, mock_open, mock_cleanup, mock_part2, mock_part1, mock_xfyun,
        mock_db, mock_part1_audio, mock_part2_audio, sample_questions_data
    ):
        """测试使用讯飞成功评估"""
        # Mock 文件读取
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(sample_questions_data).encode()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock 讯飞结果
        mock_part1.return_value = {
            "score": 3,
            "total": 3,
            "correct_words": ["hello", "world", "test"],
            "incorrect_words": [],
            "accuracy_score": 95.0,
            "fluency_score": 90.0,
            "feedback": "优秀"
        }

        mock_part2.return_value = {
            "total_score": 20,
            "question_scores": [
                {"question_index": 0, "score": 2.0},
                {"question_index": 1, "score": 2.0}
            ],
            "summary": {
                "fluency_score": 8.0,
                "pronunciation_score": 7.5,
                "confidence_score": 8.0
            },
            "feedback": "良好"
        }

        # Mock 数据库
        mock_test_record = Mock()
        mock_test_record.id = 1
        mock_test_record.part_scores = []
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # 执行测试
        result = await evaluate_test(
            student_name="TestStudent",
            level="level1",
            unit="unit1-3",
            part1_audio=mock_part1_audio,
            part2_audio=mock_part2_audio,
            db=mock_db
        )

        # 验证结果
        assert mock_db.add.called
        assert mock_db.commit.called


class TestEvaluateTestWithGemini:
    """测试使用 Gemini AI 评测的评估功能"""

    @pytest.mark.asyncio
    @patch("api.scoring.is_xfyun_configured", return_value=False)
    @patch("api.scoring.evaluate_part1")
    @patch("api.scoring.evaluate_part2_all")
    @patch("api.scoring.cleanup_service")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("api.scoring.QUESTIONS_FILE", "/fake/questions.json")
    async def test_evaluate_with_gemini_success(
        self, mock_open, mock_cleanup, mock_part2, mock_part1, mock_xfyun,
        mock_db, mock_part1_audio, mock_part2_audio, sample_questions_data
    ):
        """测试使用 Gemini 成功评估"""
        # Mock 文件读取
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(sample_questions_data).encode()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock Gemini 结果
        mock_part1.return_value = (18, {
            "feedback": "良好",
            "correct_words": ["hello", "world", "test"],
            "incorrect_words": []
        })

        mock_part2.return_value = (20, [
            {"question_num": 1, "score": 2, "feedback": "好"},
            {"question_num": 2, "score": 2, "feedback": "好"}
        ], {
            "fluency_score": 8.0,
            "pronunciation_score": 7.5,
            "confidence_score": 8.0
        })

        # Mock 数据库
        mock_test_record = Mock()
        mock_test_record.id = 1
        mock_test_record.part_scores = []
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # 执行测试
        result = await evaluate_test(
            student_name="TestStudent",
            level="level1",
            unit="unit1-3",
            part1_audio=mock_part1_audio,
            part2_audio=mock_part2_audio,
            db=mock_db
        )

        # 验证数据库操作
        assert mock_db.add.called
        assert mock_db.commit.called


class TestEvaluateTestErrors:
    """测试错误处理"""

    @pytest.mark.asyncio
    @patch("builtins.open", new_callable=MagicMock)
    @patch("api.scoring.QUESTIONS_FILE", "/fake/questions.json")
    async def test_level_not_found(self, mock_open, mock_db, mock_part1_audio, mock_part2_audio):
        """测试级别不存在"""
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps({"levels": []}).encode()
        mock_open.return_value.__enter__.return_value = mock_file

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await evaluate_test(
                student_name="TestStudent",
                level="level1",
                unit="unit1-3",
                part1_audio=mock_part1_audio,
                part2_audio=mock_part2_audio,
                db=mock_db
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("builtins.open", new_callable=MagicMock)
    @patch("api.scoring.QUESTIONS_FILE", "/fake/questions.json")
    async def test_unit_not_found(self, mock_open, mock_db, mock_part1_audio, mock_part2_audio, sample_questions_data):
        """测试单元不存在"""
        # 移除 unit1-3
        sample_questions_data["levels"][0]["sections"] = []

        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(sample_questions_data).encode()
        mock_open.return_value.__enter__.return_value = mock_file

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await evaluate_test(
                student_name="TestStudent",
                level="level1",
                unit="unit1-3",
                part1_audio=mock_part1_audio,
                part2_audio=mock_part2_audio,
                db=mock_db
            )

        assert exc_info.value.status_code == 404


class TestGetAllHistory:
    """测试获取所有历史记录"""

    @pytest.mark.asyncio
    async def test_get_all_history_success(self, mock_db):
        """测试成功获取所有历史"""
        # Mock 数据库查询结果
        mock_record = Mock()
        mock_record.id = 1
        mock_record.student_name = "Student1"
        mock_record.level = "level1"
        mock_record.unit = "unit1-3"
        mock_record.total_score = 35
        mock_record.star_rating = 3
        mock_record.created_at = "2024-01-01"
        mock_record.part_scores = []

        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_record]

        result = await get_all_history(mock_db)

        assert len(result) == 1
        assert result[0].student_name == "Student1"

    @pytest.mark.asyncio
    async def test_get_all_history_empty(self, mock_db):
        """测试空历史记录"""
        mock_db.query.return_value.order_by.return_value.all.return_value = []

        result = await get_all_history(mock_db)

        assert len(result) == 0


class TestGetHistoryByStudent:
    """测试获取学生历史记录"""

    @pytest.mark.asyncio
    async def test_get_student_history_success(self, mock_db):
        """测试成功获取学生历史"""
        mock_record = Mock()
        mock_record.id = 1
        mock_record.student_name = "TestStudent"
        mock_record.level = "level1"
        mock_record.unit = "unit1-3"
        mock_record.total_score = 35
        mock_record.star_rating = 3
        mock_record.created_at = "2024-01-01"
        mock_record.part_scores = []

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_record]

        result = await get_history("TestStudent", mock_db)

        assert len(result) == 1
        assert result[0].student_name == "TestStudent"

    @pytest.mark.asyncio
    async def test_get_student_history_empty(self, mock_db):
        """测试学生无历史记录"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        result = await get_history("NonExistent", mock_db)

        assert len(result) == 0


class TestGetResultById:
    """测试通过 ID 获取结果"""

    @pytest.mark.asyncio
    async def test_get_result_success(self, mock_db):
        """测试成功获取结果"""
        mock_record = Mock()
        mock_record.id = 1
        mock_record.student_name = "TestStudent"
        mock_record.level = "level1"
        mock_record.unit = "unit1-3"
        mock_record.total_score = 35
        mock_record.star_rating = 3
        mock_record.created_at = "2024-01-01"
        mock_record.part_scores = []

        mock_db.query.return_value.filter.return_value.first.return_value = mock_record

        result = await get_result_by_id(1, mock_db)

        assert result.id == 1
        assert result.student_name == "TestStudent"

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, mock_db):
        """测试结果不存在"""
        from fastapi import HTTPException

        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_result_by_id(999, mock_db)

        assert exc_info.value.status_code == 404
        assert "不存在" in exc_info.value.detail


class TestAudioFileHandling:
    """测试音频文件处理"""

    @pytest.mark.asyncio
    @patch("api.scoring.is_xfyun_configured", return_value=True)
    @patch("api.scoring.evaluate_words_with_xfyun")
    @patch("api.scoring.evaluate_part2_all_with_xfyun")
    @patch("api.scoring.cleanup_service")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("api.scoring.QUESTIONS_FILE", "/fake/questions.json")
    @patch("api.scoring.Path")
    async def test_audio_files_saved(
        self, mock_path, mock_open, mock_cleanup, mock_part2, mock_part1, mock_xfyun,
        mock_db, mock_part1_audio, mock_part2_audio, sample_questions_data
    ):
        """测试音频文件保存"""
        # Mock 文件
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(sample_questions_data).encode()
        mock_open.return_value.__enter__.return_value = mock_file

        mock_upload_dir = Mock()
        mock_upload_dir.mkdir = Mock()
        mock_upload_dir.absolute.return_value = "/uploads"
        mock_path.return_value = mock_upload_dir

        # Mock 讯飞结果
        mock_part1.return_value = {
            "score": 3,
            "total": 3,
            "correct_words": ["hello"],
            "incorrect_words": [],
            "accuracy_score": 90.0,
            "fluency_score": 85.0,
            "feedback": "优秀"
        }

        mock_part2.return_value = {
            "total_score": 20,
            "question_scores": [],
            "summary": {"fluency_score": 8.0, "pronunciation_score": 7.0, "confidence_score": 8.0},
            "feedback": "良好"
        }

        # Mock 数据库
        mock_test_record = Mock()
        mock_test_record.id = 1
        mock_test_record.part_scores = []
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # 执行
        await evaluate_test(
            student_name="TestStudent",
            level="level1",
            unit="unit1-3",
            part1_audio=mock_part1_audio,
            part2_audio=mock_part2_audio,
            db=mock_db
        )

        # 验证音频文件记录被添加
        assert mock_db.add.called


class TestCleanupScheduling:
    """测试清理任务调度"""

    @pytest.mark.asyncio
    @patch("api.scoring.is_xfyun_configured", return_value=True)
    @patch("api.scoring.evaluate_words_with_xfyun")
    @patch("api.scoring.evaluate_part2_all_with_xfyun")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("api.scoring.QUESTIONS_FILE", "/fake/questions.json")
    @patch("api.scoring.Path")
    async def test_cleanup_scheduled(
        self, mock_path, mock_open, mock_part2, mock_part1, mock_xfyun,
        mock_db, mock_part1_audio, mock_part2_audio, sample_questions_data
    ):
        """测试清理任务被调度"""
        # Mock 文件
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(sample_questions_data).encode()
        mock_open.return_value.__enter__.return_value = mock_file

        mock_upload_dir = Mock()
        mock_upload_dir.mkdir = Mock()
        mock_path.return_value = mock_upload_dir

        # Mock 讯飞结果
        mock_part1.return_value = {
            "score": 3,
            "total": 3,
            "correct_words": [],
            "incorrect_words": [],
            "accuracy_score": 90.0,
            "fluency_score": 85.0,
            "feedback": "优秀"
        }

        mock_part2.return_value = {
            "total_score": 20,
            "question_scores": [],
            "summary": {"fluency_score": 8.0, "pronunciation_score": 7.0, "confidence_score": 8.0},
            "feedback": "良好"
        }

        # Mock 清理服务
        mock_cleanup_service = Mock()
        mock_cleanup_service.schedule_cleanup = Mock()

        # Mock 数据库
        mock_test_record = Mock()
        mock_test_record.id = 1
        mock_test_record.part_scores = []
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        with patch("api.scoring.cleanup_service", mock_cleanup_service):
            await evaluate_test(
                student_name="TestStudent",
                level="level1",
                unit="unit1-3",
                part1_audio=mock_part1_audio,
                part2_audio=mock_part2_audio,
                db=mock_db
            )

        # 验证清理任务被调度
        mock_cleanup_service.schedule_cleanup.assert_called_once()


class TestCostCalculation:
    """测试成本计算"""

    @pytest.mark.asyncio
    @patch("api.scoring.is_xfyun_configured", return_value=False)
    @patch("api.scoring.evaluate_part1")
    @patch("api.scoring.evaluate_part2_all")
    @patch("api.scoring.cleanup_service")
    @patch("api.scoring.calculate_cost")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("api.scoring.QUESTIONS_FILE", "/fake/questions.json")
    async def test_api_cost_calculated(
        self, mock_open, mock_calculate_cost, mock_cleanup, mock_part2, mock_part1, mock_xfyun,
        mock_db, mock_part1_audio, mock_part2_audio, sample_questions_data
    ):
        """测试 API 成本计算"""
        # Mock 文件
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(sample_questions_data).encode()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock Gemini 结果
        mock_part1.return_value = (18, {
            "feedback": "良好",
            "correct_words": [],
            "incorrect_words": []
        })

        mock_part2.return_value = (20, [
            {"question_num": 1, "score": 2, "feedback": "好"}
        ], {
            "fluency_score": 8.0,
            "pronunciation_score": 7.5,
            "confidence_score": 8.0
        })

        mock_calculate_cost.return_value = 0.05

        # Mock 数据库
        mock_test_record = Mock()
        mock_test_record.id = 1
        mock_test_record.part_scores = []
        mock_db.add = Mock()
        mock_db.flush = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        await evaluate_test(
            student_name="TestStudent",
            level="level1",
            unit="unit1-3",
            part1_audio=mock_part1_audio,
            part2_audio=mock_part2_audio,
            db=mock_db
        )

        # 验证成本计算被调用
        assert mock_calculate_cost.called
