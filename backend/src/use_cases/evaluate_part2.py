"""
Part 2 评测用例
编排完整的 Part 2 评测流程：提交任务、消费处理、保存结果
"""
import uuid
import os
from urllib.parse import urlparse
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.adapters.repositories.models import TestModel, TestItemModel
from src.adapters.gateways.qwen_client import QwenOmniGateway, Part2EvaluationResult
from src.infrastructure.queue_service import Part2Task, enqueue_part2_task


@dataclass
class SubmitPart2Request:
    """提交 Part 2 评测请求"""
    test_id: int
    audio_url: str
    questions: list  # 12 道题目


@dataclass
class SubmitPart2Response:
    """提交 Part 2 响应"""
    success: bool
    task_id: Optional[str] = None
    message: str = ""


class SubmitPart2UseCase:
    """
    提交 Part 2 评测任务（异步入队）
    
    流程:
    1. 验证测评状态（必须是 part1_done）
    2. 创建任务并入队
    3. 更新测评状态为 processing
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def execute(self, request: SubmitPart2Request) -> SubmitPart2Response:
        """
        提交 Part 2 评测任务
        
        Args:
            request: SubmitPart2Request
            
        Returns:
            SubmitPart2Response 包含任务 ID
        """
        # 1. 查找并验证测评
        stmt = select(TestModel).where(TestModel.id == request.test_id)
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()
        
        if not test:
            return SubmitPart2Response(
                success=False,
                message="测评记录不存在"
            )
        
        if test.status != "part1_done":
            return SubmitPart2Response(
                success=False,
                message=f"无法提交 Part 2：当前状态为 {test.status}"
            )
        
        # 2. 创建任务
        task_id = str(uuid.uuid4())[:8]
        task = Part2Task(
            task_id=task_id,
            test_id=request.test_id,
            audio_url=request.audio_url,
            questions=request.questions
        )
        
        # 3. 入队
        try:
            await enqueue_part2_task(task)
        except Exception as e:
            logger.exception(f"Part 2 任务入队失败: {e}")
            return SubmitPart2Response(
                success=False,
                message=f"任务入队失败: {str(e)}"
            )
        
        # 4. 更新状态
        test.status = "processing"
        test.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        logger.info(f"Part 2 任务已入队: task_id={task_id}, test_id={request.test_id}")
        
        return SubmitPart2Response(
            success=True,
            task_id=task_id,
            message="评测任务已提交，请稍后查询结果"
        )


class ProcessPart2TaskUseCase:
    """
    处理 Part 2 评测任务（消费者调用）
    
    流程:
    1. 下载音频
    2. 调用 Qwen API
    3. 解析评分结果
    4. 保存到数据库
    5. 更新测评状态
    """
    
    def __init__(self, db: AsyncSession, qwen_gateway: QwenOmniGateway):
        self.db = db
        self.qwen = qwen_gateway
    
    async def execute(self, task: Part2Task) -> bool:
        """
        处理 Part 2 评测任务
        
        Args:
            task: Part2Task 任务对象
            
        Returns:
            bool - True 表示成功
        """
        # 1. 查找测评
        stmt = select(TestModel).where(TestModel.id == task.test_id)
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()
        
        if not test:
            logger.error(f"测评不存在: {task.test_id}")
            return False
        
        try:
            # 2. 下载音频
            import httpx
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(task.audio_url, timeout=60)
                    response.raise_for_status()
                    audio_data = response.content
            except Exception as e:
                logger.exception(f"下载音频失败: {e}")
                test.status = "failed"
                test.failure_reason = f"下载音频失败: {str(e)}"
                await self.db.commit()
                return False
            
            # 3. 调用 Qwen API
            # 根据 URL 判断格式 (Handle presigned URLs with query params)
            parsed_url = urlparse(task.audio_url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1].lower()
            
            audio_format = "mp3"  # Default
            if ext == ".wav":
                audio_format = "wav"
            elif ext == ".m4a":
                audio_format = "m4a"
            elif ext == ".pcm":
                 audio_format = "pcm"
            
            qwen_result = await self.qwen.evaluate_part2(
                audio_data=audio_data,
                audio_format=audio_format,
                questions=task.questions
            )
            
            # 4. 处理结果
            if not qwen_result.success:
                test.status = "failed"
                test.failure_reason = qwen_result.error
                test.retry_count += 1
                await self.db.commit()
                return False
            
            # 5. 保存逐题评分
            for item_data in qwen_result.items:
                item = TestItemModel(
                    test_id=task.test_id,
                    question_no=item_data.get("no"),
                    score=item_data.get("score_0_2", 0),
                    feedback=item_data.get("reason", ""),
                    evidence=item_data.get("evidence", "")
                )
                self.db.add(item)
            
            # 6. 更新测评记录
            test.part2_score = qwen_result.total_score
            test.part2_transcript = qwen_result.transcript
            test.part2_audio_url = task.audio_url  # 保存音频 URL
            test.part2_raw_result = qwen_result.to_dict()  # 保存完整结果 (含 5 维度分数)
            
            # 计算总分 (Part 1 和 Part 2 都是 0-100 分，取平均)
            p1_score = float(test.part1_score or 0)
            p2_score = float(qwen_result.total_score or 0)
            test.total_score = (p1_score + p2_score) / 2
            
            test.star_level = self._calculate_star_level(test.total_score)
            test.status = "completed"
            test.completed_at = datetime.now(timezone.utc)
            test.updated_at = datetime.now(timezone.utc)
            
            # Calculate Cost for Part 2
            if qwen_result.usage:
                usage = qwen_result.usage
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                prompt_details = usage.get("prompt_tokens_details", {})
                audio_tokens = prompt_details.get("audio_tokens", 0)
                text_tokens = prompt_details.get("text_tokens", 0)
                
                if audio_tokens == 0 and text_tokens == 0 and prompt_tokens > 0:
                    audio_tokens = prompt_tokens # Fallback assumption
                
                cost = (
                    (text_tokens * 0.0018 / 1000) +
                    (audio_tokens * 0.0158 / 1000) +
                    (completion_tokens * 0.0127 / 1000)
                )
                
                test.cost = float(test.cost or 0) + cost
                
                # Update tokens_used with structured data
                current_usage = dict(test.tokens_used or {})
                if not isinstance(current_usage, dict):
                    current_usage = {}
                    
                current_usage["part2"] = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "audio_tokens": audio_tokens,
                    "text_tokens": text_tokens,
                    "total_tokens": usage.get("total_tokens", 0),
                    "cost": float(f"{cost:.6f}")
                }
                # Calculate total cost in JSON
                total_cost = (current_usage.get("part1", {}).get("cost", 0) + cost)
                current_usage["total_cost"] = float(f"{total_cost:.6f}")
                
                test.tokens_used = current_usage
                
                logger.info(f"Part 2 Cost: {cost:.4f} RMB, Usage: {current_usage['part2']}")
            
            await self.db.commit()
            
            logger.info(
                f"Part 2 评测完成: test_id={task.test_id}, "
                f"part2_score={qwen_result.total_score}, "
                f"total_score={test.total_score}"
            )
            
            return True
            
        except Exception as e:
            # 全局异常捕获：确保任何异常都记录 failure_reason
            logger.exception(f"Part 2 处理异常: {e}")
            try:
                test.status = "failed"
                test.failure_reason = f"处理异常: {str(e)}"
                test.part2_audio_url = task.audio_url  # 保存音频 URL 以便排查
                test.retry_count = (test.retry_count or 0) + 1
                
                # 尝试保存已计算的评分数据（如果 Qwen 返回成功但后续处理失败）
                # 检查 qwen_result 是否存在（通过检查 locals）
                if 'qwen_result' in dir() and qwen_result and qwen_result.success:
                    test.part2_score = qwen_result.total_score
                    test.part2_transcript = qwen_result.transcript
                    test.part2_raw_result = qwen_result.raw_response
                    logger.info(f"异常恢复：保存了 Part 2 评分结果 score={qwen_result.total_score}")
                
                await self.db.commit()
            except Exception as commit_error:
                logger.error(f"保存失败原因时出错: {commit_error}")
            return False
    
    def _calculate_star_level(self, total_score: float) -> int:
        """根据总分 (0-100) 计算星级 (1-5)"""
        if total_score >= 90:
            return 5
        elif total_score >= 80:
            return 4
        elif total_score >= 60:
            return 3
        elif total_score >= 40:
            return 2
        else:
            return 1