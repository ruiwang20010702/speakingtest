#!/usr/bin/env python3
"""
Part 2 评测任务消费者 Worker
从 RabbitMQ 队列拉取任务并执行评测

已重构：使用 base_worker 模块复用通用逻辑
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.queue_service import Part2TaskConsumer, Part2Task
from src.use_cases.evaluate_part2 import ProcessPart2TaskUseCase

from base_worker import create_task_handler, run_worker


# 创建 Part 2 任务处理函数
handle_task = create_task_handler(
    part_name="Part 2",
    use_case_factory=ProcessPart2TaskUseCase,
    get_test_id=lambda task: task.test_id,
    get_task_id=lambda task: task.task_id
)


async def main():
    """启动 Part 2 Worker"""
    await run_worker(
        worker_name="Part 2 Worker",
        consumer_class=Part2TaskConsumer,
        task_handler=handle_task
    )


if __name__ == "__main__":
    asyncio.run(main())
