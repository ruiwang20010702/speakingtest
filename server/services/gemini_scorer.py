"""
Gemini AI 评分服务
使用 Gemini 2.5 Flash 分析音频并进行评分
"""
import json
from typing import Dict, List, Tuple
from services.gemini_client import gemini_client


def calculate_star_rating(total_score: float, max_score: float = 60) -> int:
    """
    根据总分计算星级评分
    
    Args:
        total_score: 总分（0-60）
        max_score: 总分满分（默认60）
    
    Returns:
        星级评分（0-5）
    """
    if total_score >= 56:
        return 5  # 杰出
    elif total_score >= 48:
        return 4  # 优秀
    elif total_score >= 30:
        return 3  # 良好
    elif total_score >= 1:
        return 2  # 中等
    else:
        return 1  # 需努力


def create_part1_prompt(words: List[str]) -> str:
    """
    创建 Part 1（词汇朗读）的评分 prompt
    
    Args:
        words: 需要朗读的单词列表
    
    Returns:
        评分 prompt
    """
    words_str = ", ".join(words)
    
    prompt = f"""你是一位专业的英语口语评估专家。请分析这段学生朗读单词的录音。

**任务**：学生需要朗读以下 {len(words)} 个单词：
{words_str}

**评分标准**：
- 每个单词发音正确：1分
- 总分：{len(words)}分
- 评估要点：元音准确性、辅音清晰度、重音位置

**重要要求**：请识别每个单词在录音中的大致时间位置（秒），这将帮助验证评分准确性。

**请以 JSON 格式返回评分结果**：
{{
  "score": 总分（0-{len(words)}的数字）,
  "correct_words": ["正确的单词1", "正确的单词2", ...],
  "incorrect_words": ["错误的单词1", "错误的单词2", ...],
  "word_timestamps": [
    {{
      "word": "单词",
      "correct": true或false,
      "start_time": 开始时间（秒，浮点数）,
      "end_time": 结束时间（秒，浮点数）,
      "confidence": 置信度（0-1，可选）
    }},
    ...
  ],
  "feedback": "整体反馈，包括发音问题和改进建议"
}}

注意：
1. 只返回 JSON，不要包含其他文字
2. 时间戳尽可能准确，如果无法确定可以估算
3. word_timestamps 应包含所有尝试朗读的单词
4. **重要**：feedback字段必须使用中文，但correct_words和incorrect_words保持英文原词
"""
    
    return prompt


def create_part2_prompt(words: List[str], sentences: List[str]) -> str:
    """
    创建 Part 2（自然拼读）的评分 prompt
    
    Args:
        words: 单词列表
        sentences: 句子列表
    
    Returns:
        评分 prompt
    """
    words_str = ", ".join(words)
    sentences_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(sentences)])
    
    prompt = f"""你是一位专业的英语口语评估专家。请分析这段学生自然拼读的录音。

**任务**：
1. 单词朗读（{len(words)}个单词）：{words_str}
2. 句子朗读（{len(sentences)}个句子）：
{sentences_str}

**评分标准**：
- 单词部分：每个单词0.5分，总计{len(words) * 0.5}分
- 句子部分：每个句子根据发音准确性、连读流畅度、语调自然度评分，每句2.5分，总计{len(sentences) * 2.5}分
- 总分：{len(words) * 0.5 + len(sentences) * 2.5}分

**重要要求**：请识别每个单词和句子在录音中的大致时间位置（秒），这将帮助验证评分准确性。

**请以 JSON 格式返回评分结果**：
{{
  "score": 总分（0-{len(words) * 0.5 + len(sentences) * 2.5}的数字）,
  "word_score": 单词部分得分,
  "sentence_score": 句子部分得分,
  "correct_words": ["正确的单词"],
  "incorrect_words": ["错误的单词"],
  "word_timestamps": [
    {{
      "word": "单词",
      "correct": true或false,
      "start_time": 开始时间（秒）,
      "end_time": 结束时间（秒）
    }},
    ...
  ],
  "sentence_timestamps": [
    {{
      "sentence_index": 句子序号（1-{len(sentences)}）,
      "start_time": 开始时间（秒）,
      "end_time": 结束时间（秒）,
      "quality_score": 质量评分（0-2.5）
    }},
    ...
  ],
  "sentence_quality": ["句子1的评价", "句子2的评价", ...],
  "feedback": "整体反馈"
}}

注意：
1. 只返回 JSON，不要包含其他文字
2. 时间戳尽可能准确，如果无法确定可以估算
3. 先朗读单词，后朗读句子，时间戳应体现这个顺序
4. **重要**：feedback和sentence_quality字段必须使用中文，但单词和句子内容保持英文
"""
    
    return prompt


