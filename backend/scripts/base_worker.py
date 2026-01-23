#!/usr/bin/env python3
"""
Base Worker 模块
提供通用的任务消费者逻辑，用于 Part 1 和 Part 2 Worker 复用。
"""
import asyncio
import sys
from pathlib import Path
from typing import TypeVar, Generic, Callable, Awaitable, Type

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from src.infrastructure.database import AsyncSessionLocal
from src.infrastructure.timezone import now as china_now


# 最大重试次数
MAX_RETRIES = 5

# 泛型任务类型
T = TypeVar('T')


async def check_retry_limit(test_id: int) -> tuple[bool, int]:
    """
    检查是否超过重试限制
    
    Args:
        test_id: 测试 ID
        
    Returns:
        (is_exceeded, current_count): 是否超限, 当前重试次数
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT retry_count, status FROM tests WHERE id = :id"),
            {"id": test_id}
        )
        row = result.first()
        if not row:
            return True, 0  # 记录不存在，不处理
        
        retry_count = row[0] or 0
        status = row[1]
        
        # 如果已经完成或已经失败，不再处理
        if status in ("completed", "failed"):
            return True, retry_count
        
        return retry_count >= MAX_RETRIES, retry_count


async def mark_task_failed(test_id: int, reason: str) -> None:
    """
    将任务标记为失败
    
    Args:
        test_id: 测试 ID
        reason: 失败原因
    """
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("UPDATE tests SET status = 'failed', failure_reason = :reason, updated_at = :now WHERE id = :id AND status NOT IN ('completed', 'failed')"),
                {"reason": reason, "now": china_now(), "id": test_id}
            )
            await db.commit()
    except Exception as e:
        logger.error(f"标记任务失败出错: {e}")


async def increment_retry_count(test_id: int, reason: str) -> None:
    """
    增加重试次数并更新失败原因
    
    Args:
        test_id: 测试 ID
        reason: 失败原因
    """
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    UPDATE tests 
                    SET retry_count = COALESCE(retry_count, 0) + 1,
                        failure_reason = :reason, 
                        updated_at = :now,
                        status = CASE WHEN COALESCE(retry_count, 0) + 1 >= :max_retry THEN 'failed' ELSE status END
                    WHERE id = :id
                """),
                {"reason": reason[:200], "now": china_now(), "id": test_id, "max_retry": MAX_RETRIES}
            )
            await db.commit()
            logger.info(f"已更新 test_id={test_id} 重试次数")
    except Exception as db_error:
        logger.error(f"更新测试状态失败: {db_error}")


def create_task_handler(
    part_name: str,
    use_case_factory: Callable,
    get_test_id: Callable[[T], int],
    get_task_id: Callable[[T], str]
) -> Callable[[T], Awaitable[bool]]:
    """
    创建任务处理函数的工厂方法
    
    Args:
        part_name: 任务名称 (e.g., "Part 1", "Part 2")
        use_case_factory: UseCase 工厂函数，接收 (db, qwen_gateway) 参数
        get_test_id: 从任务对象获取 test_id 的函数
        get_task_id: 从任务对象获取 task_id 的函数
        
    Returns:
        异步任务处理函数
    """
    async def handle_task(task: T) -> bool:
        test_id = get_test_id(task)
        task_id = get_task_id(task)
        
        # 首先检查重试次数
        exceeded, retry_count = await check_retry_limit(test_id)
        if exceeded:
            logger.warning(f"{part_name} 任务 {task_id} 超过最大重试次数 ({retry_count}/{MAX_RETRIES}) 或已完成，跳过处理")
            await mark_task_failed(test_id, f"超过最大重试次数 ({MAX_RETRIES})")
            return True  # 返回 True 以从队列移除消息
        
        try:
            logger.info(f"Worker 开始处理 {part_name} 任务: {task_id} (重试 {retry_count}/{MAX_RETRIES})")
            
            # 创建数据库会话和 Gateway
            from src.adapters.gateways.qwen_client import QwenOmniGateway
            
            async with AsyncSessionLocal() as db:
                qwen_gateway = QwenOmniGateway()
                use_case = use_case_factory(db=db, qwen_gateway=qwen_gateway)
                
                success = await use_case.execute(task)
                
                if success:
                    logger.info(f"{part_name} 任务 {task_id} 处理成功")
                else:
                    logger.warning(f"{part_name} 任务 {task_id} 处理失败")
                
                return success
                
        except Exception as e:
            logger.exception(f"{part_name} 任务 {task_id} 处理异常: {e}")
            await increment_retry_count(test_id, f"Worker 异常: {str(e)}")
            return False
    
    return handle_task


async def run_worker(
    worker_name: str,
    consumer_class: Type,
    task_handler: Callable
) -> None:
    """
    运行 Worker 的通用入口
    
    Args:
        worker_name: Worker 名称 (用于日志)
        consumer_class: 消费者类
        task_handler: 任务处理函数
    """
    logger.info("=" * 50)
    logger.info(f"{worker_name} 启动中...")
    logger.info("=" * 50)
    
    consumer = consumer_class(process_func=task_handler)
    
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info(f"{worker_name} 收到退出信号")
    finally:
        await consumer.close()
        logger.info(f"{worker_name} 已停止")
