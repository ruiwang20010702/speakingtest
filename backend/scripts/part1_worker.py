#!/usr/bin/env python3
"""
Part 1 评测任务消费者 Worker
从 RabbitMQ 队列拉取任务并执行评测
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from src.infrastructure.queue_service import Part1TaskConsumer, Part1Task
from src.infrastructure.database import AsyncSessionLocal
from src.use_cases.evaluate_part1 import ProcessPart1TaskUseCase
from src.adapters.gateways.qwen_client import QwenOmniGateway


async def handle_task(task: Part1Task) -> bool:
    """处理 Part1 评测任务"""
    try:
        logger.info(f"Worker 开始处理 Part 1 任务: {task.task_id}")
        
        # 创建数据库会话和 Gateway
        async with AsyncSessionLocal() as db:
            qwen_gateway = QwenOmniGateway()
            use_case = ProcessPart1TaskUseCase(db=db, qwen_gateway=qwen_gateway)
            
            success = await use_case.execute(task)
            
            if success:
                logger.info(f"Part 1 任务 {task.task_id} 处理成功")
            else:
                logger.warning(f"Part 1 任务 {task.task_id} 处理失败")
            
            return success
            
    except Exception as e:
        logger.exception(f"Part 1 任务 {task.task_id} 处理异常: {e}")
        return False


async def main():
    """启动 Part 1 Worker"""
    logger.info("=" * 50)
    logger.info("Part 1 Worker 启动中...")
    logger.info("=" * 50)
    
    consumer = Part1TaskConsumer(process_func=handle_task)
    
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Part 1 Worker 收到退出信号")
    finally:
        await consumer.close()
        logger.info("Part 1 Worker 已关闭")


if __name__ == "__main__":
    asyncio.run(main())
