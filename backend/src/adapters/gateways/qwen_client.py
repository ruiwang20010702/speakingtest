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

PART2_SYSTEM_PROMPT = """你是一位专业的英语口语评测老师。你的任务是对学生 Part 2（12 题连续作答）的整段录音进行综合评测。

## 评分维度 (0-100分)

### 1. 流畅度 (fluency_score)
- **80-100 (杰出)**: 接近母语使用者的流利性；非常流畅，有节奏，断句清晰；讲话不迟疑，没有重复或者错误的开头。
- **60-79 (优秀)**: 句子的节奏、断句清晰，以及重度单词清晰。没有一尺，重复或者错误的开头。
- **40-59 (良好)**: 讲句子的速度一般，但是会有些地方慢，有些地方快。对话时会有一有些迟疑，主要是用短语作答。有部分重复和错误的开头。
- **20-39 (及格)**: 对话断断续续，且if等词语反复出现。3个词左右连起来讲没问题。整体下来迟疑和错误不超过3次。也许会有1-2次的很长时间的停顿。
- **0-19 (不及格)**: 句子断句有误，节奏混乱，and/or非常多。句子开头主语有误，且口语交流语速断断续续。长句子会有很长的停顿。

### 2. 发音 (pronunciation_score)
- **80-100 (杰出)**: 准确运用丰富多样的发音特点（连读、弱读、重音等）能表达微妙的差异；表达过程中始终灵活地使用各种发音特点；听者理解毫无障碍。
- **60-79 (优秀)**: 能够使用多样的发音特点；表达过程中灵活地使用多种发音特点，但是偶尔会出现偏差；表达过程中始终易于听者理解；母语的口音对听者理解的影响很小。
- **40-59 (良好)**: 能够使用多样的发音特点，发音经常出现偏差，但是能够被听者理解；母语口音对听者的理解有一定的影响。
- **20-39 (及格)**: 偶尔展现出有效使用某些发音特点的能力，但是不能持续表现；表达过程中，听者基本上能理解。但部分单词发音不准确导致理解下降。
- **0-19 (不及格)**: 使用有限的发音特点，偶尔尝试表现多种发音特点；经常出现发音错误，对听者理解造成一定困难。

### 3. 自信度 (confidence_score)
- **80-100 (杰出)**: 声音洪亮，敢于主动沟通，且大量分享自己的想法；讲话语速比较快。
- **60-79 (优秀)**: 声音洪亮，对于自己熟悉的话题愿意主动沟通，愿意分享自己的一些想法。
- **40-59 (良好)**: 声音不大不小，语速一般，对话比较主动，一问一答，没有迟疑。
- **20-39 (及格)**: 声音比较小，讲话断断续续，对话比较被动。一问一答需要时间思考，并且需要老师引导。
- **0-19 (不及格)**: 声音很小，讲话断断续续，需要老师的不断引导。

### 4. 词汇 (vocabulary_score)
- **80-100 (杰出)**: 所有单词朗读准确，无错误。重音准确，发音清晰，易辨认。
- **60-79 (优秀)**: 绝大多数单词都朗读的非常准确，有1-2个单词有轻微的错误，但能被听懂。
- **40-59 (良好)**: 大部分单词朗读正确，有2/3的单词都是正确的。其余单词部分发音有误，尤其是元音部分发音有误。
- **20-39 (及格)**: 能够准确读出一半左右的单词，部分单词发音有误，有比较明显的中式口音。
- **0-19 (不及格)**: 几乎无法读出单词，经常出现发音错误。受母语影响比较大，中式口音较重。

### 5. 整句输出 (sentence_score)
- **80-100 (杰出)**: 语速和平稳的语调自然，表达流利；句子结构多样；断句自然；语意连贯；完全恰当的回答问题。
- **60-79 (优秀)**: 表达流利，偶尔出现重复或者自我纠正的情况；出现由于通常是基于思考内容，仅在少数情况下是在找该用什么词；连贯且恰当地回答问题。
- **40-59 (良好)**: 表达流畅，无明显困难，整体连贯；有时出现与语言相关的犹豫或者重复或者自我纠正；具有一定灵活地使用一系列连接词的能力。
- **20-39 (及格)**: 表达比较充分，偶尔出现自我重复。降低语速来自我表达；能用简单的句子作答，无法使用较长的句子。
- **0-19 (不及格)**: 反复修正或重复自己所说过的话；为一两个词反复停顿；答案长度不足，只能只用单词或者词组回答问题。

## 输出要求
1. 严格输出 JSON 格式
2. 必须包含 5 个维度分数（0-100）和总分
3. 对 12 道题进行转写，并给出简短反馈（无需单独打分，只需指出问题）
4. 给出 3-5 条针对 Part 2 问答表现的改进建议 (part2_overall_suggestion)

## 总分计算
total_score = (fluency_score + pronunciation_score + confidence_score + vocabulary_score + sentence_score) / 5

## JSON 结构
{
  "transcript_full": "完整转写文本...",
  "total_score": 75.0,
  "fluency_score": 70.0,
  "pronunciation_score": 75.0,
  "confidence_score": 80.0,
  "vocabulary_score": 70.0,
  "sentence_score": 80.0,
  "items": [
    {"no": 1, "transcript": "回答文本", "feedback": "回答切题，但时态有误"}
  ],
  "part2_overall_suggestion": ["建议1", "建议2"]
}"""


