"""
Part 1 Evaluation Use Case
Orchestrates the speech evaluation flow for Part 1 (reading).
"""
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import TestModel
from src.adapters.gateways.qwen_client import QwenOmniGateway, Part1EvaluationResult
from src.adapters.gateways.oss_client import upload_test_audio


@dataclass
class Part1EvaluationRequest:
    """Request for Part 1 evaluation."""
    test_id: int
    reference_text: str
    audio_data: bytes


@dataclass
class Part1EvaluationResponse:
    """Response from Part 1 evaluation."""
    success: bool
    test_id: int 
    score: Optional[float] = None
    fluency_score: Optional[float] = None
    pronunciation_score: Optional[float] = None
    audio_url: Optional[str] = None  # 新增：OSS URL
    error: Optional[str] = None


class EvaluatePart1UseCase:
    """
    Use case for evaluating Part 1 reading.
    
    Flow:
    1. Validate test exists and is in correct state
    2. Call Xunfei API for evaluation
    3. Upload audio to OSS
    4. Parse and store scores + audio URL
    5. Update test status
    """

    def __init__(self, db: AsyncSession, qwen_gateway: QwenOmniGateway):
        self.db = db
        self.qwen = qwen_gateway

    async def execute(self, request: Part1EvaluationRequest) -> Part1EvaluationResponse:
        """
        Execute Part 1 evaluation.
        
        Args:
            request: Part1EvaluationRequest with test_id, text, and audio
            
        Returns:
            Part1EvaluationResponse with scores or error
        """
        # 1. Find test
        stmt = select(TestModel).where(TestModel.id == request.test_id)
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()

        if not test:
            return Part1EvaluationResponse(
                success=False,
                test_id=request.test_id,
                error="Test not found"
            )

        # 2. Check test state
        if test.status not in ("pending", "part1_done"):
            return Part1EvaluationResponse(
                success=False,
                test_id=request.test_id,
                error=f"Invalid test status: {test.status}"
            )

        logger.info(f"Starting Part 1 evaluation for test {request.test_id}")

        # 3. Call Qwen API
        try:
            # Qwen expects audio format, assuming pcm/wav for now based on previous flow
            # In a real scenario, we might need to know the actual format from the request or header
            # For now, we pass "pcm" as default or "wav" if we know it. 
            # Since Xunfei used PCM, we assume raw data. Qwen might need WAV header.
            # But let's try passing "pcm" and let the client handle it (client defaults to wav in data url)
            
            evaluation_result = await self.qwen.evaluate_part1_reading(
                audio_data=request.audio_data,
                reference_text=request.reference_text,
                audio_format="pcm" 
            )
        except Exception as e:
            logger.exception(f"Qwen Part 1 API error: {e}")
            return Part1EvaluationResponse(
                success=False,
                test_id=request.test_id,
                error=f"Evaluation service error: {str(e)}"
            )

        # 4. 上传音频到 OSS (无论评分是否成功都尝试上传)
        audio_url = None
        try:
            oss_result = await upload_test_audio(
                audio_data=request.audio_data,
                test_id=request.test_id,
                part="part1",
                extension="pcm"  # 讯飞使用 PCM 格式，Qwen 也兼容
            )
            if oss_result.success:
                audio_url = oss_result.url
                logger.info(f"Part 1 音频已上传: {audio_url}")
            else:
                logger.warning(f"Part 1 音频上传失败: {oss_result.error}")
        except Exception as e:
            logger.warning(f"OSS 上传异常（不影响评测结果）: {e}")

        # 5. Handle result
        if not evaluation_result.success:
            test.failure_reason = evaluation_result.error
            test.retry_count += 1
            test.part1_audio_url = audio_url # 即使失败也保存音频链接
            await self.db.commit()
            
            return Part1EvaluationResponse(
                success=False,
                test_id=request.test_id,
                error=evaluation_result.error,
                audio_url=audio_url
            )

        # 6. Store scores + audio URL + Cost
        # 直接存储 Qwen 返回的百分制分数 (0-100)
        test.part1_score = evaluation_result.total_score
        test.part1_raw_result = evaluation_result.to_dict()
        test.part1_audio_url = audio_url  # 保存音频 URL
        test.status = "part1_done"
        test.updated_at = datetime.now(timezone.utc)
        
        # Calculate Cost
        # Pricing (Qwen3-Omni-Flash):
        # Input Text: 0.0018 / 1k
        # Input Audio: 0.0158 / 1k
        # Output: 0.0127 / 1k
        if evaluation_result.usage:
            usage = evaluation_result.usage
            # Note: Qwen usage usually has prompt_tokens, completion_tokens.
            # It might break down prompt_tokens into audio_tokens and text_tokens in prompt_tokens_details.
            # If not available, we estimate.
            
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            # Try to get detailed breakdown
            prompt_details = usage.get("prompt_tokens_details", {})
            audio_tokens = prompt_details.get("audio_tokens", 0)
            text_tokens = prompt_details.get("text_tokens", 0)
            
            # Fallback if details missing: assume mostly audio for Part 1 input?
            # Actually Part 1 input is text + audio. 
            # If no breakdown, we might under-calculate if we assume all text, or over if all audio.
            # Let's assume if audio_tokens is 0 but we sent audio, maybe it's not broken down.
            # But Qwen-Omni usually provides this.
            
            if audio_tokens == 0 and text_tokens == 0 and prompt_tokens > 0:
                # Fallback: Estimate based on prompt length?
                # Text prompt is short (~100 chars). Audio is the main part.
                # Let's assume 90% audio tokens if not specified? Or just treat as audio for safety?
                # To be safe/conservative, treat as audio (more expensive).
                audio_tokens = prompt_tokens
            
            cost = (
                (text_tokens * 0.0018 / 1000) +
                (audio_tokens * 0.0158 / 1000) +
                (completion_tokens * 0.0127 / 1000)
            )
            
            # Update TestModel
            test.cost = (test.cost or 0) + cost
            
            # Update tokens_used with structured data
            current_usage = test.tokens_used or {}
            if not isinstance(current_usage, dict):
                current_usage = {}
                
            current_usage["part1"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "audio_tokens": audio_tokens,
                "text_tokens": text_tokens,
                "total_tokens": usage.get("total_tokens", 0),
                "cost": float(f"{cost:.6f}")
            }
            test.tokens_used = current_usage
            
            logger.info(f"Part 1 Cost: {cost:.4f} RMB, Usage: {current_usage['part1']}")

        await self.db.commit()
        
        logger.info(f"Part 1 completed for test {request.test_id}, score: {evaluation_result.total_score}")

        return Part1EvaluationResponse(
            success=True,
            test_id=request.test_id,
            score=evaluation_result.total_score,
            fluency_score=evaluation_result.fluency_score,
            pronunciation_score=evaluation_result.pronunciation_score,
            audio_url=audio_url
        )


