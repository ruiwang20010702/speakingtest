"""
Qwen-Omni 语音评测网关
用于 Part 2 问答评测，基于 /async-python-patterns 和 /prompt-engineering-patterns
"""
import asyncio
import base64
import json
from typing import List, Optional, AsyncIterator
from dataclasses import dataclass

import httpx
from loguru import logger

from src.infrastructure.config import get_settings
from src.infrastructure.rate_limiter import RateLimiter

settings = get_settings()


# ============================================
# Part 2 评分 Prompt 模板
# 基于 /prompt-engineering-patterns - Progressive Disclosure + Structured Output
# ============================================

PART2_SYSTEM_PROMPT = """你是一位专业的英语口语评测老师。你的任务是对学生 Part2（12 题连续作答）的整段录音进行评测。

## 评分标准
- 2 分：完整正确回答，语法/发音基本正确
- 1 分：部分正确，或有明显语法/发音问题
- 0 分：未作答、完全错误、或无法辨识

## 输出要求
1. 严格输出 JSON 格式（不要输出 markdown）
2. 必须包含 12 道题的评分（题号 1-12，不允许缺题）
3. 每题给出简短理由和证据

## JSON 结构
{
  "transcript_full": "完整转写文本",
  "items": [
    {"no": 1, "score_0_2": 0, "reason": "评分理由", "evidence": "转写中的证据片段", "suggestion": "改进建议"}
  ],
  "overall_suggestion": ["总体建议1", "总体建议2"]
}"""


def build_part2_user_prompt(questions: List[dict]) -> str:
    """
    构建 Part 2 评测的用户 Prompt
    
    Args:
        questions: 题目列表，每个包含 no, question, reference_answer
        
    Returns:
        格式化的用户 Prompt
    """
    questions_text = "\n".join([
        f"题目 {q['no']}: {q['question']}\n参考答案: {q.get('reference_answer', '无')}"
        for q in questions
    ])
    
    return f"""请评测这段学生录音。

## 题目列表
{questions_text}

## 要求
1. 输出整段逐字转写（保留原话，不要润色）
2. 对 1-12 每题给出 0/1/2 分
3. 每题给出评分理由和转写证据
4. 给出 1-3 条总体改进建议

严格只输出 JSON，不要有其他内容。"""


@dataclass
class Part2EvaluationResult:
    """Part 2 评测结果"""
    success: bool
    transcript: Optional[str] = None
    items: Optional[List[dict]] = None  # 12 题评分
    overall_suggestion: Optional[List[str]] = None
    total_score: Optional[int] = None  # 0-24
    error: Optional[str] = None
    raw_response: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "transcript": self.transcript,
            "items": self.items,
            "overall_suggestion": self.overall_suggestion,
            "total_score": self.total_score,
            "error": self.error
        }


class QwenOmniGateway:
    """
    Qwen-Omni 流式 API 网关
    
    使用 /async-python-patterns 实现流式 HTTP 请求
    集成 Semaphore 限流以遵守 60 RPM 限制
    """
    
    def __init__(self):
        self.api_key = settings.QWEN_API_KEY
        self.base_url = settings.QWEN_BASE_URL
        self.model = settings.QWEN_MODEL
        self.semaphore = RateLimiter.get_qwen_limiter()
    
    async def evaluate_part2(
        self,
        audio_data: bytes,
        audio_format: str,  # mp3, wav, etc.
        questions: List[dict]
    ) -> Part2EvaluationResult:
        """
        评测 Part 2 录音
        
        Args:
            audio_data: 音频二进制数据
            audio_format: 音频格式 (mp3, wav, m4a)
            questions: 12 道题目列表
            
        Returns:
            Part2EvaluationResult 包含转写和逐题评分
        """
        # 构建 data URL
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        mime_type = f"audio/{audio_format}"
        if audio_format == "mp3":
            mime_type = "audio/mpeg"
        data_url = f"data:{mime_type};base64,{audio_base64}"
        
        # 构建请求体
        request_body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": PART2_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": data_url,
                                "format": audio_format
                            }
                        },
                        {
                            "type": "text",
                            "text": build_part2_user_prompt(questions)
                        }
                    ]
                }
            ],
            "modalities": ["text"],
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        
        # 使用 Semaphore 限流
        async with self.semaphore:
            logger.info(f"开始 Qwen Part 2 评测，音频大小: {len(audio_data)} bytes")
            
            try:
                full_response = await self._stream_request(request_body)
                result = self._parse_response(full_response)
                
                # 限速：每次请求后等待 1 秒（60 RPM）
                await asyncio.sleep(1.0)
                
                return result
                
            except Exception as e:
                logger.exception(f"Qwen API 调用失败: {e}")
                return Part2EvaluationResult(
                    success=False,
                    error=str(e)
                )
    
    async def _stream_request(self, request_body: dict) -> str:
        """
        发送流式 HTTP 请求并收集完整响应
        基于 /async-python-patterns Pattern 7: Async Iterators
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        full_content = ""
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                json=request_body,
                headers=headers
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]  # 移除 "data: " 前缀
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data_str)
                        if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                            full_content += chunk["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue
        
        logger.debug(f"Qwen 响应长度: {len(full_content)} 字符")
        return full_content
    
    def _parse_response(self, response_text: str) -> Part2EvaluationResult:
        """
        解析 Qwen 返回的 JSON 响应
        基于 /prompt-engineering-patterns - Error Recovery
        """
        try:
            # 尝试直接解析 JSON
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    return Part2EvaluationResult(
                        success=False,
                        error="无法解析 AI 返回的 JSON",
                        raw_response=response_text
                    )
            else:
                return Part2EvaluationResult(
                    success=False,
                    error="AI 返回格式错误",
                    raw_response=response_text
                )
        
        # 验证必要字段
        items = data.get("items", [])
        if len(items) != 12:
            logger.warning(f"Qwen 返回题目数量不正确: {len(items)}/12")
            # 尝试补全缺失的题目
            existing_nos = {item.get("no") for item in items}
            for i in range(1, 13):
                if i not in existing_nos:
                    items.append({
                        "no": i,
                        "score_0_2": 0,
                        "reason": "未能识别该题回答",
                        "evidence": "",
                        "suggestion": ""
                    })
            items.sort(key=lambda x: x.get("no", 0))
        
        # 计算总分
        total_score = sum(item.get("score_0_2", 0) for item in items)
        
        return Part2EvaluationResult(
            success=True,
            transcript=data.get("transcript_full", ""),
            items=items,
            overall_suggestion=data.get("overall_suggestion", []),
            total_score=total_score,
            raw_response=response_text
        )