def create_part3_prompt(dialogues: List[Dict]) -> str:
    """
    创建 Part 3（句子问答）的评分 prompt
    
    Args:
        dialogues: 问答对话列表，格式为 [{"teacher": "问题", "student_options": ["答案选项"]}]
    
    Returns:
        评分 prompt
    """
    questions_str = "\n".join([
        f"{i+1}. Teacher: {d['teacher']}\n   Expected: {' / '.join(d.get('student_options', []))}"
        for i, d in enumerate(dialogues)
    ])
    
    prompt = f"""你是一位专业的英语口语评估专家。请分析这段学生回答问题的录音。

**任务**：学生需要回答以下 12 个问题：
{questions_str}

**评分标准**：
- 每个问题回答完整且正确：2分
- 部分正确或不完整：1分
- 无法回答或完全错误：0分
- 总分：24分
- 评估要点：语义准确性、语法正确性、表达流畅度

**额外评估维度**（每项0-10分）：
1. **流畅度 (Fluency)**：评估学生说话的连贯性和自然度
   - 10分：非常流畅，无明显停顿，语速自然
   - 7-9分：较为流畅，偶有停顿
   - 4-6分：有明显停顿，但能完成表达
   - 0-3分：说话断断续续，严重影响理解

2. **发音 (Pronunciation)**：评估整体发音准确性
   - 10分：发音标准，音调自然
   - 7-9分：发音清晰，偶有小错误
   - 4-6分：发音基本清晰，有一些错误
   - 0-3分：发音有明显问题

3. **自信度 (Confidence)**：评估学生的表达自信程度
   - 10分：非常自信，声音洪亮清晰
   - 7-9分：较为自信，表达清楚
   - 4-6分：有些犹豫，但能完成回答
   - 0-3分：明显紧张或不确定

请仔细聆听音频，评估学生对每个问题的回答质量，并给出整体能力评估。

**请以 JSON 格式返回评分结果**：
{{
  "score": 总分（0-24的数字）,
  "fluency_score": 流畅度评分（0-10）,
  "pronunciation_score": 发音评分（0-10）,
  "confidence_score": 自信度评分（0-10）,
  "question_scores": [
    {{
      "question_num": 1,
      "score": 得分（0/1/2）,
      "student_answer": "学生的回答",
      "comment": "评价"
    }},
    ...
  ],
  "feedback": "整体反馈"
}}

注意：
1. 只返回 JSON，不要包含其他文字
2. **重要**：feedback和comment字段必须使用中文评价
3. student_answer字段必须保持学生说的英文原话"""
    
    return prompt

from services.gemini_client import GeminiClient
from services.retry_decorator import retry_on_error
from typing import List, Dict, Tuple
import json


def parse_gemini_response(response_text: str) -> Dict:
    """
    解析 Gemini 返回的 JSON 响应
    
    Args:
        response_text: Gemini 的响应文本
    
    Returns:
        解析后的字典
    """
    import re
    
    try:
        # 提取 JSON（可能被包裹在代码块中）
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        else:
            # 尝试查找第一个 { 和最后一个 }
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
            else:
                json_str = response_text.strip()
        
        # 清理尾随逗号（Gemini 有时会生成不符合 JSON 标准的尾随逗号）
        # 移除数组中的尾随逗号: ,]
        json_str = re.sub(r',\s*]', ']', json_str)
        # 移除对象中的尾随逗号: ,}
        json_str = re.sub(r',\s*}', '}', json_str)
        
        # 解析 JSON
        result = json.loads(json_str)
        print(f"✅ 评分完成: {result.get('score', 'N/A')} 分")
        return result
        
    except json.JSONDecodeError as e:
        error_msg = f"❌ JSON解析失败: {str(e)}\n响应内容: {response_text[:200]}..."
        print(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"❌ 解析错误: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)


@retry_on_error(max_retries=3, delay=2.0, backoff=2.0)
def evaluate_part1(audio_path: str, words: List[str]) -> Tuple[float, Dict]:
    """
    评估 Part 1 - 词汇朗读（带重试机制）
    
    Args:
        audio_path: 音频文件路径
        words: 单词列表
    
    Returns:
        (得分, 详细结果字典)
    """
    prompt = create_part1_prompt(words)
    response = gemini_client.analyze_audio_from_path(audio_path, prompt)
    result = parse_gemini_response(response)
    
    return result.get("score", 0), result


@retry_on_error(max_retries=3, delay=2.0, backoff=2.0)
def evaluate_part2(audio_path: str, words: List[str], sentences: List[str]) -> Tuple[float, Dict]:
    """
    评估 Part 2 - 自然拼读（带重试机制）
    
    Args:
        audio_path: 音频文件路径
        words: 单词列表
        sentences: 句子列表
    
    Returns:
        (得分, 详细结果字典)
    """
    prompt = create_part2_prompt(words, sentences)
    response = gemini_client.analyze_audio_from_path(audio_path, prompt)
    result = parse_gemini_response(response)
    
    return result.get("score", 0), result


def evaluate_part3(audio_path: str, dialogues: List[Dict]) -> Tuple[float, Dict]:
    """
    评估 Part 3 - 句子问答
    
    Args:
        audio_path: 音频文件路径
        dialogues: 问答对话列表
    
    Returns:
        (得分, 详细结果字典)
    """
    prompt = create_part3_prompt(dialogues)
    response = gemini_client.analyze_audio_from_path(audio_path, prompt)
    result = parse_gemini_response(response)
    
    return result.get("score", 0), result
