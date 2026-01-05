#!/usr/bin/env python3
"""
Qwen3-Omni-Flash 口语测评测试脚本 (结构化输出版)
使用 OpenAI 兼容协议调用阿里云百炼平台的 Qwen3-Omni-Flash 模型，并要求返回 JSON 格式数据
"""

import os
import base64
import json
from pathlib import Path
from openai import OpenAI

# ============================================
# 配置
# ============================================

# API Key 从环境变量获取，或直接填写
API_KEY = os.getenv("DASHSCOPE_API_KEY") or "sk-038d7badfa974ca9850ed879dae34a47"

# 模型名称
MODEL = "qwen3-omni-flash"

# 百炼平台 OpenAI 兼容 base_url
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def create_client():
    """创建 OpenAI 客户端"""
    if not API_KEY:
        raise ValueError(
            "请设置 DASHSCOPE_API_KEY 环境变量，或在代码中直接填写 API_KEY\n"
            "获取方式：https://bailian.console.aliyun.com/"
        )
    
    return OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
    )


def load_audio_file(audio_path: str) -> tuple[str, str, str]:
    """
    加载音频文件并转换为 base64
    
    Returns:
        tuple: (base64编码的音频数据, 音频格式, data URL)
    """
    path = Path(audio_path)
    
    if not path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    
    # 获取音频格式和 MIME 类型
    suffix = path.suffix.lower()
    format_map = {
        ".mp3": ("mp3", "audio/mpeg"),
        ".wav": ("wav", "audio/wav"),
        ".pcm": ("pcm", "audio/pcm"),
        ".m4a": ("m4a", "audio/mp4"),
        ".flac": ("flac", "audio/flac"),
    }
    
    if suffix not in format_map:
        raise ValueError(f"不支持的音频格式: {suffix}")
    
    audio_format, mime_type = format_map[suffix]
    
    # 读取并编码
    with open(path, "rb") as f:
        audio_data = base64.b64encode(f.read()).decode("utf-8")
    
    # 构建 data URL
    data_url = f"data:{mime_type};base64,{audio_data}"
    
    print(f"✅ 已加载音频文件: {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    
    return audio_data, audio_format, data_url


# 定义输出的 JSON Schema
EVALUATION_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "speaking_evaluation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "transcription": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "question": {"type": "string"},
                            "answer": {"type": "string"}
                        },
                        "required": ["id", "question", "answer"],
                        "additionalProperties": False
                    }
                },
                "scores": {
                    "type": "object",
                    "properties": {
                        "pronunciation": {"type": "integer", "description": "Score from 1-10"},
                        "grammar": {"type": "integer", "description": "Score from 1-10"},
                        "fluency": {"type": "integer", "description": "Score from 1-10"},
                        "content": {"type": "integer", "description": "Score from 1-10"},
                        "overall": {"type": "integer", "description": "Score from 1-10"}
                    },
                    "required": ["pronunciation", "grammar", "fluency", "content", "overall"],
                    "additionalProperties": False
                },
                "question_details": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "score": {"type": "integer"},
                            "comment": {"type": "string"}
                        },
                        "required": ["id", "score", "comment"],
                        "additionalProperties": False
                    }
                },
                "pronunciation_issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "word": {"type": "string"},
                            "issue": {"type": "string"}
                        },
                        "required": ["word", "issue"],
                        "additionalProperties": False
                    }
                },
                "grammar_issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "original": {"type": "string"},
                            "corrected": {"type": "string"},
                            "explanation": {"type": "string"}
                        },
                        "required": ["original", "corrected", "explanation"],
                        "additionalProperties": False
                    }
                },
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": [
                "transcription",
                "scores",
                "question_details",
                "pronunciation_issues",
                "grammar_issues",
                "suggestions"
            ],
            "additionalProperties": False
        }
    }
}


