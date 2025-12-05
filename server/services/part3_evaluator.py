"""
单个Part 3问题评估函数
"""
from services.gemini_client import GeminiClient
from services.gemini_scorer import parse_gemini_response
from services.retry_decorator import retry_on_error

@retry_on_error(max_retries=3, delay=2.0, backoff=2.0)
def evaluate_part3_single_question(audio_path: str, dialogue: dict, question_num: int):
    """
    评估Part 3的单个问题（带重试机制）
    
    Args:
        audio_path: 音频文件路径
        dialogue: 问题对话数据
        question_num: 问题编号
    
    Returns:
        (score, result_dict)
    """
    prompt = f"""你是专业的英语口语评估专家。请评估学生对这个问题的回答。

**问题 {question_num}**：
Teacher: {dialogue['teacher']}
Expected answers: {' / '.join(dialogue.get('student_options', []))}

**评分标准**：
- 回答完整且正确：2分
- 部分正确或不完整：1分
- 无法回答或完全错误：0分

请返回JSON格式：
{{
  "score": 得分（0-2的数字）,
  "student_answer": "学生实际说的内容",
  "feedback": "简短评价",
  "fluency_score": 流畅度（0-10，可选）,
  "pronunciation_score": 发音（0-10，可选）,
  "confidence_score": 自信度（0-10，可选）
}}

注意：只返回JSON，不要包含其他文字。
"""
    
    client = GeminiClient()
    response_text = client.analyze_audio_from_path(audio_path, prompt)
    result = parse_gemini_response(response_text)
    
    score = result.get("score", 0)
    return score, result
