#!/usr/bin/env python3
"""
报告解读任务消费者 Worker
从 RabbitMQ 队列拉取任务并执行 AI 生成
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.infrastructure.queue_service import InterpretationTaskConsumer, InterpretationTask
from src.use_cases.evaluate_interpretation import process_interpretation_task


async def handle_task(task: InterpretationTask) -> bool:
    """处理报告解读任务"""
    try:
        logger.info(f"Worker 开始处理报告解读任务: {task.task_id}")
        success = await process_interpretation_task(task)
        
        if success:
            logger.info(f"报告解读任务 {task.task_id} 处理成功")
        else:
            logger.warning(f"报告解读任务 {task.task_id} 处理失败")
        
        return success
        
    except Exception as e:
        logger.exception(f"报告解读任务 {task.task_id} 处理异常: {e}")
        # 异常会被 consumer 捕获并触发重试
        raise


async def main():
    """启动报告解读 Worker"""
    logger.info("=" * 50)
    logger.info("Interpretation Worker 启动中...")
    logger.info("=" * 50)
    
    consumer = InterpretationTaskConsumer(process_func=handle_task)
    
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Interpretation Worker 收到退出信号")
    finally:
        await consumer.close()
        logger.info("Interpretation Worker 已关闭")


if __name__ == "__main__":
    asyncio.run(main())
