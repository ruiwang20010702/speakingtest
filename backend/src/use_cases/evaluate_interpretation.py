"""
报告解读异步处理模块
处理异步队列中的报告解读任务
"""
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.queue_service import InterpretationTask
from src.infrastructure.database import async_session_factory
from src.infrastructure.timezone import now as china_now
from src.adapters.repositories.models import TestModel
from src.adapters.gateways.qwen_client import QwenOmniGateway


# 最大重试次数
MAX_RETRIES = 3


def _record_interpretation_cost(test, interpretation, attempt: int, success: bool = True, error: str = None) -> None:
    """
    记录报告解读的费用到历史记录
    
    Args:
        test: TestModel 对象
        interpretation: ReportInterpretation 对象
        attempt: 当前尝试次数
        success: 是否成功
        error: 错误信息（如果失败）
    """
    if not interpretation.usage:
        return
    
    usage = interpretation.usage
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
    
    # 追加到 interpretation_history 列表
    if "interpretation_history" not in current_usage:
        current_usage["interpretation_history"] = []
    
    attempt_record = {
        "attempt": attempt,
        "success": success,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": usage.get("total_tokens", 0),
        "cost": float(f"{cost:.6f}"),
        "model": "qwen-plus",
        "timestamp": china_now().isoformat()
    }
    if not success and error:
        attempt_record["error"] = str(error)[:200]
    
    current_usage["interpretation_history"].append(attempt_record)
    
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
        f"报告解读 API 调用: attempt={attempt}, success={success}, "
        f"cost={cost:.4f} RMB"
    )


async def process_interpretation_task(task: InterpretationTask) -> bool:
    """
    处理报告解读任务
    
    Args:
        task: InterpretationTask 任务对象
        
    Returns:
        bool: 是否成功
    """
    logger.info(f"开始处理报告解读任务: task_id={task.task_id}, test_id={task.test_id}")
    
    async with async_session_factory() as db:
        try:
            # 获取测试记录
            stmt = select(TestModel).where(TestModel.id == task.test_id)
            result = await db.execute(stmt)
            test = result.scalar_one_or_none()
            
            if not test:
                logger.error(f"测试记录不存在: test_id={task.test_id}")
                return True  # 返回 True 避免无限重试
            
            # 检查重试次数
            retry_count = test.interpretation_retry_count or 0
            if retry_count >= MAX_RETRIES:
                logger.warning(f"报告解读重试次数超限: test_id={task.test_id}, retries={retry_count}")
                test.interpretation_status = "failed"
                await db.commit()
                return True  # 不再重试
            
            # 调用 Qwen API 生成解读
            from src.adapters.controllers.report_controller import ReportInterpretationService
            qwen_gateway = QwenOmniGateway()
            service = ReportInterpretationService(qwen_gateway)
            
            interpretation = await service.generate(
                student_name=task.student_name,
                level=task.level,
                total_score=task.total_score,
                part1_score=task.part1_score,
                part2_score=task.part2_score,
                star_level=task.star_level,
                part1_details=task.part1_details,
                part2_items=task.part2_items,
                radar_data=task.radar_data if task.radar_data else None,
            )
            
            # 计算当前尝试次数（retry_count + 1）
            current_attempt = retry_count + 1
            
            # 记录费用到历史记录
            # ReportInterpretationService.generate() 成功返回表示生成成功
            # （内部已处理了 LLM 失败时的 fallback）
            _record_interpretation_cost(test, interpretation, current_attempt, success=True)
            
            # 成功：保存结果
            test.interpretation_pages = interpretation.pages_to_json()
            test.interpretation_parent_script = interpretation.full_script
            test.interpretation_generated_at = china_now()
            test.interpretation_status = "completed"
            
            await db.commit()
            
            logger.info(f"报告解读生成成功: test_id={task.test_id}")
            return True
            
        except Exception as e:
            logger.exception(f"报告解读处理异常: test_id={task.test_id}, error={e}")
            
            # 更新重试次数（针对未预期的异常）
            try:
                stmt = select(TestModel).where(TestModel.id == task.test_id)
                result = await db.execute(stmt)
                test = result.scalar_one_or_none()
                
                if test:
                    # 只有在异常处理时才增加重试次数（正常失败已在上面处理）
                    current_retry = test.interpretation_retry_count or 0
                    if current_retry < MAX_RETRIES:
                        test.interpretation_retry_count = current_retry + 1
                    if test.interpretation_retry_count >= MAX_RETRIES:
                        test.interpretation_status = "failed"
                        logger.warning(f"报告解读达到最大重试次数: test_id={task.test_id}")
                    await db.commit()
            except Exception as db_error:
                logger.error(f"更新重试次数失败: {db_error}")
            
            # 抛出异常触发 NACK 重试（如果未达到最大次数）
            raise
