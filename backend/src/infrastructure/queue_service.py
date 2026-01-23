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

# ============================================
# 死信队列配置
# ============================================
DLQ_MAX_RETRIES = 3  # 最大重试次数（超过后进入死信队列）
DLQ_SUFFIX = "_dlq"  # 死信队列后缀
DLX_SUFFIX = "_dlx"  # 死信交换机后缀


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
    - 限速: 可配置 RPM (通过 QWEN_OMNI_RPM 环境变量)
    - prefetch: 可配置 (通过 QWEN_OMNI_CONCURRENCY * QUEUE_PREFETCH_MULTIPLIER)
    - 自动重试: 失败任务会被 NACK 并重新入队
    
    性能说明:
    - 默认 prefetch=5, RPM=60 → 单消费者约 1 QPS
    - 扩容建议: 启动多个消费者实例，或提升 Qwen 账号配额
    """
    
    QUEUE_NAME = "part2_evaluation_tasks"
    
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
        # 可配置的限速参数
        self.rpm_limit = settings.QWEN_OMNI_RPM
        self.interval = 60.0 / self.rpm_limit if self.rpm_limit > 0 else 0
        self.prefetch = settings.QWEN_OMNI_CONCURRENCY * settings.QUEUE_PREFETCH_MULTIPLIER
        self.disable_sleep = settings.QUEUE_DISABLE_SLEEP
    
    async def connect(self):
        """建立连接，配置死信队列"""
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        
        # 可配置的 prefetch，配合并发限流
        await self.channel.set_qos(prefetch_count=self.prefetch)
        
        # 声明死信交换机
        dlx_name = f"{self.QUEUE_NAME}{DLX_SUFFIX}"
        self.dlx = await self.channel.declare_exchange(
            dlx_name,
            type="fanout",
            durable=True
        )
        
        # 声明死信队列
        dlq_name = f"{self.QUEUE_NAME}{DLQ_SUFFIX}"
        self.dlq = await self.channel.declare_queue(
            dlq_name,
            durable=True
        )
        
        # 绑定死信队列到死信交换机
        await self.dlq.bind(self.dlx)
        
        # 主队列配置：失败消息发送到死信交换机
        self.queue = await self.channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": dlx_name,
            }
        )
        
        logger.info(
            f"Part2TaskConsumer 已连接，prefetch={self.prefetch}, "
            f"RPM={self.rpm_limit}, DLQ={dlq_name}"
        )
    
    async def _on_message(self, message: IncomingMessage):
        """处理消息，带重试次数限制"""
        # 获取当前重试次数（从消息头中读取）
        headers = message.headers or {}
        retry_count = headers.get("x-retry-count", 0)
        task_data = None
        
        try:
            task_data = json.loads(message.body.decode())
            task = Part2Task.from_dict(task_data)
            
            logger.info(f"开始处理 Part2 任务: {task.task_id} (重试: {retry_count}/{DLQ_MAX_RETRIES})")
            
            # 调用处理函数
            success = await self.process_func(task)
            
            if success:
                logger.info(f"Part2 任务完成: {task.task_id}")
                await message.ack()  # 成功，确认消息
            else:
                # 业务逻辑失败
                logger.warning(f"Part2 任务业务失败: {task.task_id}")
                await self._handle_failure(message, task_data, retry_count, "业务逻辑返回失败")
                
        except Exception as e:
            logger.exception(f"Part2 任务处理异常: {e}")
            await self._handle_failure(
                message, 
                task_data or {}, 
                retry_count, 
                str(e)[:200]
            )
            
        finally:
            # 限速等待（可通过 QUEUE_DISABLE_SLEEP=true 禁用，用于压测）
            if not self.disable_sleep and self.interval > 0:
                await asyncio.sleep(self.interval)
    
    async def _handle_failure(self, message: IncomingMessage, task_data: dict, retry_count: int, error_msg: str):
        """处理任务失败：重试或进入死信队列"""
        if retry_count < DLQ_MAX_RETRIES:
            # 重新入队，增加重试计数
            new_retry_count = retry_count + 1
            logger.warning(
                f"Part2 任务失败，重新入队 (第 {new_retry_count}/{DLQ_MAX_RETRIES} 次重试)"
            )
            
            # 发送新消息（带更新的重试计数）
            new_message = Message(
                body=json.dumps(task_data).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                headers={
                    "x-retry-count": new_retry_count,
                    "x-last-error": error_msg
                }
            )
            
            await self.channel.default_exchange.publish(
                new_message,
                routing_key=self.QUEUE_NAME,
            )
            
            # ACK 原消息（避免自动重入队）
            await message.ack()
        else:
            # 达到最大重试次数，拒绝消息（进入死信队列）
            logger.error(
                f"Part2 任务达到最大重试次数 ({DLQ_MAX_RETRIES})，进入死信队列。"
                f"错误: {error_msg}"
            )
            await message.reject(requeue=False)
    
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
    """Part 1 任务消费者 (可配置化限流)"""
    
    QUEUE_NAME = "part1_evaluation_tasks"
    
    def __init__(
        self,
        process_func: Callable[[Part1Task], Awaitable[bool]],
        rabbitmq_url: str = None
    ):
        self.url = rabbitmq_url or settings.RABBITMQ_URL
        self.process_func = process_func
        self.connection = None
        self.channel = None
        # 可配置的限速参数
        self.rpm_limit = settings.QWEN_OMNI_RPM
        self.interval = 60.0 / self.rpm_limit if self.rpm_limit > 0 else 0
        self.prefetch = settings.QWEN_OMNI_CONCURRENCY * settings.QUEUE_PREFETCH_MULTIPLIER
        self.disable_sleep = settings.QUEUE_DISABLE_SLEEP
    
    async def connect(self):
        """建立连接，配置死信队列"""
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=self.prefetch)
        
        # 声明死信交换机
        dlx_name = f"{self.QUEUE_NAME}{DLX_SUFFIX}"
        self.dlx = await self.channel.declare_exchange(
            dlx_name,
            type="fanout",
            durable=True
        )
        
        # 声明死信队列
        dlq_name = f"{self.QUEUE_NAME}{DLQ_SUFFIX}"
        self.dlq = await self.channel.declare_queue(
            dlq_name,
            durable=True
        )
        
        # 绑定死信队列到死信交换机
        await self.dlq.bind(self.dlx)
        
        # 主队列配置：失败消息发送到死信交换机
        self.queue = await self.channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": dlx_name,
            }
        )
        
        logger.info(
            f"Part1TaskConsumer 已连接，prefetch={self.prefetch}, "
            f"RPM={self.rpm_limit}, DLQ={dlq_name}"
        )
    
    async def _on_message(self, message: IncomingMessage):
        """处理消息，带重试次数限制"""
        # 获取当前重试次数
        headers = message.headers or {}
        retry_count = headers.get("x-retry-count", 0)
        task_data = None
        
        try:
            task_data = json.loads(message.body.decode())
            task = Part1Task.from_dict(task_data)
            logger.info(f"开始处理 Part1 任务: {task.task_id} (重试: {retry_count}/{DLQ_MAX_RETRIES})")
            
            success = await self.process_func(task)
            
            if success:
                logger.info(f"Part1 任务完成: {task.task_id}")
                await message.ack()
            else:
                logger.warning(f"Part1 任务业务失败: {task.task_id}")
                await self._handle_failure(message, task_data, retry_count, "业务逻辑返回失败")
                    
        except Exception as e:
            logger.exception(f"Part1 任务处理异常: {e}")
            await self._handle_failure(
                message,
                task_data or {},
                retry_count,
                str(e)[:200]
            )
        finally:
            if not self.disable_sleep and self.interval > 0:
                await asyncio.sleep(self.interval)
    
    async def _handle_failure(self, message: IncomingMessage, task_data: dict, retry_count: int, error_msg: str):
        """处理任务失败：重试或进入死信队列"""
        if retry_count < DLQ_MAX_RETRIES:
            new_retry_count = retry_count + 1
            logger.warning(
                f"Part1 任务失败，重新入队 (第 {new_retry_count}/{DLQ_MAX_RETRIES} 次重试)"
            )
            
            new_message = Message(
                body=json.dumps(task_data).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                headers={
                    "x-retry-count": new_retry_count,
                    "x-last-error": error_msg
                }
            )
            
            await self.channel.default_exchange.publish(
                new_message,
                routing_key=self.QUEUE_NAME,
            )
            
            await message.ack()
        else:
            logger.error(
                f"Part1 任务达到最大重试次数 ({DLQ_MAX_RETRIES})，进入死信队列。"
                f"错误: {error_msg}"
            )
            await message.reject(requeue=False)
    
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


# ============================================
# Interpretation 任务队列 (报告解读异步化)
# ============================================

@dataclass
class InterpretationTask:
    """报告解读任务"""
    task_id: str
    test_id: int
    # 以下数据用于生成解读
    student_name: str
    level: str
    total_score: float
    part1_score: float
    part2_score: float
    star_level: int
    part1_details: dict  # Part 1 评测详情
    part2_items: list    # Part 2 题目详情
    radar_data: list     # 雷达图数据
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "test_id": self.test_id,
            "student_name": self.student_name,
            "level": self.level,
            "total_score": self.total_score,
            "part1_score": self.part1_score,
            "part2_score": self.part2_score,
            "star_level": self.star_level,
            "part1_details": self.part1_details,
            "part2_items": self.part2_items,
            "radar_data": self.radar_data,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InterpretationTask":
        return cls(
            task_id=data["task_id"],
            test_id=data["test_id"],
            student_name=data["student_name"],
            level=data["level"],
            total_score=data["total_score"],
            part1_score=data["part1_score"],
            part2_score=data["part2_score"],
            star_level=data["star_level"],
            part1_details=data["part1_details"],
            part2_items=data["part2_items"],
            radar_data=data["radar_data"],
        )


class InterpretationTaskProducer:
    """报告解读任务生产者"""
    
    QUEUE_NAME = "interpretation_tasks"
    
    def __init__(self, rabbitmq_url: str = None):
        self.url = rabbitmq_url or settings.RABBITMQ_URL
        self.connection = None
        self.channel = None
    
    async def connect(self):
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(self.QUEUE_NAME, durable=True)
        logger.info(f"InterpretationTaskProducer 已连接到 {self.QUEUE_NAME}")
    
    async def publish(self, task: InterpretationTask):
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
        logger.info(f"已发布 Interpretation 任务: task_id={task.task_id}, test_id={task.test_id}")
    
    async def close(self):
        if self.connection:
            await self.connection.close()


class InterpretationTaskConsumer:
    """
    报告解读任务消费者 (使用 qwen-plus，可配置化限流)
    
    特性:
    - 最大重试 3 次
    - prefetch: 可配置 (通过 QWEN_PLUS_CONCURRENCY)
    - 限速: 可配置 RPM (通过 QWEN_PLUS_RPM)
    """
    
    QUEUE_NAME = "interpretation_tasks"
    MAX_RETRIES = 3
    
    def __init__(
        self,
        process_func: Callable[[InterpretationTask], Awaitable[bool]],
        rabbitmq_url: str = None
    ):
        self.url = rabbitmq_url or settings.RABBITMQ_URL
        self.process_func = process_func
        self.connection = None
        self.channel = None
        # 使用 qwen-plus 的配置（RPM 更高）
        self.rpm_limit = settings.QWEN_PLUS_RPM
        self.interval = 60.0 / self.rpm_limit if self.rpm_limit > 0 else 0
        self.prefetch = settings.QWEN_PLUS_CONCURRENCY * settings.QUEUE_PREFETCH_MULTIPLIER
        self.disable_sleep = settings.QUEUE_DISABLE_SLEEP
    
    async def connect(self):
        """建立连接，配置死信队列"""
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=self.prefetch)
        
        # 声明死信交换机
        dlx_name = f"{self.QUEUE_NAME}{DLX_SUFFIX}"
        self.dlx = await self.channel.declare_exchange(
            dlx_name,
            type="fanout",
            durable=True
        )
        
        # 声明死信队列
        dlq_name = f"{self.QUEUE_NAME}{DLQ_SUFFIX}"
        self.dlq = await self.channel.declare_queue(
            dlq_name,
            durable=True
        )
        
        # 绑定死信队列到死信交换机
        await self.dlq.bind(self.dlx)
        
        # 主队列配置：失败消息发送到死信交换机
        self.queue = await self.channel.declare_queue(
            self.QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": dlx_name,
            }
        )
        
        logger.info(
            f"InterpretationTaskConsumer 已连接，prefetch={self.prefetch}, "
            f"RPM={self.rpm_limit}, DLQ={dlq_name}"
        )
    
    async def _on_message(self, message: IncomingMessage):
        """处理消息，带重试次数限制"""
        # 获取当前重试次数
        headers = message.headers or {}
        retry_count = headers.get("x-retry-count", 0)
        task_data = None
        
        try:
            task_data = json.loads(message.body.decode())
            task = InterpretationTask.from_dict(task_data)
            logger.info(f"开始处理 Interpretation 任务: {task.task_id} (重试: {retry_count}/{DLQ_MAX_RETRIES})")
            
            success = await self.process_func(task)
            
            if success:
                logger.info(f"Interpretation 任务完成: {task.task_id}")
                await message.ack()
            else:
                logger.warning(f"Interpretation 任务业务失败: {task.task_id}")
                await self._handle_failure(message, task_data, retry_count, "业务逻辑返回失败")
                    
        except Exception as e:
            logger.exception(f"Interpretation 任务处理异常: {e}")
            await self._handle_failure(
                message,
                task_data or {},
                retry_count,
                str(e)[:200]
            )
        finally:
            if not self.disable_sleep and self.interval > 0:
                await asyncio.sleep(self.interval)
    
    async def _handle_failure(self, message: IncomingMessage, task_data: dict, retry_count: int, error_msg: str):
        """处理任务失败：重试或进入死信队列"""
        if retry_count < DLQ_MAX_RETRIES:
            new_retry_count = retry_count + 1
            logger.warning(
                f"Interpretation 任务失败，重新入队 (第 {new_retry_count}/{DLQ_MAX_RETRIES} 次重试)"
            )
            
            new_message = Message(
                body=json.dumps(task_data).encode(),
                delivery_mode=DeliveryMode.PERSISTENT,
                headers={
                    "x-retry-count": new_retry_count,
                    "x-last-error": error_msg
                }
            )
            
            await self.channel.default_exchange.publish(
                new_message,
                routing_key=self.QUEUE_NAME,
            )
            
            await message.ack()
        else:
            logger.error(
                f"Interpretation 任务达到最大重试次数 ({DLQ_MAX_RETRIES})，进入死信队列。"
                f"错误: {error_msg}"
            )
            await message.reject(requeue=False)
    
    async def start(self):
        await self.connect()
        await self.queue.consume(self._on_message)
        logger.info("InterpretationTaskConsumer 已启动，等待任务...")
        await asyncio.Future()
    
    async def close(self):
        if self.connection:
            await self.connection.close()


async def enqueue_interpretation_task(task: InterpretationTask):
    """快速入队一个 Interpretation 任务"""
    producer = InterpretationTaskProducer()
    try:
        await producer.connect()
        await producer.publish(task)
    finally:
        await producer.close()


# ============================================
# 死信队列消费者 (自动标记失败任务)
# ============================================

class DeadLetterConsumer:
    """
    死信队列消费者
    自动处理进入死信队列的失败任务：更新数据库状态为 failed
    
    用法:
        consumer = DeadLetterConsumer("part2_evaluation_tasks_dlq")
        await consumer.start()
    """
    
    def __init__(self, queue_name: str, rabbitmq_url: str = None):
        """
        Args:
            queue_name: 死信队列名称（如 part2_evaluation_tasks_dlq）
        """
        self.url = rabbitmq_url or settings.RABBITMQ_URL
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """建立连接"""
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        
        # 声明死信队列（应该已存在，这里是确保存在）
        self.queue = await self.channel.declare_queue(
            self.queue_name,
            durable=True
        )
        logger.info(f"DeadLetterConsumer 已连接到 {self.queue_name}")
    
    async def _on_message(self, message: IncomingMessage):
        """处理死信消息：更新数据库状态"""
        async with message.process():
            try:
                task_data = json.loads(message.body.decode())
                test_id = task_data.get("test_id")
                task_id = task_data.get("task_id", "unknown")
                
                # 获取错误信息（从消息头中读取）
                headers = message.headers or {}
                error_msg = headers.get("x-last-error", "未知错误")
                retry_count = headers.get("x-retry-count", DLQ_MAX_RETRIES)
                
                logger.error(
                    f"死信队列处理: queue={self.queue_name}, task_id={task_id}, "
                    f"test_id={test_id}, 重试次数={retry_count}, 错误={error_msg}"
                )
                
                # 更新数据库状态
                if test_id:
                    await self._mark_test_failed(test_id, error_msg, retry_count)
                else:
                    logger.warning(f"死信消息缺少 test_id: {task_data}")
                    
            except Exception as e:
                logger.exception(f"死信队列处理异常: {e}")
    
    async def _mark_test_failed(self, test_id: int, error_msg: str, retry_count: int):
        """更新测试记录为失败状态"""
        from src.infrastructure.database import AsyncSessionLocal
        from src.adapters.repositories.models import TestModel
        from src.infrastructure.timezone import now as china_now
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            try:
                stmt = select(TestModel).where(TestModel.id == test_id)
                result = await db.execute(stmt)
                test = result.scalar_one_or_none()
                
                if test:
                    test.status = "failed"
                    test.failure_reason = f"队列重试 {retry_count} 次后失败: {error_msg[:200]}"
                    test.retry_count = retry_count
                    test.updated_at = china_now()
                    await db.commit()
                    logger.info(f"已标记测试 {test_id} 为失败状态")
                else:
                    logger.warning(f"找不到测试记录: test_id={test_id}")
            except Exception as e:
                logger.exception(f"更新测试状态失败: test_id={test_id}, error={e}")
                await db.rollback()
    
    async def start(self):
        """启动消费者"""
        await self.connect()
        await self.queue.consume(self._on_message)
        logger.info(f"DeadLetterConsumer 已启动，监听 {self.queue_name}...")
        await asyncio.Future()
    
    async def close(self):
        """关闭连接"""
        if self.connection:
            await self.connection.close()


async def start_dlq_consumers():
    """
    启动所有死信队列消费者
    
    用法:
        python -c "import asyncio; from src.infrastructure.queue_service import start_dlq_consumers; asyncio.run(start_dlq_consumers())"
    """
    dlq_queues = [
        "part1_evaluation_tasks_dlq",
        "part2_evaluation_tasks_dlq",
        "interpretation_tasks_dlq",
    ]
    
    logger.info(f"启动死信队列消费者，监听 {len(dlq_queues)} 个队列...")
    
    # 创建消费者实例
    consumers = [DeadLetterConsumer(q) for q in dlq_queues]
    
    # 并发启动所有消费者
    await asyncio.gather(*[c.start() for c in consumers])
