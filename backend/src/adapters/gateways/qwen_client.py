"""
Qwen-Omni 语音评测网关
用于 Part 2 问答评测，基于 /async-python-patterns 和 /prompt-engineering-patterns
"""
import asyncio
import base64
import json
import re
from typing import List, Optional, AsyncIterator
from dataclasses import dataclass

import httpx
from loguru import logger

from src.infrastructure.config import get_settings
from src.infrastructure.rate_limiter import RateLimiter
from src.infrastructure.course_knowledge_base import (
    generate_course_knowledge_prompt,
    generate_roadmap_content_guide,
    calculate_learning_plan,
    normalize_level_code,
)

settings = get_settings()


def strip_thinking_tags(text: str) -> str:
    """
    移除 Qwen 思考模式返回的 <think>...</think> 标签
    
    思考模式开启后，模型会在最终答案前输出思考过程：
    <think>
    这里是模型的思考过程...
    </think>
    {"actual": "json response"}
    
    此函数提取 </think> 后面的实际内容
    """
    # 匹配 <think>...</think> 标签（包括换行）
    pattern = r'<think>[\s\S]*?</think>\s*'
    cleaned = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return cleaned.strip()


# ============================================
# Part 1/2 评分 Prompt 模板
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

## 逐题评分标准 (S/A/B)
每道题需要单独评分，评分等级如下：
- **S (Super)**: 回答准确、完整、流利，语法正确，表达自然
- **A (Average)**: 基本正确，能理解意思，但有小问题（如时态错误、单词发音不准、表达不够完整）
- **B (Below)**: 回答错误、答非所问、未作答、或完全听不懂

## feedback 字段要求 (非常重要)
每道题的 `feedback` 必须**详细具体**，至少包含以下内容：

### 对于 S 评分的回答：
- 指出回答的亮点（如用了什么好的句型、词汇、表达方式）
- 示例：✅ "用完整句子回答，句型 'I like playing...' 使用正确，发音清晰流利"

### 对于 A 评分的回答：
- 指出做对了什么 + 具体哪里有问题 + 如何改正
- 示例：✅ "回答内容正确，但时态有误，说成了 'I go' 而不是 'I went'；过去时要用 went"
- 示例：✅ "能理解问题并作答，但有明显迟疑 'um...'，建议多练习该句型增加熟练度"

### 对于 B 评分的回答：
- 指出具体问题（未作答/答非所问/听不懂）+ 参考答案提示
- 示例：✅ "未作答，沉默超过5秒；这道题可以回答 'My favorite color is blue.'"
- 示例：✅ "答非所问，问的是颜色但回答了食物；应该回答颜色相关内容如 red, blue"
- 示例：✅ "发音模糊无法辨识，只听到 'I... mmm...'；建议先练习基础词汇发音"

### feedback 示例对比
- ❌ 不好: "回答正确"、"有迟疑"、"未作答"
- ✅ 好的: "用 'I like...' 句型完整回答，发音准确，表达自信流利"
- ✅ 好的: "回答基本正确但不够完整，只说了 'Basketball'，建议用完整句子 'I like basketball'"
- ✅ 好的: "沉默未作答；可以尝试回答 'It's sunny today' 或 'The weather is nice'"

## 输出要求
1. 严格输出 JSON 格式
2. 必须包含 5 个维度分数（0-100）和总分
3. 对 12 道题进行转写，给出 S/A/B 评分和**详细具体的反馈**（每条至少15字）
4. 给出 3-5 条针对 Part 2 问答表现的总体改进建议 (part2_overall_suggestion)
5. **重要**：所有评价、诊断、建议内容必须使用**中文**。
6. **思维链 (Chain of Thought)**：在给出最终分数前，请先在内心分析学生的流利度、发音、自信度、词汇和句式。确保分数能准确反映学生的实际水平。
7. **防御性指令**：如果音频完全无声、全是噪音或无法识别为英语作答，请在 `error` 字段中说明原因，并将 `success` 设为 `false`。

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
    {"no": 1, "transcript": "I like playing basketball.", "score": "S", "feedback": "用完整句子回答，'I like playing...' 句型正确，发音清晰，表达自信"},
    {"no": 2, "transcript": "It is... um... red.", "score": "A", "feedback": "回答内容正确，但有明显迟疑 'um...'，建议多练习颜色词汇增加熟练度"},
    {"no": 3, "transcript": "...", "score": "B", "feedback": "沉默未作答，超过5秒无回应；可以尝试回答 'My favorite food is pizza'"}
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
- **扣分细则**: 每错读/漏读/增读一个核心词汇，建议扣除 5-10 分；非核心词汇扣除 2-5 分。

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

## 核心规则 <critical_rules>
1. **固定数量**：<strong>本测评共有 20 个词条（单词或短语），`details` 数组长度**必须精确等于 20，注意一定是20个，大于20个按照常见搭配合并词语**。</strong>
2. **切记details中的content字段不会重复**
3. **强制对齐**：`details` 数组长度必须与参考文本（单词和短语）数**完全一致**。
4. **禁止篡改**：`content` 字段必须是参考文本原词，禁止同义词替换（如 dad -> father 是**绝对禁止**的）。
5. **语言要求**：所有评价、诊断、建议内容必须使用**中文**。
6. **防御性指令**：如果音频完全无声、全是噪音，请将 `is_rejected` 设为 `true`，`total_score` 设为 0。
</critical_rules>

