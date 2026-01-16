"""
Part 2 评测用例
编排完整的 Part 2 评测流程：提交任务、消费处理、保存结果
"""
import uuid
import os
from urllib.parse import urlparse
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.infrastructure.timezone import now as china_now

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
        
        # 允许的状态：part1_done（Part 1 已完成）或 part1_processing（Part 1 处理中，Part 2 可以先入队）
        allowed_statuses = ["part1_done", "part1_processing"]
        if test.status not in allowed_statuses:
            # 状态不允许时，仍保存 OSS 链接
            if request.audio_url and not test.part2_audio_url:
                test.part2_audio_url = request.audio_url
                test.updated_at = china_now()
                await self.db.commit()
                logger.info(f"Part 2 状态检查失败，但已保存音频链接: {request.audio_url}")
            return SubmitPart2Response(
                success=False,
                message=f"无法提交 Part 2：当前状态为 {test.status}"
            )
        
        # 2. 保存音频链接
        if request.audio_url:
            test.part2_audio_url = request.audio_url
        
        # 3. 创建任务
        task_id = str(uuid.uuid4())[:8]
        task = Part2Task(
            task_id=task_id,
            test_id=request.test_id,
            audio_url=request.audio_url,
            questions=request.questions
        )
        
        # 4. 入队
        try:
            await enqueue_part2_task(task)
        except Exception as e:
            logger.exception(f"Part 2 任务入队失败: {e}")
            return SubmitPart2Response(
                success=False,
                message=f"任务入队失败: {str(e)}"
            )
        
        # 5. 更新状态
        # 如果 Part 1 已完成，设为 processing；如果 Part 1 还在处理，保持 part1_processing
        if test.status == "part1_done":
            test.status = "processing"
        # 如果是 part1_processing，状态不变，Worker 会等待 Part 1 完成
        test.updated_at = china_now()
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
        import asyncio
        
        # 1. 查找测评
        stmt = select(TestModel).where(TestModel.id == task.test_id)
        result = await self.db.execute(stmt)
        test = result.scalar_one_or_none()
        
        if not test:
            logger.error(f"测评不存在: {task.test_id}")
            return False
        
        # 等待 Part 1 完成（如果还在处理中）
        max_wait_seconds = 120  # 最多等待 2 分钟
        wait_interval = 5  # 每 5 秒检查一次
        waited = 0
        
        while test.status == "part1_processing" and waited < max_wait_seconds:
            logger.info(f"Part 2 等待 Part 1 完成... (已等待 {waited}s)")
            await asyncio.sleep(wait_interval)
            waited += wait_interval
            
            # 重新查询状态
            await self.db.refresh(test)
        
        # 如果等待超时，Part 1 仍未完成
        if test.status == "part1_processing":
            logger.warning(f"Part 2 等待 Part 1 超时，test_id={task.test_id}")
            test.failure_reason = "Part 1 处理超时，Part 2 无法继续"[:250]
            test.status = "failed"
            await self.db.commit()
            return False
        
        # 如果 Part 1 失败了
        if test.status == "failed":
            logger.warning(f"Part 1 已失败，跳过 Part 2 处理，test_id={task.test_id}")
            return False
        
        # Part 1 完成，更新状态为 processing
        if test.status == "part1_done":
            test.status = "processing"
            test.updated_at = china_now()
            await self.db.commit()
            logger.info(f"Part 2 开始处理，test_id={task.test_id}")
        
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
                test.failure_reason = f"下载音频失败: {str(e)}"[:250]
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
            
            # 4. 记录 Token 消耗 (无论成功或失败，只要有 usage 就记录)
            if qwen_result.usage:
                usage = qwen_result.usage
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                prompt_details = usage.get("prompt_tokens_details", {})
                audio_tokens = prompt_details.get("audio_tokens", 0)
                text_tokens = prompt_details.get("text_tokens", 0)
                
                if audio_tokens == 0 and text_tokens == 0 and prompt_tokens > 0:
                    audio_tokens = prompt_tokens  # Fallback assumption
                
                cost = (
                    (text_tokens * 0.0018 / 1000) +
                    (audio_tokens * 0.0158 / 1000) +
                    (completion_tokens * 0.0127 / 1000)
                )
                
                # 累加到总 cost
                test.cost = float(test.cost or 0) + cost
                
                # 更新 tokens_used，保留历史记录
                current_usage = dict(test.tokens_used or {})
                if not isinstance(current_usage, dict):
                    current_usage = {}
                    
                # 记录本次调用的详情
                attempt_record = {
                    "attempt": (test.retry_count or 0) + 1,
                    "success": qwen_result.success,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "audio_tokens": audio_tokens,
                    "text_tokens": text_tokens,
                    "total_tokens": usage.get("total_tokens", 0),
                    "cost": float(f"{cost:.6f}"),
                    "timestamp": china_now().isoformat()
                }
                
                # 追加到 part2_history 列表
                if "part2_history" not in current_usage:
                    current_usage["part2_history"] = []
                current_usage["part2_history"].append(attempt_record)
                
                # 保留最新一次的快照 (兼容旧代码)
                current_usage["part2"] = {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "audio_tokens": audio_tokens,
                    "text_tokens": text_tokens,
                    "total_tokens": usage.get("total_tokens", 0),
                    "cost": float(f"{cost:.6f}")
                }
                
                # 计算总 cost（遍历所有历史记录）
                total_cost = (
                    sum(h.get("cost", 0) for h in current_usage.get("part1_history", [])) +
                    sum(h.get("cost", 0) for h in current_usage.get("part2_history", [])) +
                    sum(h.get("cost", 0) for h in current_usage.get("summary_analysis_history", [])) +
                    sum(h.get("cost", 0) for h in current_usage.get("interpretation_history", []))
                )
                current_usage["total_cost"] = float(f"{total_cost:.6f}")
                
                test.tokens_used = current_usage
                
                logger.info(
                    f"Part 2 API 调用: success={qwen_result.success}, "
                    f"cost={cost:.4f} RMB, attempt={attempt_record['attempt']}"
                )
            
            # 5. 处理失败情况
            if not qwen_result.success:
                test.status = "failed"
                test.failure_reason = (qwen_result.error or "未知错误")[:250]
                test.retry_count = (test.retry_count or 0) + 1
                await self.db.commit()
                return False
            
            # 6. 保存逐题评分
            # 模型返回: {"no": 1, "transcript": "回答文本", "score": "S/A/B", "feedback": "评价"}
            for item_data in qwen_result.items:
                # 转换 S/A/B 为数值: S=2, A=1, B=0
                score_str = str(item_data.get("score", "A")).upper()
                score_map = {"S": 2, "A": 1, "B": 0}
                score_num = score_map.get(score_str, 1)  # 默认 A=1
                
                item = TestItemModel(
                    test_id=task.test_id,
                    question_no=item_data.get("no"),
                    score=score_num,
                    feedback=item_data.get("feedback", ""),  # 评价反馈
                    evidence=item_data.get("transcript", "")  # 学生回答转写
                )
                self.db.add(item)
            
            # 7. 更新测评记录
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
            test.completed_at = china_now()
            test.updated_at = china_now()
            
            await self.db.commit()
            
            logger.info(
                f"Part 2 评测完成: test_id={task.test_id}, "
                f"part2_score={qwen_result.total_score}, "
                f"total_score={test.total_score}"
            )
            
            # 8. 自动生成测评汇总分析 (给家长端 H5 用)
            await self._generate_summary_analysis(test)
            
            return True
            
        except Exception as e:
            # 全局异常捕获：确保任何异常都记录 failure_reason
            logger.exception(f"Part 2 处理异常: {e}")
            try:
                test.status = "failed"
                test.failure_reason = f"处理异常: {str(e)}"[:250]
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
    
    async def _generate_summary_analysis(self, test) -> None:
        """
        生成测评汇总分析 (给家长端 H5 用)
        
        在 Part 2 评测完成后自动调用，不阻塞主流程
        支持最多 3 次重试，失败后使用规则生成 fallback
        """
        import json
        from src.adapters.repositories.models import StudentProfileModel
        from sqlalchemy import select
        
        MAX_SUMMARY_RETRIES = 3
        
        try:
            # 获取学生名称
            stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == test.student_id)
            result = await self.db.execute(stmt)
            student_profile = result.scalar_one_or_none()
            student_name = student_profile.student_name if student_profile else "学生"
            
            # 构建雷达图分数 (从 Part1 和 Part2 raw result 中提取)
            part1_raw = test.part1_raw_result or {}
            part2_raw = test.part2_raw_result or {}
            
            radar_scores = {
                "fluency": (part1_raw.get("fluency_score", 0) * 0.4 + part2_raw.get("fluency_score", 0) * 0.6),
                "pronunciation": (part1_raw.get("pronunciation_score", 0) * 0.4 + part2_raw.get("pronunciation_score", 0) * 0.6),
                "confidence": part2_raw.get("confidence_score", 0),
                "vocabulary": (part1_raw.get("accuracy_score", 0) * 0.3 + part2_raw.get("vocabulary_score", 0) * 0.7),
                "sentence": (part1_raw.get("integrity_score", 0) * 0.2 + part2_raw.get("sentence_score", 0) * 0.8),
            }
            
            # 提取 Part1 词汇详情 (用于具体举例)
            # 数据来源: part1_raw["details"] = [{content, score, issue}, ...]
            part1_words = []
            if part1_raw.get("details"):
                for word in part1_raw["details"]:
                    score = word.get("score", 0)
                    part1_words.append({
                        "word": word.get("content", ""),
                        "score": score,
                        "status": "perfect" if score >= 80 else ("unclear" if score >= 50 else "failed"),
                        "issue": word.get("issue")  # 具体问题描述，如 "尾音发音不清"
                    })
            
            # 提取 Part2 问答详情 (用于具体举例)
            # 数据来源: part2_raw["items"] = [{no, transcript, score, feedback}, ...]
            part2_items = []
            if part2_raw.get("items"):
                for item in part2_raw["items"]:
                    part2_items.append({
                        "no": item.get("no"),
                        "score": item.get("score", "A"),  # S/A/B
                        "transcript": item.get("transcript", "")[:100],  # 学生实际回答
                        "feedback": item.get("feedback", "")  # 模型对该题的反馈
                    })
            
            # 协程内循环重试（最多 3 次）
            summary_result = None
            for attempt in range(1, MAX_SUMMARY_RETRIES + 1):
                # 调用 qwen-plus 生成汇总分析
                summary_result = await self.qwen.generate_summary_analysis(
                    student_name=student_name,
                    level=test.level,
                    total_score=float(test.total_score or 0),
                    star_level=test.star_level or 1,
                    radar_scores=radar_scores,
                    part1_score=float(test.part1_score or 0),
                    part2_score=float(test.part2_score or 0),
                    part1_words=part1_words,
                    part2_items=part2_items,
                    part1_suggestion=part1_raw.get("part1_overall_suggestion", []),
                    part2_suggestion=part2_raw.get("part2_overall_suggestion", [])
                )
                
                # 记录本次调用费用（无论成功或失败，只要有 usage）
                if summary_result.usage:
                    self._record_summary_analysis_cost(test, summary_result, attempt)
                
                # 成功则退出循环
                if summary_result.success:
                    break
                
                logger.warning(f"测评汇总分析第 {attempt} 次失败: {summary_result.error}")
            
            # 存储结果
            if summary_result and summary_result.success:
                test.summary_highlights = json.dumps(summary_result.highlights, ensure_ascii=False)
                test.summary_weaknesses = json.dumps(summary_result.weaknesses, ensure_ascii=False)
                test.summary_weekly_plan = json.dumps(summary_result.weekly_plan, ensure_ascii=False)
                # 存储 AI 生成的五维评语（用于家长端雷达图）
                if summary_result.dimension_feedback:
                    test.summary_dimension_feedback = summary_result.dimension_feedback
                test.summary_generated_at = china_now()
                
                await self.db.commit()
                logger.info(f"测评汇总分析生成成功: test_id={test.id}, has_dimension_feedback={summary_result.dimension_feedback is not None}")
            else:
                logger.warning(f"测评汇总分析重试 {MAX_SUMMARY_RETRIES} 次均失败，使用规则生成 fallback")
                # 失败时使用规则生成默认建议
                self._generate_fallback_summary(test, radar_scores)
                await self.db.commit()
                
        except Exception as e:
            logger.exception(f"生成测评汇总分析时出错: {e}")
            # 不影响主流程，即使失败也不抛出异常
    
    def _record_summary_analysis_cost(self, test, summary_result, attempt: int) -> None:
        """记录测评汇总分析的费用到历史记录"""
        usage = summary_result.usage
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # qwen-plus 定价: 输入 ¥0.0008/千tokens, 输出 ¥0.002/千tokens
        cost = (
            (prompt_tokens * 0.0008 / 1000) +
            (completion_tokens * 0.002 / 1000)
        )
        
        # 累加到总 cost
        test.cost = float(test.cost or 0) + cost
        
        # 更新 tokens_used
        current_usage = dict(test.tokens_used or {})
        if not isinstance(current_usage, dict):
            current_usage = {}
        
        # 追加到 summary_analysis_history 列表
        if "summary_analysis_history" not in current_usage:
            current_usage["summary_analysis_history"] = []
        
        attempt_record = {
            "attempt": attempt,
            "success": summary_result.success,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": usage.get("total_tokens", 0),
            "cost": float(f"{cost:.6f}"),
            "model": "qwen-plus",
            "timestamp": china_now().isoformat()
        }
        if not summary_result.success and summary_result.error:
            attempt_record["error"] = str(summary_result.error)[:200]
        
        current_usage["summary_analysis_history"].append(attempt_record)
        
        # 重新计算总 cost（遍历所有历史记录）
        total_cost = (
            sum(h.get("cost", 0) for h in current_usage.get("part1_history", [])) +
            sum(h.get("cost", 0) for h in current_usage.get("part2_history", [])) +
            sum(h.get("cost", 0) for h in current_usage.get("summary_analysis_history", [])) +
            sum(h.get("cost", 0) for h in current_usage.get("interpretation_history", []))
        )
        current_usage["total_cost"] = float(f"{total_cost:.6f}")
        
        test.tokens_used = current_usage
        
        logger.info(
            f"测评汇总分析 API 调用: attempt={attempt}, success={summary_result.success}, "
            f"cost={cost:.4f} RMB"
        )
    
    def _generate_fallback_summary(self, test, radar_scores: dict) -> None:
        """使用规则生成默认的测评汇总分析（fallback）"""
        import json
        
        default_highlights = []
        default_weaknesses = []
        
        # 新阈值：≥90 杰出, 70-89 优秀, 60-69 良好, <60 待提升
        for dim_name, score in radar_scores.items():
            dim_cn = {"fluency": "流利度", "pronunciation": "发音", "confidence": "自信度", 
                      "vocabulary": "词汇", "sentence": "整句输出"}.get(dim_name, dim_name)
            if score >= 70:
                default_highlights.append(f"{dim_cn}表现优秀")
            elif score < 60:
                default_weaknesses.append(f"{dim_cn}有提升空间")
        
        test.summary_highlights = json.dumps(default_highlights or ["本次测评表现稳定"], ensure_ascii=False)
        test.summary_weaknesses = json.dumps(default_weaknesses or ["暂无明显短板"], ensure_ascii=False)
        test.summary_weekly_plan = json.dumps([
            "每天跟读 10 分钟标准音频",
            "多用完整句子回答问题",
            "保持自信，大声开口练习"
        ], ensure_ascii=False)
        # 失败时不设置 dimension_feedback，将使用规则模板
        test.summary_generated_at = china_now()