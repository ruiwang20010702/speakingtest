"""
Part 2 消息队列服务
基于 /async-queue-patterns 实现异步任务处理
"""
import asyncio
import json
from typing import Callable, Awaitable
from dataclasses import dataclass

from aio_pika import connect_robust, Message, DeliveryMode, IncomingMessage
from loguru import logger

from src.infrastructure.config import get_settings

settings = get_settings()


@dataclass
class Part2Task:
    """Part 2 评测任务"""
    task_id: str
    test_id: int
    audio_url: str  # OSS URL
    questions: list  # 12 道题目
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "test_id": self.test_id,
            "audio_url": self.audio_url,
            "questions": self.questions
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Part2Task":
        return cls(
            task_id=data["task_id"],
            test_id=data["test_id"],
            audio_url=data["audio_url"],
            questions=data["questions"]
        )


class Part2TaskProducer:
    """
    Part 2 任务生产者
    将评测任务发布到 RabbitMQ 队列
    """
    
    QUEUE_NAME = "part2_evaluation_tasks"
    
    def __init__(self, rabbitmq_url: str = None):
        self.url = rabbitmq_url or settings.RABBITMQ_URL
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """建立连接"""
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        
        # 声明持久化队列
        await self.channel.declare_queue(
            self.QUEUE_NAME,
            durable=True
        )
        logger.info(f"Part2TaskProducer 已连接到 {self.QUEUE_NAME}")
    
    async def publish(self, task: Part2Task):
        """
        发布评测任务到队列
        
        Args:
            task: Part2Task 任务对象
        """
        if not self.channel:
            await self.connect()
        
        message = Message(
            body=json.dumps(task.to_dict()).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,  # 持久化，防止 broker 重启丢失
        )
        
        await self.channel.default_exchange.publish(
            message,
            routing_key=self.QUEUE_NAME,
        )
        
        logger.info(f"已发布 Part2 任务: task_id={task.task_id}, test_id={task.test_id}")
    
    async def close(self):
        """关闭连接"""
        if self.connection:
            await self.connection.close()
            logger.info("Part2TaskProducer 连接已关闭")


class Part2TaskConsumer:
    """
    Part 2 任务消费者
    从队列拉取任务并执行评测
    
    特性:
    - 限速: 60 RPM (每秒最多 1 个请求)
    - prefetch=1: 一次只处理一个任务
    - 自动重试: 失败任务会被 NACK 并重新入队
    """
    
    QUEUE_NAME = "part2_evaluation_tasks"
    RPM_LIMIT = 60  # Qwen API 限制
    
    def __init__(
        self,
        process_func: Callable[[Part2Task], Awaitable[bool]],
        rabbitmq_url: str = None
    ):
        """
        Args:
            process_func: 处理任务的异步函数，返回 True 表示成功
        """
        self.url = rabbitmq_url or settings.RABBITMQ_URL
        self.process_func = process_func
        self.connection = None
        self.channel = None
        self.interval = 60.0 / self.RPM_LIMIT  # 1 秒/请求
    
    async def connect(self):
        """建立连接，设置 prefetch"""
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        
        # prefetch=1: 确保一次只处理一个任务
        await self.channel.set_qos(prefetch_count=1)
        
        self.queue = await self.channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
        )
        
        logger.info(f"Part2TaskConsumer 已连接，限速: {self.RPM_LIMIT} RPM")
    
    async def _on_message(self, message: IncomingMessage):
        """处理消息"""
        async with message.process():  # 自动 ACK/NACK
            try:
                task_data = json.loads(message.body.decode())
                task = Part2Task.from_dict(task_data)
                
                logger.info(f"开始处理 Part2 任务: {task.task_id}")
                
                # 调用处理函数
                success = await self.process_func(task)
                
                if success:
                    logger.info(f"Part2 任务完成: {task.task_id}")
                else:
                    logger.warning(f"Part2 任务失败: {task.task_id}")
                    # 注意: 这里不抛异常，message.process() 仍会 ACK
                    # 如果需要重试，应该在 process_func 中处理
                    
            except Exception as e:
                logger.exception(f"Part2 任务处理异常: {e}")
                raise  # 抛出异常会触发 NACK 并重新入队
            
            finally:
                # 限速等待
                await asyncio.sleep(self.interval)
    
    async def start(self):
        """启动消费者"""
        await self.connect()
        await self.queue.consume(self._on_message)
        
        logger.info("Part2TaskConsumer 已启动，等待任务...")
        
        # 保持运行
        await asyncio.Future()
    
    async def close(self):
        """关闭连接"""
        if self.connection:
            await self.connection.close()


