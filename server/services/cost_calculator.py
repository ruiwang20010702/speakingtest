"""
API成本计算工具
基于Gemini API定价计算token使用和成本
"""

# Gemini 2.5 Flash 定价（2024年12月 - 付费层级）
# 参考: https://ai.google.dev/gemini-api/docs/pricing?hl=zh-cn#gemini-2.5-flash
PRICE_PER_1K_INPUT_TOKENS_TEXT = 0.0003  # $0.30 per 1M tokens (文字/图片/视频)
PRICE_PER_1K_INPUT_TOKENS_AUDIO = 0.001  # $1.00 per 1M tokens (音频)
PRICE_PER_1K_OUTPUT_TOKENS = 0.0025      # $2.50 per 1M tokens (输出，包括思考token)


# 音频token计算（官方标准）
# 参考: https://ai.google.dev/gemini-api/docs/tokens?hl=zh-cn&lang=python#video-audio
TOKENS_PER_SECOND_AUDIO = 32  # 音频：每秒 32 个 token


def estimate_audio_duration(audio_bytes: int) -> float:
    """
    粗略估算音频时长（秒）
    基于常见的 webm/opus 编码（约16KB/秒）
    
    Args:
        audio_bytes: 音频文件大小（字节）
    
    Returns:
        音频时长（秒）
    """
    # WebM/Opus 音频大约 16KB/秒（取决于比特率）
    # 这是一个粗略估算，实际应该用音频库获取精确时长
    estimated_duration = audio_bytes / (16 * 1024)
    return max(1, estimated_duration)  # 至少1秒


def estimate_tokens(text: str, audio_bytes: int = 0) -> dict:
    """
    估算token数量（基于官方标准）
    
    Args:
        text: 文本内容（prompt）
        audio_bytes: 音频文件大小（字节）
    
    Returns:
        包含input和output token估算的字典
    """
    # 文本token估算（粗略估算：1个token约4个字符）
    text_tokens = len(text) // 4
    
    # 音频token估算（官方标准：每秒32个token）
    if audio_bytes > 0:
        audio_duration = estimate_audio_duration(audio_bytes)
        audio_tokens = int(audio_duration * TOKENS_PER_SECOND_AUDIO)
    else:
        audio_tokens = 0
        audio_duration = 0
    
    # 总输入token
    input_tokens = text_tokens + audio_tokens
    
    # 输出token估算（通常远少于输入，假设为输入的1/5）
    output_tokens = input_tokens // 5
    
    return {
        "text_tokens": text_tokens,      # 文本token（用于计算成本）
        "audio_tokens": audio_tokens,    # 音频token（用于计算成本）
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "audio_duration_seconds": audio_duration
    }


def calculate_cost(text_tokens: int, audio_tokens: int, output_tokens: int) -> float:
    """
    计算API调用成本（区分文本和音频定价）
    
    Args:
        text_tokens: 文本输入token数
        audio_tokens: 音频输入token数
        output_tokens: 输出token数
    
    Returns:
        成本（美元）
    """
    text_input_cost = (text_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS_TEXT
    audio_input_cost = (audio_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS_AUDIO
    output_cost = (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    return text_input_cost + audio_input_cost + output_cost



def format_cost(cost_usd: float) -> str:
    """
    格式化成本为人类可读字符串
    
    Args:
        cost_usd: 成本（美元）
    
    Returns:
        格式化的字符串
    """
    if cost_usd < 0.01:
        # 小于1美分，显示为毫美分
        return f"${cost_usd * 1000:.2f} mills"
    else:
        return f"${cost_usd:.4f}"
