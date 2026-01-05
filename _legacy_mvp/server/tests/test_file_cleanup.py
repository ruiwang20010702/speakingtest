"""
测试录音文件清理服务
"""
import pytest
import asyncio
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from services.file_cleanup import FileCleanupService, cleanup_service


@pytest.fixture
def temp_audio_files(tmp_path):
    """创建临时音频文件用于测试"""
    files = []
    for i in range(3):
        file_path = tmp_path / f"audio_{i}.m4a"
        file_path.write_text(f"dummy audio content {i}")
        files.append(str(file_path))
    return files


@pytest.fixture
def mock_db_session():
    """Mock 数据库会话"""
    session = Mock(spec=Session)
    return session


class TestFileCleanupServiceInit:
    """测试 FileCleanupService 初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        service = FileCleanupService()
        assert service.cleanup_delay_hours == 1
        assert service.cleanup_tasks == {}

    def test_custom_delay_hours(self):
        """测试自定义延迟时间"""
        service = FileCleanupService(cleanup_delay_hours=2)
        assert service.cleanup_delay_hours == 2
        assert service.cleanup_tasks == {}


class TestScheduleCleanup:
    """测试调度清理任务"""

    def test_schedule_cleanup(self):
        """测试调度清理任务"""
        service = FileCleanupService(cleanup_delay_hours=0)  # 0小时用于快速测试
        test_record_id = 123
        audio_files = ["/path/to/audio1.m4a", "/path/to/audio2.m4a"]

        service.schedule_cleanup(test_record_id, audio_files)

        assert test_record_id in service.cleanup_tasks
        assert service.get_pending_cleanups() == 1

        # 取消任务避免影响其他测试
        service.cancel_cleanup(test_record_id)

    def test_schedule_multiple_cleanups(self):
        """测试调度多个清理任务"""
        service = FileCleanupService(cleanup_delay_hours=0)

        service.schedule_cleanup(1, ["/path1.m4a"])
        service.schedule_cleanup(2, ["/path2.m4a"])
        service.schedule_cleanup(3, ["/path3.m4a"])

        assert service.get_pending_cleanups() == 3

        # 清理
        service.cancel_cleanup(1)
        service.cancel_cleanup(2)
        service.cancel_cleanup(3)


class TestCleanupAfterDelay:
    """测试延迟清理执行"""

    @pytest.mark.asyncio
    async def test_cleanup_after_delay_deletes_files(self, temp_audio_files):
        """测试延迟后删除文件"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123

        # Mock database
        mock_audio_record_1 = Mock()
        mock_audio_record_2 = Mock()
        mock_audio_record_3 = Mock()

        with patch("services.file_cleanup.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = [
                mock_audio_record_1,
                mock_audio_record_2,
                mock_audio_record_3
            ]

            # 执行清理
            await service._cleanup_after_delay(test_record_id, temp_audio_files)

            # 验证文件被删除
            for file_path in temp_audio_files:
                assert not os.path.exists(file_path)

            # 验证数据库更新
            assert mock_session.query.called
            for record in [mock_audio_record_1, mock_audio_record_2, mock_audio_record_3]:
                assert record.file_path is None
                assert record.deleted_at is not None

    @pytest.mark.asyncio
    async def test_cleanup_handles_nonexistent_files(self):
        """测试处理不存在的文件"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123
        nonexistent_files = ["/nonexistent/file1.m4a", "/nonexistent/file2.m4a"]

        with patch("services.file_cleanup.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = []

            # 不应该抛出异常
            await service._cleanup_after_delay(test_record_id, nonexistent_files)

            # 验证数据库操作仍然执行
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_handles_file_deletion_errors(self, temp_audio_files):
        """测试处理文件删除错误"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123

        # Mock os.remove 来模拟删除失败
        original_remove = os.remove
        call_count = [0]

        def mock_remove_with_error(path):
            call_count[0] += 1
            if call_count[0] == 1:
                raise PermissionError(f"Permission denied: {path}")
            return original_remove(path)

        with patch("os.remove", side_effect=mock_remove_with_error):
            with patch("services.file_cleanup.SessionLocal") as mock_session_local:
                mock_session = Mock()
                mock_session_local.return_value = mock_session
                mock_session.query.return_value.filter.return_value.all.return_value = []

                # 应该继续执行，不抛出异常
                await service._cleanup_after_delay(test_record_id, temp_audio_files)

                # 验证至少尝试删除了文件
                assert call_count[0] > 0