# ============================================
# 异步版本：用于队列处理
# ============================================

import uuid
from src.infrastructure.queue_service import Part1Task, enqueue_part1_task


@dataclass
class SubmitPart1Request:
    """Part 1 提交请求（异步模式）"""
    test_id: int
    audio_url: str  # OSS URL (已上传)
    reference_text: str


@dataclass
class SubmitPart1Response:
    """Part 1 提交响应（异步模式）"""
    success: bool
    task_id: Optional[str] = None
    message: str = ""


class SubmitPart1UseCase:
    """
    提交 Part 1 评测任务（入队，立即返回）
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def execute(self, request: SubmitPart1Request) -> SubmitPart1Response:
        # 1. 查找测评
        stmt = select(TestModel).where(TestModel.id == request.test_id)
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()
        
        if not test:
            return SubmitPart1Response(success=False, message="测评记录不存在")
        
        if test.status != "pending":
            return SubmitPart1Response(
                success=False,
                message=f"无法提交 Part 1：当前状态为 {test.status}"
            )
        
        # 2. 创建任务
        task_id = str(uuid.uuid4())[:8]
        task = Part1Task(
            task_id=task_id,
            test_id=request.test_id,
            audio_url=request.audio_url,
            reference_text=request.reference_text
        )
        
        # 3. 入队
        try:
            await enqueue_part1_task(task)
        except Exception as e:
            logger.exception(f"Part 1 任务入队失败: {e}")
            return SubmitPart1Response(
                success=False,
                message=f"任务入队失败: {str(e)}"
            )
        
        # 4. 更新状态
        test.status = "part1_processing"
        test.part1_audio_url = request.audio_url  # 保存音频 URL
        test.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        logger.info(f"Part 1 任务已入队: task_id={task_id}, test_id={request.test_id}")
        
        return SubmitPart1Response(
            success=True,
            task_id=task_id,
            message="评测任务已提交，正在后台处理"
        )


class ProcessPart1TaskUseCase:
    """
    处理 Part 1 评测任务（消费者调用）
    """
    
    def __init__(self, db: AsyncSession, qwen_gateway: QwenOmniGateway):
        self.db = db
        self.qwen = qwen_gateway
    
    async def execute(self, task: Part1Task) -> bool:
        # 1. 查找测评
        stmt = select(TestModel).where(TestModel.id == task.test_id)
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()
        
        if not test:
            logger.error(f"测评不存在: {task.test_id}")
            return False
        
        # 2. 下载音频
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(task.audio_url, timeout=60)
                response.raise_for_status()
                audio_data = response.content
        except Exception as e:
            logger.error(f"下载音频失败: {e}")
            test.failure_reason = f"音频下载失败: {str(e)}"
            test.retry_count += 1
            await self.db.commit()
            return False
        
        # 3. 调用 Qwen API
        try:
            evaluation_result = await self.qwen.evaluate_part1_reading(
                audio_data=audio_data,
                reference_text=task.reference_text,
                audio_format="mp3"  # OSS 上传的是 mp3
            )
        except Exception as e:
            logger.exception(f"Qwen Part 1 API error: {e}")
            test.failure_reason = str(e)
            test.retry_count += 1
            await self.db.commit()
            return False
        
        # 4. 处理结果
        if not evaluation_result.success:
            test.failure_reason = evaluation_result.error
            test.retry_count += 1
            await self.db.commit()
            return False
        
        # 5. 存储分数
        test.part1_score = evaluation_result.total_score
        test.part1_raw_result = evaluation_result.to_dict()
        test.status = "part1_done"
        test.updated_at = datetime.now(timezone.utc)
        
        # 6. 计算成本
        if evaluation_result.usage:
            usage = evaluation_result.usage
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            prompt_details = usage.get("prompt_tokens_details", {})
            audio_tokens = prompt_details.get("audio_tokens", 0)
            text_tokens = prompt_details.get("text_tokens", 0)
            
            if audio_tokens == 0 and text_tokens == 0 and prompt_tokens > 0:
                audio_tokens = prompt_tokens
            
            cost = (
                (text_tokens * 0.0018 / 1000) +
                (audio_tokens * 0.0158 / 1000) +
                (completion_tokens * 0.0127 / 1000)
            )
            
            test.cost = (test.cost or 0) + cost
            current_usage = test.tokens_used or {}
            if not isinstance(current_usage, dict):
                current_usage = {}
            current_usage["part1"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "audio_tokens": audio_tokens,
                "text_tokens": text_tokens,
                "total_tokens": usage.get("total_tokens", 0),
                "cost": float(f"{cost:.6f}")
            }
            test.tokens_used = current_usage
            
            logger.info(f"Part 1 Cost: {cost:.4f} RMB")
        
        await self.db.commit()
        logger.info(f"Part 1 评测完成: test_id={task.test_id}, score={test.part1_score}")
        return True