# ============================================
# 便捷函数
# ============================================

async def enqueue_part2_task(task: Part2Task):
    """快速入队一个 Part2 任务"""
    producer = Part2TaskProducer()
    try:
        await producer.connect()
        await producer.publish(task)
    finally:
        await producer.close()


# ============================================
# Part 1 任务队列 (结构类似 Part 2)
# ============================================

@dataclass
class Part1Task:
    """Part 1 评测任务"""
    task_id: str
    test_id: int
    audio_url: str  # OSS URL
    reference_text: str  # 朗读参考文本
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "test_id": self.test_id,
            "audio_url": self.audio_url,
            "reference_text": self.reference_text
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Part1Task":
        return cls(
            task_id=data["task_id"],
            test_id=data["test_id"],
            audio_url=data["audio_url"],
            reference_text=data["reference_text"]
        )


class Part1TaskProducer:
    """Part 1 任务生产者"""
    
    QUEUE_NAME = "part1_evaluation_tasks"
    
    def __init__(self, rabbitmq_url: str = None):
        self.url = rabbitmq_url or settings.RABBITMQ_URL
        self.connection = None
        self.channel = None
    
    async def connect(self):
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(self.QUEUE_NAME, durable=True)
        logger.info(f"Part1TaskProducer 已连接到 {self.QUEUE_NAME}")
    
    async def publish(self, task: Part1Task):
        if not self.channel:
            await self.connect()
        
        message = Message(
            body=json.dumps(task.to_dict()).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        
        await self.channel.default_exchange.publish(
            message,
            routing_key=self.QUEUE_NAME,
        )
        logger.info(f"已发布 Part1 任务: task_id={task.task_id}, test_id={task.test_id}")
    
    async def close(self):
        if self.connection:
            await self.connection.close()


class Part1TaskConsumer:
    """Part 1 任务消费者"""
    
    QUEUE_NAME = "part1_evaluation_tasks"
    RPM_LIMIT = 60
    
    def __init__(
        self,
        process_func: Callable[[Part1Task], Awaitable[bool]],
        rabbitmq_url: str = None
    ):
        self.url = rabbitmq_url or settings.RABBITMQ_URL
        self.process_func = process_func
        self.connection = None
        self.channel = None
        self.interval = 60.0 / self.RPM_LIMIT
    
    async def connect(self):
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)
        self.queue = await self.channel.declare_queue(self.QUEUE_NAME, durable=True)
        logger.info(f"Part1TaskConsumer 已连接，限速: {self.RPM_LIMIT} RPM")
    
    async def _on_message(self, message: IncomingMessage):
        async with message.process():
            try:
                task_data = json.loads(message.body.decode())
                task = Part1Task.from_dict(task_data)
                logger.info(f"开始处理 Part1 任务: {task.task_id}")
                
                success = await self.process_func(task)
                
                if success:
                    logger.info(f"Part1 任务完成: {task.task_id}")
                else:
                    logger.warning(f"Part1 任务失败: {task.task_id}")
                    
            except Exception as e:
                logger.exception(f"Part1 任务处理异常: {e}")
                raise
            finally:
                await asyncio.sleep(self.interval)
    
    async def start(self):
        await self.connect()
        await self.queue.consume(self._on_message)
        logger.info("Part1TaskConsumer 已启动，等待任务...")
        await asyncio.Future()
    
    async def close(self):
        if self.connection:
            await self.connection.close()


async def enqueue_part1_task(task: Part1Task):
    """快速入队一个 Part1 任务"""
    producer = Part1TaskProducer()
    try:
        await producer.connect()
        await producer.publish(task)
    finally:
        await producer.close()