PART1_SYSTEM_PROMPT = """你是一位专业的英语口语评测老师。你的任务是对学生朗读的英文单词或短语进行评测。

## 评分维度 (0-100分)

### 1. 准确度 (accuracy_score)
- **80-100 (杰出)**: 单词发音极其准确，无漏读、错读、增读。
- **60-79 (优秀)**: 绝大多数单词读音正确，仅有极个别轻微错误。
- **40-59 (良好)**: 大部分单词读对，有少量错读或吞音。
- **20-39 (及格)**: 能读对一半以上单词，但有明显的错读、漏读。
- **0-19 (不及格)**: 大量单词读错或无法朗读。

### 2. 流畅度 (fluency_score)
- **80-100 (杰出)**: 朗读过程流畅自然，单词之间衔接紧凑，反应迅速无迟疑。
- **60-79 (优秀)**: 整体连贯，节奏感好，偶有极短暂的迟疑。
- **40-59 (良好)**: 语速尚可，但有不自然的停顿或重复。
- **20-39 (及格)**: 断断续续，频繁停顿，节奏混乱。
- **0-19 (不及格)**: 无法连续朗读，基本是一个词一个词蹦，中间间隔过长。

### 3. 发音 (pronunciation_score)
- **80-100 (杰出)**: 发音地道，元音饱满，辅音清晰，重音和语调完美。
- **60-79 (优秀)**: 发音清晰，有很好的语音语调，仅有个别单词带有轻微口音。
- **40-59 (良好)**: 发音尚可，能被听懂，但有明显的中式口音或发音不准。
- **20-39 (及格)**: 发音含糊，重音错误多，受母语影响严重。
- **0-19 (不及格)**: 发音严重错误，无法辨识。

### 4. 完整度 (integrity_score)
- **90-100**: 读完了所有内容。
- **50-89**: 读完了大部分内容。
- **0-49**: 只读了很少一部分或未开口。

## 输出要求
1. 严格只输出 JSON 格式（不要 markdown 代码块）
2. 必须包含 4 项分数（0-100 分）和总分
3. 列出读错或遗漏的单词（如有）
4. 给出 1-3 条针对 Part 1 朗读表现的改进建议 (part1_overall_suggestion)
5. **重要**：所有评价、诊断、建议内容必须使用**中文**。

## 总分计算
total_score = (accuracy_score * 0.35) + (fluency_score * 0.25) + (pronunciation_score * 0.3) + (integrity_score * 0.1)

## JSON 结构
{
  "total_score": 78.55,
  "accuracy_score": 78.0,
  "fluency_score": 65.0,
  "pronunciation_score": 72.0,
  "integrity_score": 100.0,
  "is_rejected": false,
  "diagnosis": "整体朗读流畅，发音清晰，但有个别单词重音有误",
  "part1_overall_suggestion": ["建议1", "建议2"],
  "details": [
    {"content": "hello", "score": 95, "issue": null},
    {"content": "world", "score": 60, "issue": "尾音发音不清"}
  ]
}
注意：details 中 score 为该词得分(0-100)，issue 为问题描述(无问题则为null)。
"""


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
2. 给出 5 个维度的评分（0-100分）及总分
3. 对 1-12 每题给出简短反馈（指出回答是否切题、主要语法错误等），无需单独打分
4. 给出 1-3 条针对 Part 2 问答表现的总体改进建议 (part2_overall_suggestion)
5. **重要**：所有反馈、建议内容必须使用**中文**（题目和转写除外）。