## 短语识别规则 <phrase_rules>
以下类型应作为单个词条（而非多个单词）处理：
1. **复合名词**：ice cream, bus stop, high school, birthday cake, post office
2. **专有名词**：New York, United States, Harry Potter
3. **固定短语**：good morning, thank you, excuse me, by the way
4. **数字表达**：twenty-one, one hundred, three o'clock
5. **用下划线或特殊标记连接的词组**：如 "ice_cream" 或 "[ice cream]" 表示这是一个整体

**判断标准**：如果两个或多个词在语义上构成一个不可分割的概念，应作为一个词条。
</phrase_rules>

## issue 字段要求 (非常重要)
当单词发音有问题时 (score < 80)，`issue` 字段必须**详细具体**地描述问题，包括：
1. **具体错误**：学生实际发出的音是什么（用音标或近似汉字描述）
2. **正确发音**：该单词的正确发音是什么
3. **改进建议**：如何纠正这个发音问题

### issue 示例
- ❌ 不好的 issue: "发音不准"、"读错了"
- ✅ 好的 issue: "th 发成了 /s/，读成了 'sree'；正确发音是 /θriː/，舌尖要轻触上齿"
- ✅ 好的 issue: "元音 /æ/ 发成了 /e/，听起来像 'epple'；apple 的 a 要张大嘴发"
- ✅ 好的 issue: "重音位置错误，重读了第二音节；banana 应重读第二音节 ba-NA-na"
- ✅ 好的 issue: "漏读了尾音 /d/，birthday 的 d 要发出来"
- ✅ 好的 issue: "误读为 father，应该读 dad /dæd/"

## 示例 (Few-Shot)
**输入**:
参考文本: "apple, polar bear, hello, dog" (4个词条)
学生录音: 学生读了 "apple, ice cream, hello, cat"

**正确输出**:
{
  "total_score": 75.0,
  "accuracy_score": 75.0,
  "fluency_score": 80.0,
  "pronunciation_score": 75.0,
  "integrity_score": 100.0,
  "is_rejected": false,
  "diagnosis": "学生将 'dog' 误读为 'cat'，其他词条发音正确。",
  "part1_overall_suggestion": ["注意区分动物词汇", "练习 /d/ 和 /k/ 的发音区别"],
  "details": [
    {"content": "apple", "score": 100, "issue": null},
    {"content": "polar bear", "score": 100, "issue": null},
    {"content": "hello", "score": 100, "issue": null},
    {"content": "dog", "score": 0, "issue": "误读为 cat；dog /dɒɡ/ 和 cat /kæt/ 是不同的动物"}
  ]
}
(注意：polar bear 作为一个词条，而非两个)

## 思维链 (Chain of Thought)
在生成 JSON 之前，请先执行以下步骤：
1. **解析词条列表**：将参考文本拆分为 **20 个词条**，短语作为整体保留（如 "polar bear" 是 1 个词条，不是 2 个）。
2. **听音辨义**：按顺序听录音，判断每个位置的单词是否正确。
3. **对齐检查**：确认 `details` 数组的长度与参考文本词条数是否一致（必须是 20 个）。
4. **评分生成**：根据评分维度计算各项分数。

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
4. 给出 3-5 条针对 Part 2 问答表现的总体改进建议 (part2_overall_suggestion)
5. **重要**：所有反馈、建议内容必须使用**中文**（题目和转写除外）。

严格只输出 JSON，不要有其他内容。"""



# ============================================
# 测评汇总分析 Prompt (给家长看的学习建议 + 五维评语)
# 使用 qwen-plus 模型 + 结构化输出
# ============================================

SUMMARY_ANALYSIS_SYSTEM_PROMPT = """你是一位专业的英语教育专家。你的任务是根据学生的口语测评数据，生成一份详细的测评汇总分析和五维能力评语，帮助家长了解孩子的学习情况。

## 分析原则
1. **客观真实**：基于测评数据给出分析，不夸大不贬低
2. **积极正面**：以鼓励为主，短板表述要委婉
3. **具体举例**：亮点和短板都必须结合具体的词汇或回答举例说明
4. **建议详细**：每条建议至少20字，要具体可执行
5. **评语个性化**：五维评语要结合学生的具体表现，不要使用模板化语言

## 评分参考（新标准）
- 90-100 分：杰出
- 70-89 分：优秀
- 60-69 分：良好
- 0-59 分：待提升

## S/A/B 评分含义
- S (Super): 回答完美
- A (Average): 回答正确但有小问题
- B (Below): 回答错误或未作答

## 举例要求
- 亮点举例：如"词汇发音准确，如 'apple'、'banana' 等单词发音清晰标准"
- 短板举例：如"部分词汇发音需加强，如 'three' 读成了 'free'"
- 问答举例：如"能用完整句子回答问题，如Q3回答'I like playing basketball'表达流畅"

## 五维能力评语要求
为每个维度生成**个性化评语**，需要：
1. **comment**：一句话评语（20-40字），包含等级和具体表现描述
2. **tags**：2-3个标签词，概括该维度的特点

