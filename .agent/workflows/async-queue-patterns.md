---
description: Implement async message queue patterns with RabbitMQ and Redis for task offloading and rate limiting.
---

# Async Queue Patterns

Implement reliable asynchronous task processing using message queues to handle background jobs, rate limiting, and traffic smoothing.

## When to Use This Skill

- Offloading time-consuming tasks (AI processing, file conversion)
- Rate limiting external API calls (respecting RPM limits)
- Decoupling services in microservices architecture
- Handling traffic spikes with queue buffering
- Implementing retry logic for failed tasks
- Building worker-based processing pipelines

## Core Concepts

### 1. Producer-Consumer Pattern

- **Producer**: Publishes tasks to queue
- **Queue**: Stores tasks (FIFO or priority)
- **Consumer (Worker)**: Processes tasks from queue

### 2. Queue Types

| Type | Use Case | Tool |
| :--- | :--- | :--- |
| **Task Queue** | Background jobs | RabbitMQ, Redis Queue |
| **Pub/Sub** | Event broadcasting | Redis Pub/Sub, RabbitMQ Fanout |
| **Priority Queue** | VIP processing | RabbitMQ with priority |

### 3. Delivery Guarantees

- **At-most-once**: Fast, may lose messages
- **At-least-once**: Reliable, may duplicate (use idempotency)
- **Exactly-once**: Complex, usually simulated

## RabbitMQ Patterns (aio-pika)

### Pattern 1: Basic Producer

```python
import asyncio
import json
from aio_pika import connect_robust, Message, DeliveryMode

class RabbitMQProducer:
    """Async RabbitMQ producer."""
    
    def __init__(self, url: str, queue_name: str):
        self.url = url
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """Establish connection."""
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(self.queue_name, durable=True)
    
    async def publish(self, task_data: dict):
        """Publish task to queue."""
        message = Message(
            body=json.dumps(task_data).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,  # Survive broker restart
        )
        await self.channel.default_exchange.publish(
            message,
            routing_key=self.queue_name,
        )
    
    async def close(self):
        """Close connection."""
        if self.connection:
            await self.connection.close()

# Usage
async def main():
    producer = RabbitMQProducer("amqp://guest:guest@localhost/", "tasks")
    await producer.connect()
    
    await producer.publish({
        "task_id": "123",
        "type": "evaluate_part2",
        "test_id": 456,
        "audio_url": "https://oss.example.com/audio.mp3"
    })
    
    await producer.close()
```

### Pattern 2: Consumer with Rate Limiting

```python
import asyncio
import json
from aio_pika import connect_robust, IncomingMessage

class RateLimitedConsumer:
    """
    Consumer with rate limiting.
    Processes at most N tasks per minute.
    """
    
    def __init__(self, url: str, queue_name: str, rpm_limit: int = 60):
        self.url = url
        self.queue_name = queue_name
        self.rpm_limit = rpm_limit
        self.interval = 60.0 / rpm_limit  # Seconds between tasks
        self.connection = None
    
    async def connect(self):
        """Establish connection with prefetch limit."""
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()
        
        # Prefetch 1: Only get next message after current is ACKed
        await self.channel.set_qos(prefetch_count=1)
        
        self.queue = await self.channel.declare_queue(
            self.queue_name,
            durable=True,
        )
    
    async def process_task(self, task_data: dict) -> bool:
        """
        Override this method to implement task processing.
        Return True on success, False on failure.
        """
        raise NotImplementedError
    
    async def on_message(self, message: IncomingMessage):
        """Handle incoming message with rate limiting."""
        async with message.process():  # Auto-ACK on success
            task_data = json.loads(message.body.decode())
            
            try:
                success = await self.process_task(task_data)
                if not success:
                    # Optionally requeue or move to dead letter queue
                    pass
            except Exception as e:
                # Log error, message will be NACKed and requeued
                raise
            finally:
                # Rate limiting delay
                await asyncio.sleep(self.interval)
    
    async def start(self):
        """Start consuming messages."""
        await self.connect()
        await self.queue.consume(self.on_message)
        
        # Keep running
        await asyncio.Future()

# Usage
class Part2EvaluationConsumer(RateLimitedConsumer):
    async def process_task(self, task_data: dict) -> bool:
        test_id = task_data["test_id"]
        audio_url = task_data["audio_url"]
        
        # Call Qwen API (rate limited by consumer interval)
        result = await evaluate_with_qwen(audio_url)
        
        # Save result to database
        await save_result(test_id, result)
        
        return True
```

