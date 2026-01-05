#!/usr/bin/env python3
"""
Qwen3-Omni-Flash 口语测评测试脚本
使用 OpenAI 兼容协议调用阿里云百炼平台的 Qwen3-Omni-Flash 模型
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
MODEL = "qwen-omni-turbo"  # 或 "qwen-omni-turbo-latest"

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


def evaluate_speaking(
    client: OpenAI,
    audio_path: str,
    question: str = None,
    expected_answer: str = None,
) -> dict:
    """
    使用 Qwen3-Omni 评测口语
    
    Args:
        client: OpenAI 客户端
        audio_path: 音频文件路径
        question: 测试题目（可选）
        expected_answer: 参考答案（可选）
    
    Returns:
        评测结果字典
    """
    # 加载音频
    audio_base64, audio_format, data_url = load_audio_file(audio_path)
    
    # 构建评测 prompt
    prompt_parts = ["请评测这段英语口语录音：\n"]
    
    if question:
        prompt_parts.append(f"**测试题目**: {question}\n")
    
    if expected_answer:
        prompt_parts.append(f"**参考答案**: {expected_answer}\n")
    
    prompt_parts.append("""
请按以下格式输出评测结果：

## 1. 语音转写
（学生实际说了什么，逐字转写）

## 2. 评分（每项1-10分）
- **发音准确度**: X/10
- **语法正确性**: X/10  
- **流利度**: X/10
- **内容完整性**: X/10
- **综合得分**: X/10

## 3. 发音问题
（列出发音有问题的单词，并说明具体问题）

## 4. 语法问题
（列出语法错误，并给出正确表达）

## 5. 改进建议
（给出具体、可操作的改进建议）
""")
    
    prompt = "\n".join(prompt_parts)
    
    print(f"\n🎯 正在调用 {MODEL} 进行评测...")
    print("-" * 50)
    
    # 调用 API - 使用流式输出（百炼 Qwen-Omni 要求 stream=True）
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的英语口语评测老师，擅长评估学生的发音、语法和流利度。请认真听取学生的口语录音，给出详细、准确的评测反馈。"
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
                            "text": prompt
                        }
                    ]
                }
            ],
            # 只输出文本，不输出音频
            modalities=["text"],
            stream=True,
            stream_options={"include_usage": True},
        )
        
        # 收集流式响应
        result_text = ""
        usage_info = None
        
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                result_text += content
            if hasattr(chunk, 'usage') and chunk.usage:
                usage_info = chunk.usage
        
        return {
            "success": True,
            "evaluation": result_text,
            "model": MODEL,
            "usage": {
                "prompt_tokens": usage_info.prompt_tokens if usage_info else 0,
                "completion_tokens": usage_info.completion_tokens if usage_info else 0,
                "total_tokens": usage_info.total_tokens if usage_info else 0,
            } if usage_info else {}
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def main():
    """主函数"""
    print("=" * 60)
    print("🎤 Qwen3-Omni 口语测评测试")
    print("=" * 60)
    
    # 创建客户端
    client = create_client()
    print(f"✅ 已连接到百炼平台")
    print(f"📍 Base URL: {BASE_URL}")
    print(f"🤖 模型: {MODEL}")
    
    # ============================================
    # 测试用例 1: playing basketball.mp3
    # ============================================
    print("\n" + "=" * 60)
    print("📝 测试用例 1: playing basketball")
    print("=" * 60)
    
    audio_file = "playing basketball.mp3"
    
    if Path(audio_file).exists():
        result = evaluate_speaking(
            client=client,
            audio_path=audio_file,
            question="What do you like to do in your free time?",
            expected_answer="I like playing basketball in my free time.",
        )
        
        if result["success"]:
            print("\n📊 评测结果：")
            print("-" * 50)
            print(result["evaluation"])
            print("-" * 50)
            print(f"\n💰 Token 使用: {result['usage']}")
        else:
            print(f"\n❌ 评测失败: {result['error']}")
    else:
        print(f"⚠️ 音频文件不存在: {audio_file}")
    
    # ============================================
    # 测试用例 2: car.mp3
    # ============================================
    print("\n" + "=" * 60)
    print("📝 测试用例 2: car")
    print("=" * 60)
    
    audio_file = "car.mp3"
    
    if Path(audio_file).exists():
        result = evaluate_speaking(
            client=client,
            audio_path=audio_file,
            question="What can you see in the picture?",
            expected_answer="I can see a car.",
        )
        
        if result["success"]:
            print("\n📊 评测结果：")
            print("-" * 50)
            print(result["evaluation"])
            print("-" * 50)
            print(f"\n💰 Token 使用: {result['usage']}")
        else:
            print(f"\n❌ 评测失败: {result['error']}")
    else:
        print(f"⚠️ 音频文件不存在: {audio_file}")


def test_simple():
    """
    简单测试 - 只测试一个音频文件
    """
    print("🎤 Qwen3-Omni 简单测试")
    print("-" * 40)
    
    client = create_client()
    
    # 测试音频文件
    audio_file = "playing basketball.mp3"
    
    result = evaluate_speaking(
        client=client,
        audio_path=audio_file,
    )
    
    if result["success"]:
        print("\n📊 评测结果：")
        print(result["evaluation"])
    else:
        print(f"❌ 失败: {result['error']}")


if __name__ == "__main__":
    # 运行完整测试
    main()
    
    # 或运行简单测试
    # test_simple()