评语格式示例：
- 流利度 comment："等级：优秀 - 整体语速流畅，节奏感好，在回答Q5时有轻微停顿但很快恢复"
- 流利度 tags：["整体流畅", "节奏感好"]
"""

# 测评汇总分析的 JSON Schema (结构化输出，包含五维评语)
_DIMENSION_FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "comment": {
            "type": "string",
            "description": "该维度的评语，格式：等级：{杰出/优秀/良好/待提升} - {具体表现描述}，20-40字"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 3,
            "description": "2-3个标签词，概括该维度的特点"
        }
    },
    "required": ["comment", "tags"],
    "additionalProperties": False
}

SUMMARY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "highlights": {
            "type": "array",
            "items": {"type": "string", "minLength": 15},
            "minItems": 1,
            "maxItems": 2,
            "description": "1-2个最突出的亮点，必须结合具体词汇或回答举例"
        },
        "weaknesses": {
            "type": "array",
            "items": {"type": "string", "minLength": 15},
            "minItems": 1,
            "maxItems": 2,
            "description": "1-2个需要提升的方向，必须结合具体词汇或回答举例，表述要委婉"
        },
        "weekly_plan": {
            "type": "array",
            "items": {"type": "string", "minLength": 20},
            "minItems": 3,
            "maxItems": 3,
            "description": "3条具体的本周练习建议，每条至少20字"
        },
        "dimension_feedback": {
            "type": "object",
            "description": "五维能力的个性化评语",
            "properties": {
                "fluency": _DIMENSION_FEEDBACK_SCHEMA,
                "pronunciation": _DIMENSION_FEEDBACK_SCHEMA,
                "confidence": _DIMENSION_FEEDBACK_SCHEMA,
                "vocabulary": _DIMENSION_FEEDBACK_SCHEMA,
                "sentence": _DIMENSION_FEEDBACK_SCHEMA
            },
            "required": ["fluency", "pronunciation", "confidence", "vocabulary", "sentence"],
            "additionalProperties": False
        }
    },
    "required": ["highlights", "weaknesses", "weekly_plan", "dimension_feedback"],
    "additionalProperties": False
}


# ============================================
# 报告解读 Prompt (班主任演讲稿)
# 使用 qwen-plus 模型 + 结构化输出
# 按6页组织：cover, radar, vocab, dialogue, roadmap, badge
# 总时长约10分钟（1500-2000字）
# ============================================

INTERPRETATION_SYSTEM_PROMPT = """你是一位资深的英语教育专家和演讲稿撰写专家。你的任务是为班主任撰写一份**针对单一学生家长的演讲稿**，用于向该学生的家长一对一解读孩子的英语口语测评报告。

## 演讲稿要求

### 整体要求
- **总时长**：约10分钟（按每分钟150字计算，总共约1500字）
- **语气**：亲切、专业、积极、建设性
- **风格**：口语化，像在和家长一对一面对面交流，针对性强，个性化
- **格式**：纯文本，不需要 Markdown 格式，但可以用口语化的强调方式

### 按页面组织（6页）

每一页对应家长端 H5 报告的一个页面。班主任会边展示报告边向家长讲解**这个孩子**的具体表现。

#### 1. cover（封面页，约1分钟，150字）
- 开场问候，说明今天要解读的是**这个孩子**的测评报告
- 告知**这个孩子**的总分和星级评定
- 简要说明评分体系的意义，让家长了解评分标准

#### 2. radar（能力图谱，约2分钟，300字）
- 解释五维能力图谱的含义（流利度、发音、自信度、词汇、整句输出）
- **针对这个孩子**：具体说明**这个孩子**在哪些维度表现好，结合具体数据说明
- **针对这个孩子**：明确指出**这个孩子**哪些维度需要加强，用具体例子说明
- **个性化建议**：针对**这个孩子**的弱项，给出具体可操作的练习方法

#### 3. vocab（词汇掌握，约2分钟，300字）
- 解释词汇能量站的三种状态（完美/模糊/未学）
- **针对这个孩子**：说明**这个孩子**掌握了哪些单词，可以举例说明（如"比如 apple、banana 这些单词发音很标准"）
- **针对这个孩子**：指出**这个孩子**需要重点练习的单词，具体列出2-3个例子
- **个性化建议**：针对**这个孩子**的词汇情况，给出在家练习的具体方法

#### 4. dialogue（对话表现，约2分钟，300字）
- 解释问答环节的评分标准
- **针对这个孩子**：说明**这个孩子**在哪些题目上回答出色，可以引用具体的题目和回答
- **针对这个孩子**：指出**这个孩子**哪些题目需要改进，说明具体问题（如"第3题回答时有些迟疑"）
- **个性化建议**：针对**这个孩子**的问答表现，给出提升问答能力的具体方法

#### 5. roadmap（成长计划，约2分钟，300字）
- 综合分析**这个孩子**的整体表现
- **针对这个孩子**：总结**这个孩子**的优势，用具体例子说明
- **针对这个孩子**：明确**这个孩子**的改进方向，结合具体数据
- **个性化建议**：为**这个孩子**制定本周的具体练习计划（3-5条），每条都要具体可操作

#### 6. badge（徽章页，约1分钟，150字）
- 祝贺**这个孩子**获得的星级徽章，用孩子的名字称呼
- 针对**这个孩子**的表现给予鼓励的话语，要具体、真诚
- 结束语，邀请家长有问题随时沟通，体现一对一关怀

### 写作技巧（一对一沟通风格）
1. 每页话术要**自然衔接**，像在面对面和这位家长聊天，讲述**这个孩子**的故事
2. 用"我们可以看到**孩子**..."、"在这里我们可以看到..."、"从报告中可以看到..."等过渡语，让家长感觉在共同观看报告
3. 多用"孩子"、"宝贝"、"小朋友"等亲切称呼，可以直接用孩子的名字（如"小明"、"小红"）
4. 批评要委婉，用"还可以进一步提升"、"还有进步空间"代替"不好"、"差"
5. 每个建议要**具体可操作**，不要泛泛而谈，要结合**这个孩子**的具体情况
6. 引用**这个孩子**的具体数据和例子增加说服力，让家长感受到这是专门为**这个孩子**准备的解读
7. 语气要像朋友间的交流，用"您看"、"您觉得"、"我们一起看看"等表达，体现一对一沟通的互动感
8. 避免使用"学生们"、"孩子们"等复数表达，始终聚焦在**这个孩子**身上