### Pattern 3: Dead Letter Queue (Failed Tasks)

```python
from aio_pika import ExchangeType

async def setup_with_dlq(channel, queue_name: str):
    """
    Setup queue with Dead Letter Queue for failed messages.
    """
    # Declare DLQ exchange and queue
    dlq_exchange = await channel.declare_exchange(
        f"{queue_name}_dlx",
        ExchangeType.DIRECT,
    )
    dlq_queue = await channel.declare_queue(
        f"{queue_name}_dlq",
        durable=True,
    )
    await dlq_queue.bind(dlq_exchange, routing_key=queue_name)
    
    # Main queue with DLQ routing
    main_queue = await channel.declare_queue(
        queue_name,
        durable=True,
        arguments={
            "x-dead-letter-exchange": f"{queue_name}_dlx",
            "x-dead-letter-routing-key": queue_name,
        },
    )
    
    return main_queue, dlq_queue
```

## Redis Queue Patterns (Simple Alternative)

### Pattern 4: Redis List as Queue

```python
import asyncio
import json
import redis.asyncio as redis

class RedisQueue:
    """Simple Redis-based queue using LIST."""
    
    def __init__(self, redis_url: str, queue_name: str):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.client = None
    
    async def connect(self):
        self.client = redis.from_url(self.redis_url)
    
    async def push(self, task_data: dict):
        """Add task to queue (LPUSH for FIFO with BRPOP)."""
        await self.client.lpush(
            self.queue_name,
            json.dumps(task_data)
        )
    
    async def pop(self, timeout: int = 0) -> dict | None:
        """
        Pop task from queue (blocking).
        timeout=0 means block forever.
        """
        result = await self.client.brpop(self.queue_name, timeout=timeout)
        if result:
            _, data = result
            return json.loads(data)
        return None
    
    async def length(self) -> int:
        """Get queue length."""
        return await self.client.llen(self.queue_name)

# Consumer loop
async def worker(queue: RedisQueue, rpm_limit: int = 60):
    interval = 60.0 / rpm_limit
    
    while True:
        task = await queue.pop(timeout=30)
        if task:
            await process_task(task)
            await asyncio.sleep(interval)  # Rate limit
```

### Pattern 5: Priority Queue with Sorted Set

```python
import time

class RedisPriorityQueue:
    """Priority queue using Redis ZSET."""
    
    async def push(self, task_data: dict, priority: int = 0):
        """
        Push with priority (lower = higher priority).
        Use timestamp for FIFO within same priority.
        """
        score = priority * 1e10 + time.time()
        await self.client.zadd(
            self.queue_name,
            {json.dumps(task_data): score}
        )
    
    async def pop(self) -> dict | None:
        """Pop highest priority task."""
        # ZPOPMIN returns lowest score = highest priority
        result = await self.client.zpopmin(self.queue_name)
        if result:
            data, _ = result[0]
            return json.loads(data)
        return None
```

## Best Practices

1. **Idempotency**: Design tasks to be safely re-processed
2. **Visibility Timeout**: Hide message while processing to prevent duplicates
3. **Retry with Backoff**: Exponential backoff for failed tasks
4. **Monitoring**: Track queue length, processing time, failure rate
5. **Dead Letter Queue**: Capture permanently failed tasks for analysis

## Checklist

- [ ] Queue connection is robust (auto-reconnect)?
- [ ] Messages are persistent (survive broker restart)?
- [ ] Consumer has prefetch limit set?
- [ ] Rate limiting is implemented for external APIs?
- [ ] Failed tasks go to DLQ for analysis?
- [ ] Tasks are idempotent (safe to retry)?
