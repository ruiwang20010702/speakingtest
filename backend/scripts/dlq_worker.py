#!/usr/bin/env python3
"""
死信队列消费者启动脚本

处理所有评测队列的失败任务，自动更新数据库状态为 failed。

用法:
    cd backend
    python scripts/dlq_worker.py

功能:
    - 监听 3 个死信队列:
      * part1_evaluation_tasks_dlq
      * part2_evaluation_tasks_dlq
      * interpretation_tasks_dlq
    - 当任务进入死信队列时，自动更新数据库:
      * status = 'failed'
      * failure_reason = 错误信息
      * retry_count = 重试次数
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.infrastructure.queue_service import start_dlq_consumers


async def main():
    """启动死信队列消费者"""
    logger.info("=" * 50)
    logger.info("死信队列消费者启动中...")
    logger.info("=" * 50)
    
    try:
        await start_dlq_consumers()
    except KeyboardInterrupt:
        logger.info("收到退出信号，正在关闭...")
    except Exception as e:
        logger.exception(f"死信队列消费者异常退出: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