def evaluate_speaking(
    client: OpenAI,
    audio_path: str,
    question_context: str,
) -> dict:
    """
    使用 Qwen3-Omni 评测口语，返回结构化 JSON 数据
    """
    # 加载音频
    audio_base64, audio_format, data_url = load_audio_file(audio_path)
    
    # 构建 Prompt
    system_prompt = """
你是一位专业的英语口语评测老师。请听取学生的录音，并根据提供的问题列表进行评测。
请严格按照要求的 JSON 格式输出评测结果。

**评分标准（1-10分）**：
- **发音准确度 (Pronunciation)**: 
  - 9-10: 发音清晰、标准，无明显口音，元音/辅音发音准确。
  - 7-8: 发音较清晰，有个别单词发音不准，但不影响理解。
  - 5-6: 有明显口音，部分单词发音错误，影响理解。
  - 1-4: 发音含糊不清，难以理解。
- **语法正确性 (Grammar)**:
  - 9-10: 语法结构正确，时态、单复数使用得当。
  - 7-8: 偶有小错误（如单复数、冠词），但不影响句意。
  - 5-6: 语法错误较多，影响句子结构的完整性。
  - 1-4: 语法错误严重，无法构成完整句子。
- **流利度 (Fluency)**:
  - 9-10: 语速适中，停顿自然，连贯性好。
  - 7-8: 稍有停顿或重复，但整体流畅。
  - 5-6: 停顿较多，语速缓慢，有明显的犹豫。
  - 1-4: 极不流利，频繁卡顿。
- **内容完整性 (Content)**:
  - 9-10: 回答切题，内容丰富完整，逻辑清晰。
  - 7-8: 回答基本切题，内容较完整。
  - 5-6: 回答部分切题，内容遗漏较多。
  - 1-4: 答非所问或未回答。
"""
    
    user_prompt = f"""
请评测这段录音。

**测试题目**:
{question_context}

请分析学生的回答，包括语音转写、各项评分（1-10分）、每道题的详细点评、发音问题、语法问题以及改进建议。
"""
    
    print(f"\n🎯 正在调用 {MODEL} 进行结构化评测...")
    print("-" * 50)
    
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
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
            modalities=["text"],  # 暂时只获取文本（JSON）
            response_format=EVALUATION_SCHEMA, # 使用结构化输出
            stream=False,
        )
        
        # 获取响应内容
        result_text = completion.choices[0].message.content
        usage_info = completion.usage
        
        print("\n" + "-" * 50)
        
        # 解析 JSON
        try:
            evaluation_json = json.loads(result_text)
            return {
                "success": True,
                "data": evaluation_json,
                "usage": {
                    "prompt_tokens": usage_info.prompt_tokens if usage_info else 0,
                    "completion_tokens": usage_info.completion_tokens if usage_info else 0,
                    "total_tokens": usage_info.total_tokens if usage_info else 0,
                } if usage_info else {}
            }
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "无法解析模型返回的 JSON",
                "raw_output": result_text
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def main():
    """主函数"""
    print("=" * 60)
    print("🎤 Qwen3-Omni 结构化口语测评测试")
    print("=" * 60)
    
    client = create_client()
    
    # Part 2 问题列表
    part2_questions = """Part 2: Sentences - Question & Answer
1. How are you?
2. Are you happy today?
3. How old are you?
4. What grade are you in?
5. Do you have sisters or brothers?
6. How many sisters or brothers do you have?
7. What can you see in your room?
8. What time is it now?
9. When do you wake up?
10. What is your favorite food?
11. Do you like English?
12. Can you count from one to twenty?"""
    
    # 使用转换后的 MP3 文件
    audio_file = "test_converted.mp3"
    
    if Path(audio_file).exists():
        result = evaluate_speaking(
            client=client,
            audio_path=audio_file,
            question_context=part2_questions
        )
        
        if result["success"]:
            print("\n✅ 评测成功！解析后的数据：")
            print(json.dumps(result["data"], indent=2, ensure_ascii=False))
            print(f"\n💰 Token 使用: {result['usage']}")
        else:
            print(f"\n❌ 评测失败: {result['error']}")
    else:
        print(f"⚠️ 音频文件不存在: {audio_file} (请先运行之前的转换命令)")

if __name__ == "__main__":
    main()