## 输出格式
按6页分别输出演讲话术，同时输出一份完整的演讲稿（full_script）供一键复制。
"""

# 报告解读的 JSON Schema (演讲稿格式)
# 每页一段完整的演讲话术（字符串）
INTERPRETATION_SCHEMA = {
    "type": "object",
    "properties": {
        "pages": {
            "type": "object",
            "properties": {
                "cover": {
                    "type": "string",
                    "description": "封面页演讲话术，约150字，包含开场问候和总分介绍"
                },
                "radar": {
                    "type": "string",
                    "description": "能力图谱演讲话术，约300字，融合数据解释、亮点、问题、建议"
                },
                "vocab": {
                    "type": "string",
                    "description": "词汇掌握演讲话术，约300字，融合数据解释、亮点、问题、建议"
                },
                "dialogue": {
                    "type": "string",
                    "description": "对话表现演讲话术，约300字，融合数据解释、亮点、问题、建议"
                },
                "roadmap": {
                    "type": "string",
                    "description": "成长计划演讲话术，约300字，融合总结和具体练习计划"
                },
                "badge": {
                    "type": "string",
                    "description": "徽章页演讲话术，约150字，包含祝贺和结束语"
                }
            },
            "required": ["cover", "radar", "vocab", "dialogue", "roadmap", "badge"],
            "additionalProperties": False
        },
        "full_script": {
            "type": "string",
            "description": "完整演讲稿，将6页内容自然连接，约1500字，可直接复制使用"
        }
    },
    "required": ["pages", "full_script"],
    "additionalProperties": False
}


# ============================================
# 课程规划 Prompt (独立板块，与报告解读并行生成)
# 使用 qwen-plus 模型 + 结构化输出
# 约5分钟，2200字以上
# ============================================

COURSE_SELLING_SYSTEM_PROMPT = """你是一位资深的英语教育顾问和课程规划专家。你的任务是为班主任撰写一份**针对单一学生家长的课程规划演讲稿**，用于向该学生的家长一对一介绍孩子的英语学习规划和课程建议。

## 演讲稿要求

### 整体要求
- **总时长**：约5分钟（按每分钟150字计算，总共约2200字以上）
- **语气**：亲切、专业、积极、有说服力
- **风格**：对话式，像在和家长一对一面对面交流，引导家长参与讨论
- **格式**：纯文本，不需要 Markdown 格式

### 内容结构（8个核心问题）

采用对话式结构，通过8个核心问题引导家长参与讨论：

#### 问题1：孩子当前处于哪个阶段？（约250字）
- 用陈述句直接切入主题，如"关于孩子的学习规划，我想先和您聊聊孩子当下处于哪个阶段。"
- 必须使用课程知识库中的正确级别名称和阶段名称
- 介绍这个阶段在整个CEJ体系中的位置

#### 问题2：学习的内容主要是什么？（约300字）
- 过渡问题："那您知道孩子现在这个阶段主要在学什么内容吗？"
- 必须引用课程知识库中的真实数据（词汇量、句子数、单元主题等）
- 结合孩子课堂上的实际表现举例

#### 问题3：提升哪方面能力？（约250字）
- 用陈述句引导，如"这个阶段重点培养的是听说能力和自信表达。"
- 结合报告数据说明，用孩子的进步案例佐证

#### 问题4：目标级别到哪？（约350字）
- 关键问题："那您对孩子的英语学习有什么期待呢？咱们的目标级别想定到哪？"
- 介绍CEJ体系的里程碑（Level 3、Level 6、Level 9）
- 说明每个里程碑达到后能做什么
- 根据孩子情况建议合适的目标级别

#### 问题5：能学到什么？（约400字）
- 展望："您想知道孩子达到这个目标后能学到什么、能做到什么吗？"
- 引用课程知识库中的阶段能力达成数据
- 用具体生活场景让家长有画面感

#### 问题6：有没有类似的成功案例？（约250字）
- 过渡："说到这里，我想和您分享一个我们学员的真实案例。"
- 必须使用课程知识库中的真实案例数据
- 用真实案例增强家长信心

#### 问题7：需要多少课时？（约300字）
- 必须使用课程知识库中的课时数据，严禁自己计算
- 课时规则：LS=148课时，L0-L6每个都是144课时，L7-L9每个都是48课时
- 引导家长理解课时安排

#### 问题8：如何规划学习周期？（约200字）
- 根据家长的时间安排，给出具体的学习周期建议
- 总结并确认学习计划

### 写作技巧
1. 每个问题之间要**自然衔接**，像在面对面聊天
2. 多用"您看"、"您觉得"、"我们一起看看"等表达，体现互动感
3. **必须使用课程知识库中的真实数据**，严禁编造任何数字
4. 用孩子的名字称呼，增加亲切感
5. 适时询问家长意见，让家长参与决策