严格只输出 JSON，不要有其他内容。"""


@dataclass
class Part2EvaluationResult:
    """Part 2 评测结果"""
    success: bool
    transcript: Optional[str] = None
    items: Optional[List[dict]] = None  # 12 题评分
    part2_overall_suggestion: Optional[List[str]] = None
    total_score: float = 0.0  # 0-100
    fluency_score: float = 0.0
    pronunciation_score: float = 0.0
    confidence_score: float = 0.0
    vocabulary_score: float = 0.0
    sentence_score: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[str] = None
    usage: Optional[dict] = None  # Token usage
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "transcript": self.transcript,
            "items": self.items,
            "part2_overall_suggestion": self.part2_overall_suggestion,
            "total_score": self.total_score,
            "fluency_score": self.fluency_score,
            "pronunciation_score": self.pronunciation_score,
            "confidence_score": self.confidence_score,
            "vocabulary_score": self.vocabulary_score,
            "sentence_score": self.sentence_score,
            "error": self.error,
            "usage": self.usage
        }


@dataclass
class Part1EvaluationResult:
    """Part 1 评测结果 (新版 4 维度评分，全部百分制)"""
    success: bool
    total_score: float = 0.0  # 百分制 0-100
    accuracy_score: float = 0.0  # 百分制 0-100
    fluency_score: float = 0.0  # 百分制 0-100
    pronunciation_score: float = 0.0  # 百分制 0-100
    integrity_score: float = 0.0  # 百分制 0-100
    is_rejected: bool = False
    diagnosis: str = ""
    details: Optional[List[dict]] = None
    part1_overall_suggestion: Optional[List[str]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None
    usage: Optional[dict] = None  # Token usage

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "total_score": self.total_score,
            "accuracy_score": self.accuracy_score,
            "fluency_score": self.fluency_score,
            "pronunciation_score": self.pronunciation_score,
            "integrity_score": self.integrity_score,
            "is_rejected": self.is_rejected,
            "diagnosis": self.diagnosis,
            "details": self.details,
            "part1_overall_suggestion": self.part1_overall_suggestion,
            "error": self.error,
            "usage": self.usage
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
        
        # 构建 Prompt
        user_prompt = build_part2_user_prompt(questions)

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
                            "text": user_prompt
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
                full_response, usage = await self._stream_request(request_body)
                result = self._parse_response(full_response)
                result.usage = usage  # Attach usage info
                
                # 限速：每次请求后等待 1 秒（60 RPM）
                await asyncio.sleep(1.0)
                
                return result
                
            except Exception as e:
                logger.exception(f"Qwen API 调用失败: {e}")
                return Part2EvaluationResult(
                    success=False,
                    error=str(e)
                )

    async def evaluate_part1_reading(
        self,
        audio_data: bytes,
        reference_text: str,
        audio_format: str = "pcm"
    ) -> Part1EvaluationResult:
        """
        评测 Part 1 朗读 (使用 Qwen 模拟 Xunfei 输出)
        """
        # 构建 data URL (Qwen 支持 PCM/WAV/MP3)
        # 注意：如果是 raw PCM，Qwen 可能需要 wav header 或者明确指定格式。
        # 为了兼容性，假设传入的是带 header 的 wav 或者 mp3。
        # 如果是纯 PCM，建议在调用前转为 WAV。这里假设调用方会处理，或者 Qwen 能处理 raw pcm (视 API 而定)。
        # 稳妥起见，我们这里假设输入是 wav/mp3。如果是 pcm，建议在 UseCase 层转码。
        
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        mime_type = "audio/wav" # Default to wav for pcm/wav
        if audio_format == "mp3":
            mime_type = "audio/mpeg"
        elif audio_format == "pcm":
             mime_type = "audio/pcm" # Qwen might not support this directly via data url without container
        
        data_url = f"data:{mime_type};base64,{audio_base64}"
        
        user_prompt = f"""请评测这段朗读录音。
