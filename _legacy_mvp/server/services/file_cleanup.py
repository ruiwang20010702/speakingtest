"""
录音文件清理服务
在生成报告后1小时自动删除录音文件，节省存储空间
"""
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from models import TestRecord, AudioFile
from database import SessionLocal


class FileCleanupService:
    """录音文件定时清理服务"""
    
    def __init__(self, cleanup_delay_hours: int = 1):
        """
        初始化清理服务
        
        Args:
            cleanup_delay_hours: 报告生成后多少小时清理文件（默认1小时）
        """
        self.cleanup_delay_hours = cleanup_delay_hours
        self.cleanup_tasks = {}  # 存储待清理任务
    
    def schedule_cleanup(self, test_record_id: int, audio_files: List[str]):
        """
        调度文件清理任务
        
        Args:
            test_record_id: 测试记录ID
            audio_files: 需要清理的音频文件路径列表
        """
        # 创建异步清理任务
        task = asyncio.create_task(
            self._cleanup_after_delay(test_record_id, audio_files)
        )
        self.cleanup_tasks[test_record_id] = task
        print(f"🗑️ 已调度清理任务: 测试#{test_record_id}, {len(audio_files)}个文件, {self.cleanup_delay_hours}小时后清理")
    
    async def _cleanup_after_delay(self, test_record_id: int, audio_files: List[str]):
        """
        延迟后执行清理
        
        Args:
            test_record_id: 测试记录ID
            audio_files: 音频文件路径列表
        """
        try:
            # 等待指定时间
            await asyncio.sleep(self.cleanup_delay_hours * 3600)
            
            # 执行清理
            deleted_count = 0
            for file_path in audio_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        print(f"✅ 已删除: {Path(file_path).name}")
                    except Exception as e:
                        print(f"❌ 删除失败: {file_path}, 错误: {e}")
            
            # 更新数据库记录（标记文件已清理）
            db = SessionLocal()
            try:
                audio_records = db.query(AudioFile).filter(
                    AudioFile.test_record_id == test_record_id
                ).all()
                
                for record in audio_records:
                    record.file_path = None  # 清空路径标记已删除
                    record.deleted_at = datetime.now()
                
                db.commit()
                print(f"🗑️ 清理完成: 测试#{test_record_id}, 删除{deleted_count}/{len(audio_files)}个文件")
            finally:
                db.close()
            
            # 清理任务记录
            if test_record_id in self.cleanup_tasks:
                del self.cleanup_tasks[test_record_id]
                
        except asyncio.CancelledError:
            print(f"⚠️ 清理任务被取消: 测试#{test_record_id}")
        except Exception as e:
            print(f"❌ 清理任务失败: 测试#{test_record_id}, 错误: {e}")
    
    def cancel_cleanup(self, test_record_id: int):
        """
        取消清理任务（如果用户需要保留文件）
        
        Args:
            test_record_id: 测试记录ID
        """
        if test_record_id in self.cleanup_tasks:
            self.cleanup_tasks[test_record_id].cancel()
            del self.cleanup_tasks[test_record_id]
            print(f"✅ 已取消清理任务: 测试#{test_record_id}")
    
    def get_pending_cleanups(self) -> int:
        """获取待清理任务数量"""
        return len(self.cleanup_tasks)


# 全局清理服务实例
cleanup_service = FileCleanupService(cleanup_delay_hours=1)