## 输出格式
输出一份完整的课程规划演讲稿（纯文本字符串），约2200字以上。
"""

# 课程规划的 JSON Schema
COURSE_SELLING_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "完整的课程规划演讲稿，约2200字以上，包含8个核心问题的对话式内容"
        }
    },
    "required": ["content"],
    "additionalProperties": False
}


@dataclass
class CourseSellingResult:
    """课程规划生成结果"""
    success: bool
    content: Optional[str] = None     # 课程规划演讲稿内容
    error: Optional[str] = None
    usage: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "usage": self.usage
        }


@dataclass
class SummaryAnalysisResult:
    """测评汇总分析结果 (给家长看的学习建议 + 五维评语)"""
    success: bool
    highlights: List[str] = None      # 亮点 1-2 条
    weaknesses: List[str] = None      # 短板 1-2 条
    weekly_plan: List[str] = None     # 本周练习计划 3 条
    # 五维能力的 AI 生成评语（用于家长端雷达图展示）
    dimension_feedback: Optional[dict] = None  # {"fluency": {"comment": "...", "tags": [...]}, ...}
    error: Optional[str] = None
    usage: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "highlights": self.highlights,
            "weaknesses": self.weaknesses,
            "weekly_plan": self.weekly_plan,
            "dimension_feedback": self.dimension_feedback,
            "error": self.error,
            "usage": self.usage
        }


@dataclass
class ReportInterpretationResult:
    """报告解读结果 (班主任演讲稿，按6页组织 + 可选的课程规划)"""
    success: bool
    pages: Optional[dict] = None  # 按页面组织的演讲话术（每页一段字符串）
    full_script: str = None       # 完整演讲稿（约1500字，10分钟）
    course_selling: Optional[str] = None  # 课程规划演讲稿（约2200字，5分钟）
    error: Optional[str] = None
    usage: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "pages": self.pages,
            "full_script": self.full_script,
            "course_selling": self.course_selling,
            "error": self.error,
            "usage": self.usage
        }


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
    # 每个维度的 AI 生成评语（用于家长端雷达图展示）
    dimension_feedback: Optional[dict] = None  # {"fluency": {"comment": "...", "tags": [...]}, ...}
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
            "dimension_feedback": self.dimension_feedback,
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
    Qwen API 网关
    
    支持两种模型：
    - qwen3-omni-flash: 用于音频评测 (Part1/Part2)
    - qwen-plus: 用于文本分析 (测评汇总/报告解读)，支持结构化输出
    
    使用 /async-python-patterns 实现流式 HTTP 请求
    集成 Semaphore 限流以遵守 60 RPM 限制
    """
    
    def __init__(self):
        self.api_key = settings.QWEN_API_KEY
        self.base_url = settings.QWEN_BASE_URL
        self.model = settings.QWEN_MODEL           # qwen3-omni-flash (音频评测)
        self.plus_model = settings.QWEN_PLUS_MODEL  # qwen-plus (文本分析)
        # 分开限流：omni (音频) RPM=60, plus (文本) RPM=600
        self.omni_semaphore = RateLimiter.get_qwen_omni_limiter()  # 5 并发
        self.plus_semaphore = RateLimiter.get_qwen_plus_limiter()  # 10 并发
        # 思考模式配置
        self.enable_thinking = settings.QWEN_ENABLE_THINKING
        self.thinking_budget = settings.QWEN_THINKING_BUDGET
    
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
        
        # 添加思考模式参数 (提高评测准确性)
        if self.enable_thinking:
            request_body["enable_thinking"] = True
            request_body["thinking_budget"] = self.thinking_budget
            logger.info(f"Part 2 启用思考模式，thinking_budget={self.thinking_budget}")
        
        # 使用 omni_semaphore 限流 (qwen3-omni-flash, RPM=60)
        async with self.omni_semaphore:
            logger.info(f"开始 Qwen Part 2 评测，音频大小: {len(audio_data)} bytes")
            
            try:
                full_response, usage = await self._stream_request(request_body)
                result = self._parse_part2_response(full_response)
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
            "stream": True,  # 模型要求必须使用流式输出
            "stream_options": {"include_usage": True}
        }
        
        # 添加思考模式参数 (提高评测准确性)
        if self.enable_thinking:
            request_body["enable_thinking"] = True
            request_body["thinking_budget"] = self.thinking_budget
            logger.info(f"Part 1 启用思考模式，thinking_budget={self.thinking_budget}")
        
        # 使用 omni_semaphore 限流 (qwen3-omni-flash, RPM=60)
        async with self.omni_semaphore:
            logger.info(f"开始 Qwen Part 1 评测，音频大小: {len(audio_data)} bytes")
            try:
                # 流式请求
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=request_body
                    ) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            logger.error(f"Qwen Part 1 API 错误 [{response.status_code}]: {error_text.decode()}")
                            # 截断错误信息，避免数据库字段溢出
                            error_msg = error_text.decode()[:200]
                            return Part1EvaluationResult(success=False, error=f"API错误: {error_msg}")
                        
                        # 收集流式响应
                        content_parts = []
                        usage = {}
                        
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            
                            data_str = line[6:]  # 去掉 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data_str)
                                # 获取 usage 信息
                                if "usage" in chunk and chunk["usage"]:
                                    usage = chunk["usage"]
                                
                                # 获取内容
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    if "content" in delta and delta["content"]:
                                        content_parts.append(delta["content"])
                            except json.JSONDecodeError:
                                continue
                        
                        content = "".join(content_parts)
                        logger.info(f"Part 1 流式响应完成，内容长度: {len(content)}")
                        
                        result = self._parse_part1_response(content, reference_text)
                        result.usage = usage
                        return result
                    
            except Exception as e:
                logger.exception(f"Qwen Part 1 API 调用失败: {e}")
                # 截断错误信息
                return Part1EvaluationResult(success=False, error=str(e)[:200])

    def _parse_part1_response(self, response_text: str, reference_text: str = "") -> Part1EvaluationResult:
        """解析 Part 1 JSON 响应 (新版 4 维度评分)"""
        try:
            # 1. 移除思考模式的 <think> 标签
            cleaned_text = strip_thinking_tags(response_text)
            if cleaned_text != response_text:
                logger.debug(f"Part1: 已移除思考标签，原始长度={len(response_text)}, 清理后={len(cleaned_text)}")
            
            json_match = re.search(r'\{[\s\S]*\}', cleaned_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(cleaned_text)
            
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
                
            # Post-processing: Force align content with reference text if counts match
            # This fixes the issue where model hallucinates synonyms (e.g. dad -> father)
            details = data.get("details", [])
            if details and reference_text:
                # Split by comma to support phrases as single items (e.g., "polar bear")
                ref_words = [w.strip() for w in reference_text.strip().split(",")]
                
                if len(details) == len(ref_words):
                    logger.info("Aligning Part 1 details content with reference text")
                    for i, detail in enumerate(details):
                        # Force overwrite content with reference word
                        # This ensures the UI shows the correct question word
                        if detail.get("content") != ref_words[i]:
                            logger.warning(f"Correcting content mismatch: {detail.get('content')} -> {ref_words[i]}")
                            detail["content"] = ref_words[i]
                else:
                    logger.warning(f"Part 1 count mismatch: details={len(details)}, ref={len(ref_words)}. Skipping alignment.")

            return Part1EvaluationResult(
                success=True,
                total_score=total_score,
                accuracy_score=accuracy,
                fluency_score=fluency,
                pronunciation_score=pronunciation,
                integrity_score=integrity,
                is_rejected=data.get("is_rejected", False),
                diagnosis=data.get("diagnosis", ""),
                details=details,
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
    
    async def generate_summary_analysis(
        self,
        student_name: str,
        level: str,
        total_score: float,
        star_level: int,
        radar_scores: dict,
        part1_score: float,
        part2_score: Optional[float] = None,
        part1_words: Optional[List[dict]] = None,
        part2_items: Optional[List[dict]] = None,
        part1_suggestion: Optional[List[str]] = None,
        part2_suggestion: Optional[List[str]] = None
    ) -> SummaryAnalysisResult:
        """
        生成测评汇总分析 (给家长看的学习建议)
        
        使用 qwen-plus 模型 + 结构化输出
        
        Args:
            student_name: 学生姓名
            level: 测试等级
            total_score: 总分 (0-100)
            star_level: 星级 (1-5)
            radar_scores: 五维雷达图分数 {fluency, pronunciation, confidence, vocabulary, sentence}
            part1_score: Part 1 分数
            part2_score: Part 2 分数
            part1_words: Part 1 词汇详情列表 [{word, score, status}]
            part2_items: Part 2 问答详情列表 [{no, score, transcript, feedback}]
            part1_suggestion: Part 1 的建议
            part2_suggestion: Part 2 的建议
            
        Returns:
            SummaryAnalysisResult
        """
        # 构建输入数据
        input_data = {
            "student": {"name": student_name, "level": level},
            "scores": {
                "total": total_score,
                "star_level": star_level,
                "part1": part1_score,
                "part2": part2_score,
                "radar": {
                    "fluency": round(radar_scores.get("fluency", 0), 1),
                    "pronunciation": round(radar_scores.get("pronunciation", 0), 1),
                    "confidence": round(radar_scores.get("confidence", 0), 1),
                    "vocabulary": round(radar_scores.get("vocabulary", 0), 1),
                    "sentence": round(radar_scores.get("sentence", 0), 1)
                }
            }
        }
        
        # 添加 Part1 词汇详情 (用于具体举例)
        if part1_words:
            perfect_words = [w["word"] for w in part1_words if w.get("status") == "perfect"][:5]
            # 获取有问题的词及其具体问题描述
            weak_words_with_issues = [
                {"word": w["word"], "issue": w.get("issue") or "发音不清"} 
                for w in part1_words 
                if w.get("status") in ("unclear", "failed")
            ][:5]
            input_data["part1_details"] = {
                "good_words": perfect_words,
                "weak_words": weak_words_with_issues,  # 包含具体问题描述
                "total_words": len(part1_words),
                "perfect_count": len([w for w in part1_words if w.get("status") == "perfect"])
            }
        
        # 添加 Part2 问答详情 (用于具体举例)
        if part2_items:
            good_answers = [{"no": q["no"], "answer": q.get("transcript", "")[:50]} 
                          for q in part2_items if q.get("score") in ("S", "A")][:3]
            weak_answers = [{"no": q["no"], "feedback": q.get("feedback", "")[:50]} 
                          for q in part2_items if q.get("score") == "B"][:3]
            input_data["part2_details"] = {
                "good_answers": good_answers,
                "weak_answers": weak_answers,
                "total_questions": len(part2_items)
            }
        
        # 添加原始建议作为参考
        if part1_suggestion:
            input_data["part1_model_suggestion"] = part1_suggestion[:2]
        if part2_suggestion:
            input_data["part2_model_suggestion"] = part2_suggestion[:2]
        
        user_prompt = f"""请根据以下测评数据生成测评汇总分析和五维能力评语：

{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 输出要求
1. **亮点**：必须结合具体的词汇（如good_words中的单词）或回答（如good_answers）举例说明
2. **短板**：必须结合具体的词汇（如weak_words）或回答（如weak_answers）举例说明，表述要委婉
3. **周计划**：每条建议至少20字，要具体说明练习什么、怎么练、练多久
4. **五维评语**（dimension_feedback）：
   - 根据 radar 分数判断等级：≥90杰出，70-89优秀，60-69良好，<60待提升
   - 每个维度的 comment 必须包含"等级：xxx - "前缀，然后是具体表现描述
   - 结合学生的具体表现（词汇、回答）生成个性化评语，不要使用模板化语言
   - 如流利度评语："等级：优秀 - 整体语速流畅，节奏感好，Q5回答时有轻微停顿但很快恢复\""""

        request_body = {
            "model": self.plus_model,  # 使用 qwen-plus
            "messages": [
                {"role": "system", "content": SUMMARY_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "summary_analysis",
                    "strict": True,
                    "schema": SUMMARY_ANALYSIS_SCHEMA
                }
            }
        }
        
        # 使用 plus_semaphore 限流 (qwen-plus, RPM=600)
        async with self.plus_semaphore:
            logger.info(f"开始生成测评汇总分析 (qwen-plus): {student_name}")
            usage = {}  # 初始化 usage，确保失败时也能访问
            content = ""
            try:
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
                    
                    logger.info(f"测评汇总分析完成, tokens: {usage}")
                    
                    # 移除可能的思考标签
                    cleaned_content = strip_thinking_tags(content)
                    result_data = json.loads(cleaned_content)
                    return SummaryAnalysisResult(
                        success=True,
                        highlights=result_data.get("highlights", []),
                        weaknesses=result_data.get("weaknesses", []),
                        weekly_plan=result_data.get("weekly_plan", []),
                        dimension_feedback=result_data.get("dimension_feedback"),  # AI 生成的五维评语
                        usage=usage
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"测评汇总分析 JSON 解析失败: {e}, content={content[:200] if content else 'empty'}")
                # 即使解析失败，也返回 usage 数据用于计费
                return SummaryAnalysisResult(success=False, error=f"JSON 解析失败: {e}", usage=usage)
            except Exception as e:
                logger.exception(f"测评汇总分析生成失败: {e}")
                # 网络异常等情况可能没有 usage
                return SummaryAnalysisResult(success=False, error=str(e), usage=usage if usage else None)
    
    async def generate_course_selling(
        self,
        student_name: str,
        level: str,
        total_score: float,
        star_level: int,
        radar_data: Optional[list] = None,
        target_level: str = None,
    ) -> CourseSellingResult:
        """
        生成课程规划演讲稿（独立板块）
        
        使用 qwen-plus 模型 + 结构化输出
        约5分钟，2200字以上
        
        Args:
            student_name: 学生姓名
            level: 当前级别
            total_score: 总分
            star_level: 星级
            radar_data: 五维能力数据
            target_level: 目标级别（如果为 None 则使用推荐目标级别）
        """
        # 获取课程知识库数据
        course_knowledge = generate_course_knowledge_prompt(level, target_level)
        roadmap_guide = generate_roadmap_content_guide(level, target_level)
        
        # 构建输入数据摘要
        input_summary = {
            "student_name": student_name,
            "current_level": level,
            "total_score": total_score,
            "star_level": star_level,
            "radar": radar_data,
        }
        
        user_prompt = f"""请根据以下学生信息和课程知识库，生成课程规划演讲稿：

## 学生信息摘要
{json.dumps(input_summary, ensure_ascii=False, indent=2)}

## 课程知识库数据（必须引用！）
{course_knowledge}

## 内容指南（必须遵循！）
{roadmap_guide}

请按 JSON Schema 要求输出，生成约2200字以上的课程规划演讲稿。"""

        request_body = {
            "model": self.plus_model,  # 使用 qwen-plus
            "messages": [
                {"role": "system", "content": COURSE_SELLING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "course_selling",
                    "strict": True,
                    "schema": COURSE_SELLING_SCHEMA
                }
            }
        }
        
        # 使用 plus_semaphore 限流 (qwen-plus, RPM=600)
        async with self.plus_semaphore:
            logger.info(f"开始生成课程规划 (qwen-plus, 8个核心问题): {student_name}")
            usage = {}
            content = ""
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:  # 课程规划内容多，超时时间更长
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=request_body
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    logger.info(f"课程规划完成, tokens: {usage}")
                    
                    # 移除可能的思考标签
                    cleaned_content = strip_thinking_tags(content)
                    result_data = json.loads(cleaned_content)
                    return CourseSellingResult(
                        success=True,
                        content=result_data.get("content", ""),
                        usage=usage
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"课程规划 JSON 解析失败: {e}, content={content[:200] if content else 'empty'}")
                # 即使解析失败，也返回 usage 数据用于计费（API 已调用成功）
                return CourseSellingResult(success=False, error=f"JSON 解析失败: {e}", usage=usage)
            except Exception as e:
                logger.exception(f"课程规划生成失败: {e}")
                # 网络异常等情况，usage 可能为空字典，但仍要记录（表示尝试调用）
                return CourseSellingResult(success=False, error=str(e), usage=usage)

    async def generate_report_interpretation(
        self,
        student_name: str,
        level: str,
        total_score: float,
        part1_score: float,
        part2_score: Optional[float],
        star_level: int,
        part1_details: Optional[dict] = None,
        part2_items: Optional[list] = None,
        radar_data: Optional[list] = None,
        include_course_selling: bool = False,
        target_level: str = None,
    ) -> ReportInterpretationResult:
        """
        生成报告解读 (按6页组织：cover/radar/vocab/dialogue/roadmap/badge)
        
        使用 qwen-plus 模型 + 结构化输出
        
        Args:
            student_name: 学生姓名
            level: 当前级别
            total_score: 总分
            part1_score: Part 1 得分
            part2_score: Part 2 得分
            star_level: 星级
            part1_details: Part 1 详情（单词掌握情况）
            part2_items: Part 2 题目列表
            radar_data: 五维能力数据
            include_course_selling: 是否同时生成课程规划（并行调用）
            target_level: 目标级别（用于课程规划）
        """
        if include_course_selling:
            # 并行调用：同时生成6页报告和课程规划
            logger.info(f"开始并行生成报告解读和课程规划: {student_name}")
            
            report_task = self._generate_report_pages(
                student_name, level, total_score, part1_score, part2_score,
                star_level, part1_details, part2_items, radar_data
            )
            selling_task = self.generate_course_selling(
                student_name, level, total_score, star_level,
                radar_data, target_level
            )
            
            # 并行执行，允许异常传播
            results = await asyncio.gather(
                report_task, selling_task, return_exceptions=True
            )
            
            report_result = results[0]
            selling_result = results[1]
            
            # 处理异常情况
            if isinstance(report_result, Exception):
                logger.exception(f"报告解读生成异常: {report_result}")
                report_result = ReportInterpretationResult(
                    success=False, error=str(report_result)
                )
            if isinstance(selling_result, Exception):
                logger.exception(f"课程规划生成异常: {selling_result}")
                selling_result = CourseSellingResult(
                    success=False, error=str(selling_result)
                )
            
            # 合并结果 - 即使失败也要记录成本
            combined_usage = {}
            if report_result.usage is not None:
                combined_usage["report"] = report_result.usage
            if selling_result.usage is not None:
                combined_usage["course_selling"] = selling_result.usage
            
            return ReportInterpretationResult(
                success=report_result.success,  # 主报告成功即可
                pages=report_result.pages if report_result.success else None,
                full_script=report_result.full_script if report_result.success else None,
                course_selling=selling_result.content if selling_result.success else None,
                error=report_result.error if not report_result.success else (
                    f"课程规划失败: {selling_result.error}" if not selling_result.success else None
                ),
                usage=combined_usage
            )
        else:
            # 仅生成6页报告
            return await self._generate_report_pages(
                student_name, level, total_score, part1_score, part2_score,
                star_level, part1_details, part2_items, radar_data
            )

    async def _generate_report_pages(
        self,
        student_name: str,
        level: str,
        total_score: float,
        part1_score: float,
        part2_score: Optional[float],
        star_level: int,
        part1_details: Optional[dict] = None,
        part2_items: Optional[list] = None,
        radar_data: Optional[list] = None,
    ) -> ReportInterpretationResult:
        """
        内部方法：生成6页报告解读
        """
        # 构建 Prompt 输入数据（按页面说明数据来源）
        input_data = {
            "student": {
                "name": student_name,
                "level": level,
                "total_score": total_score,
                "star_level": star_level
            },
            "part1": {
                "score": part1_score,
                "details": part1_details  # 包含 words 列表，每个 word 有 text/score/status
            },
            "part2": {
                "score": part2_score,
                "items": part2_items  # 包含每题的 question_no/score/evidence
            },
            "radar": radar_data  # 五维能力图谱：流利度/发音/自信度/词汇/整句输出
        }
        
        user_prompt = f"""请根据以下测评数据，按6个页面生成报告解读：

{json.dumps(input_data, ensure_ascii=False, indent=2)}

## 数据来源说明
- **cover（封面页）**：使用 student.total_score, student.star_level, student.level
- **radar（雷达图）**：使用 radar 数据（流利度/发音/自信度/词汇/整句输出）
- **vocab（词汇页）**：使用 part1.details.words（单词掌握情况）
- **dialogue（对话页）**：使用 part2.items（每题得分和评价）
- **roadmap（成长计划）**：综合所有数据
- **badge（徽章页）**：使用 student.star_level

请按 JSON Schema 要求输出。"""

        request_body = {
            "model": self.plus_model,  # 使用 qwen-plus
            "messages": [
                {"role": "system", "content": INTERPRETATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "report_interpretation",
                    "strict": True,
                    "schema": INTERPRETATION_SCHEMA
                }
            }
        }
        
        # 使用 plus_semaphore 限流 (qwen-plus, RPM=600)
        async with self.plus_semaphore:
            logger.info(f"开始生成报告解读 (qwen-plus, 6页结构): {student_name}")
            usage = {}  # 初始化 usage，确保失败时也能访问
            content = ""
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:  # 增加超时时间
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=request_body
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    logger.info(f"报告解读完成, tokens: {usage}")
                    
                    # 移除可能的思考标签
                    cleaned_content = strip_thinking_tags(content)
                    result_data = json.loads(cleaned_content)
                    return ReportInterpretationResult(
                        success=True,
                        pages=result_data.get("pages", {}),
                        full_script=result_data.get("full_script", ""),
                        usage=usage
                    )
                    
            except json.JSONDecodeError as e:
                logger.error(f"报告解读 JSON 解析失败: {e}, content={content[:200] if content else 'empty'}")
                # 即使解析失败，也返回 usage 数据用于计费
                return ReportInterpretationResult(success=False, error=f"JSON 解析失败: {e}", usage=usage)
            except Exception as e:
                logger.exception(f"报告解读生成失败: {e}")
                # 网络异常等情况可能没有 usage
                return ReportInterpretationResult(success=False, error=str(e), usage=usage if usage else None)

    def _parse_part2_response(self, response_text: str) -> Part2EvaluationResult:
        """
        解析 Qwen 返回的 Part 2 JSON 响应
        基于 /prompt-engineering-patterns - Error Recovery
        """
        # 1. 移除思考模式的 <think> 标签
        cleaned_text = strip_thinking_tags(response_text)
        if cleaned_text != response_text:
            logger.debug(f"已移除思考标签，原始长度={len(response_text)}, 清理后={len(cleaned_text)}")
        
        try:
            # 尝试直接解析 JSON
            data = json.loads(cleaned_text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            json_match = re.search(r'\{[\s\S]*\}', cleaned_text)
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