class TestCancelCleanup:
    """测试取消清理任务"""

    def test_cancel_existing_task(self):
        """测试取消存在的任务"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123

        service.schedule_cleanup(test_record_id, ["/path.m4a"])
        assert service.get_pending_cleanups() == 1

        service.cancel_cleanup(test_record_id)

        assert service.get_pending_cleanups() == 0
        assert test_record_id not in service.cleanup_tasks

    def test_cancel_nonexistent_task(self):
        """测试取消不存在的任务"""
        service = FileCleanupService()

        # 不应该抛出异常
        service.cancel_cleanup(999)
        assert service.get_pending_cleanups() == 0


class TestGetPendingCleanups:
    """测试获取待清理任务数量"""

    def test_get_pending_cleanups_empty(self):
        """测试空任务列表"""
        service = FileCleanupService()
        assert service.get_pending_cleanups() == 0

    def test_get_pending_cleanups_with_tasks(self):
        """测试有任务时的计数"""
        service = FileCleanupService(cleanup_delay_hours=0)

        assert service.get_pending_cleanups() == 0

        service.schedule_cleanup(1, ["/path1.m4a"])
        assert service.get_pending_cleanups() == 1

        service.schedule_cleanup(2, ["/path2.m4a"])
        assert service.get_pending_cleanups() == 2

        service.cancel_cleanup(1)
        assert service.get_pending_cleanups() == 1


class TestAsyncTaskCleanup:
    """测试异步任务自动清理"""

    @pytest.mark.asyncio
    async def test_task_removed_after_completion(self, temp_audio_files):
        """测试任务完成后自动移除"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123

        with patch("services.file_cleanup.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = []

            # 等待清理完成
            await service._cleanup_after_delay(test_record_id, temp_audio_files)

            # 任务应该被自动移除
            assert test_record_id not in service.cleanup_tasks


class TestDatabaseIntegration:
    """测试数据库集成"""

    @pytest.mark.asyncio
    async def test_database_session_closed(self, temp_audio_files):
        """测试数据库会话正确关闭"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123

        with patch("services.file_cleanup.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = []

            await service._cleanup_after_delay(test_record_id, temp_audio_files)

            # 验证会话被关闭
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_commit_on_success(self, temp_audio_files):
        """测试成功时提交数据库更改"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123

        with patch("services.file_cleanup.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            mock_audio_record = Mock()
            mock_session.query.return_value.filter.return_value.all.return_value = [mock_audio_record]

            await service._cleanup_after_delay(test_record_id, temp_audio_files)

            # 验证提交
            mock_session.commit.assert_called_once()

            # 验证字段更新
            assert mock_audio_record.file_path is None
            assert isinstance(mock_audio_record.deleted_at, datetime)


class TestCancelledErrorHandling:
    """测试任务取消错误处理"""

    @pytest.mark.asyncio
    async def test_cleanup_handles_cancelled_error(self):
        """测试处理 CancelledError"""
        service = FileCleanupService(cleanup_delay_hours=1)
        test_record_id = 123

        # 创建一个会被取消的任务
        task = asyncio.create_task(
            service._cleanup_after_delay(test_record_id, ["/path.m4a"])
        )

        # 立即取消
        task.cancel()

        # 应该抛出 CancelledError
        with pytest.raises(asyncio.CancelledError):
            await task


class TestGeneralExceptionHandling:
    """测试一般异常处理"""

    @pytest.mark.asyncio
    async def test_cleanup_handles_database_errors(self, temp_audio_files):
        """测试处理数据库错误"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123

        with patch("services.file_cleanup.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            # 模拟数据库查询失败
            mock_session.query.side_effect = Exception("Database connection lost")

            # 不应该抛出异常
            await service._cleanup_after_delay(test_record_id, temp_audio_files)


class TestGlobalCleanupService:
    """测试全局清理服务实例"""

    def test_global_service_exists(self):
        """测试全局服务实例存在"""
        assert cleanup_service is not None
        assert isinstance(cleanup_service, FileCleanupService)

    def test_global_service_default_config(self):
        """测试全局服务默认配置"""
        assert cleanup_service.cleanup_delay_hours == 1


class TestFileCleanupIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_cleanup_workflow(self, temp_audio_files):
        """测试完整的清理工作流"""
        service = FileCleanupService(cleanup_delay_hours=0)
        test_record_id = 123

        # 1. 调度清理
        service.schedule_cleanup(test_record_id, temp_audio_files)
        assert service.get_pending_cleanups() == 1

        # 2. 等待清理完成
        with patch("services.file_cleanup.SessionLocal") as mock_session_local:
            mock_session = Mock()
            mock_session_local.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = []

            await service._cleanup_after_delay(test_record_id, temp_audio_files)

        # 3. 验证文件被删除
        for file_path in temp_audio_files:
            assert not os.path.exists(file_path)

        # 4. 验证任务被移除
        assert service.get_pending_cleanups() == 0