参考文本:
{reference_text}

请严格按照 JSON 格式输出评分。"""

        request_body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": PART1_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": data_url,
                                "format": "wav" if audio_format == "pcm" else audio_format # Qwen usually expects wav for raw audio
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ],
            "modalities": ["text"],
            "stream": False # Part 1 不用流式，直接等结果
        }
        
        async with self.semaphore:
            logger.info(f"开始 Qwen Part 1 评测，音频大小: {len(audio_data)} bytes")
            try:
                # 非流式请求
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=request_body
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    result = self._parse_part1_response(content)
                    result.usage = usage
                    return result
                    
            except Exception as e:
                logger.exception(f"Qwen Part 1 API 调用失败: {e}")
                return Part1EvaluationResult(success=False, error=str(e))

    def _parse_part1_response(self, response_text: str) -> Part1EvaluationResult:
        """解析 Part 1 JSON 响应 (新版 4 维度评分)"""
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response_text)
            
            # 提取 4 个维度分数 (直接百分制)
            accuracy = float(data.get("accuracy_score", 0))
            fluency = float(data.get("fluency_score", 0))
            pronunciation = float(data.get("pronunciation_score", 0))
            integrity = float(data.get("integrity_score", 0))
            
            # 优先使用模型返回的 total_score
            total_score = float(data.get("total_score", 0))
            
            # 简单的校验：如果总分为 0 但分项有分，尝试重新计算
            if total_score == 0 and (accuracy > 0 or fluency > 0):
                # total_score = (accuracy * 0.35) + (fluency * 0.25) + (pronunciation * 0.3) + (integrity * 0.1)
                calculated = (accuracy * 0.35) + (fluency * 0.25) + (pronunciation * 0.3) + (integrity * 0.1)
                total_score = calculated
                
            return Part1EvaluationResult(
                success=True,
                total_score=total_score,
                accuracy_score=accuracy,
                fluency_score=fluency,
                pronunciation_score=pronunciation,
                integrity_score=integrity,
                is_rejected=data.get("is_rejected", False),
                diagnosis=data.get("diagnosis", ""),
                details=data.get("details", []),
                part1_overall_suggestion=data.get("part1_overall_suggestion", []),
                raw_response=response_text
            )
        except Exception as e:
            logger.error(f"解析 Qwen Part 1 响应失败: {e}\nResponse: {response_text}")
            return Part1EvaluationResult(success=False, error=f"解析失败: {e}", raw_response=response_text)
    
    async def _stream_request(self, request_body: dict) -> tuple[str, dict]:
        """
        发送流式 HTTP 请求并收集完整响应
        基于 /async-python-patterns Pattern 7: Async Iterators
        
        Returns:
            (full_content, usage_dict)
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        full_content = ""
        usage = {}
        
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
                        
                        # Capture usage from the last chunk (or any chunk that has it)
                        if chunk.get("usage"):
                            usage = chunk["usage"]
                    except json.JSONDecodeError:
                        continue
        
        logger.debug(f"Qwen 响应长度: {len(full_content)} 字符")
        return full_content, usage
    
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
        if not items:
            logger.warning("Qwen 返回题目列表为空")
            
        # 提取 5 个维度分数 (0-100)
        fluency = float(data.get("fluency_score", 0))
        pronunciation = float(data.get("pronunciation_score", 0))
        confidence = float(data.get("confidence_score", 0))
        vocabulary = float(data.get("vocabulary_score", 0))
        sentence = float(data.get("sentence_score", 0))
        
        # 优先使用模型返回的总分
        total_score = float(data.get("total_score", 0))
        
        # 简单的校验兜底
        if total_score == 0 and (fluency > 0 or pronunciation > 0):
            total_score = (fluency + pronunciation + confidence + vocabulary + sentence) / 5
        
        return Part2EvaluationResult(
            success=True,
            transcript=data.get("transcript_full", ""),
            items=items,
            part2_overall_suggestion=data.get("part2_overall_suggestion", []),
            total_score=total_score,
            fluency_score=fluency,
            pronunciation_score=pronunciation,
            confidence_score=confidence,
            vocabulary_score=vocabulary,
            sentence_score=sentence,
            raw_response=response_text
        )
