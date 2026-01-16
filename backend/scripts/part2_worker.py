#!/usr/bin/env python3
"""
Part 2 评测任务消费者 Worker
从 RabbitMQ 队列拉取任务并执行评测
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.infrastructure.queue_service import Part2TaskConsumer, Part2Task
from src.infrastructure.database import AsyncSessionLocal
from src.use_cases.evaluate_part2 import ProcessPart2TaskUseCase
from src.adapters.gateways.qwen_client import QwenOmniGateway


MAX_RETRIES = 5  # 最大重试次数


async def check_retry_limit(test_id: int) -> tuple[bool, int]:
    """检查是否超过重试限制，返回 (is_exceeded, current_count)"""
    from sqlalchemy import text
    
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


async def handle_task(task: Part2Task) -> bool:
    """处理 Part2 评测任务"""
    from sqlalchemy import text
    from src.infrastructure.timezone import now as china_now
    
    # 首先检查重试次数
    exceeded, retry_count = await check_retry_limit(task.test_id)
    if exceeded:
        logger.warning(f"Part 2 任务 {task.task_id} 超过最大重试次数 ({retry_count}/{MAX_RETRIES}) 或已完成，跳过处理")
        # 确保标记为失败
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("UPDATE tests SET status = 'failed', failure_reason = :reason, updated_at = :now WHERE id = :id AND status NOT IN ('completed', 'failed')"),
                    {"reason": f"超过最大重试次数 ({MAX_RETRIES})", "now": china_now(), "id": task.test_id}
                )
                await db.commit()
        except Exception as e:
            logger.error(f"标记任务失败出错: {e}")
        return True  # 返回 True 以从队列移除消息
    
    try:
        logger.info(f"Worker 开始处理 Part 2 任务: {task.task_id} (重试 {retry_count}/{MAX_RETRIES})")
        
        # 创建数据库会话和 Gateway
        async with AsyncSessionLocal() as db:
            qwen_gateway = QwenOmniGateway()
            use_case = ProcessPart2TaskUseCase(db=db, qwen_gateway=qwen_gateway)
            
            success = await use_case.execute(task)
            
            if success:
                logger.info(f"Part 2 任务 {task.task_id} 处理成功")
            else:
                logger.warning(f"Part 2 任务 {task.task_id} 处理失败")
            
            return success
            
    except Exception as e:
        logger.exception(f"Part 2 任务 {task.task_id} 处理异常: {e}")
        # 确保异常时也更新数据库状态为 failed
        try:
            async with AsyncSessionLocal() as db:
                # 增加重试次数并检查是否应该标记为失败
                await db.execute(
                    text("""
                        UPDATE tests 
                        SET retry_count = COALESCE(retry_count, 0) + 1,
                            failure_reason = :reason, 
                            updated_at = :now,
                            status = CASE WHEN COALESCE(retry_count, 0) + 1 >= :max_retry THEN 'failed' ELSE status END
                        WHERE id = :id
                    """),
                    {"reason": f"Worker 异常: {str(e)[:200]}", "now": china_now(), "id": task.test_id, "max_retry": MAX_RETRIES}
                )
                await db.commit()
                logger.info(f"已更新 test_id={task.test_id} 重试次数")
        except Exception as db_error:
            logger.error(f"更新测试状态失败: {db_error}")
        return False


async def main():
    """启动 Worker"""
    logger.info("=" * 50)
    logger.info("Part 2 Worker 启动中...")
    logger.info("=" * 50)
    
    consumer = Part2TaskConsumer(process_func=handle_task)
    
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Worker 收到退出信号")
    finally:
        await consumer.close()
        logger.info("Worker 已关闭")


if __name__ == "__main__":
    asyncio.run(main())
