"""
单个Part 3问题评估函数
"""
from typing import List, Dict, Tuple
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


@retry_on_error(max_retries=3, delay=2.0, backoff=2.0)
def evaluate_part3_group(audio_path: str, dialogues: List[Dict], start_question_num: int) -> Tuple[float, List[Dict]]:
    """
    评估Part 3的一组问题（6个问题使用一个音频文件）（带重试机制）
    
    Args:
        audio_path: 音频文件路径
        dialogues: 问题对话列表（6个）
        start_question_num: 起始问题编号（1或7）
    
    Returns:
        (total_score, list_of_result_dicts)
    """
    # 构建包含所有6个问题的prompt
    questions_text = ""
    for i, dialogue in enumerate(dialogues):
        q_num = start_question_num + i
        questions_text += f"""
**问题 {q_num}**：
Teacher: {dialogue['teacher']}
Expected answers: {' / '.join(dialogue.get('student_options', []))}
"""

    prompt = f"""你是专业的英语口语评估专家。请评估学生对以下6个问题的回答。
学生在一个音频中依次回答了以下问题：

{questions_text}

**评分标准**（每个问题）：
- 回答完整且正确：2分
- 部分正确或不完整：1分
- 无法回答或完全错误：0分

请返回JSON格式，包含每个问题的评估结果：
{{
  "questions": [
    {{
      "question_num": {start_question_num},
      "score": 得分（0-2的数字）,
      "student_answer": "学生实际说的内容",
      "feedback": "简短评价"
    }},
    // ... 共6个问题
  ],
  "fluency_score": 整体流畅度（0-10）,
  "pronunciation_score": 整体发音（0-10）,
  "confidence_score": 整体自信度（0-10）
}}

注意：
1. 只返回JSON，不要包含其他文字
2. 请确保questions数组包含6个问题的评估结果，按顺序对应问题 {start_question_num} 到 {start_question_num + 5}
3. **重要**：feedback字段必须使用中文评价
4. student_answer字段必须保持学生说的英文原话
"""
    
    client = GeminiClient()
    response_text = client.analyze_audio_from_path(audio_path, prompt)
    result = parse_gemini_response(response_text)
    
    # 解析结果
    question_results = result.get("questions", [])
    
    # 如果返回的结果不完整，补充默认值
    if len(question_results) < 6:
        for i in range(len(question_results), 6):
            question_results.append({
                "question_num": start_question_num + i,
                "score": 0,
                "student_answer": "",
                "feedback": "未能识别回答"
            })
    
    # 添加整体评分到每个问题结果
    fluency_score = result.get("fluency_score", 7.0)
    pronunciation_score = result.get("pronunciation_score", 7.0)
    confidence_score = result.get("confidence_score", 7.0)
    
    for q_result in question_results:
        q_result["fluency_score"] = fluency_score
        q_result["pronunciation_score"] = pronunciation_score
        q_result["confidence_score"] = confidence_score
    
    total_score = sum(q.get("score", 0) for q in question_results)
    
    return total_score, question_results


@retry_on_error(max_retries=3, delay=2.0, backoff=2.0)
def evaluate_part2_all(audio_path: str, dialogues: List[Dict]) -> Tuple[float, List[Dict], Dict]:
    """
    评估Part 2的所有12个问题（使用一个音频文件）（带重试机制）
    
    Args:
        audio_path: 音频文件路径
        dialogues: 问题对话列表（12个）
    
    Returns:
        (total_score, list_of_result_dicts, overall_scores)
    """
    # 构建包含所有12个问题的prompt
    questions_text = ""
    for i, dialogue in enumerate(dialogues):
        q_num = i + 1
        questions_text += f"""
**问题 {q_num}**：
Teacher: {dialogue['teacher']}
Expected answers: {' / '.join(dialogue.get('student_options', []))}
"""

    prompt = f"""你是专业的英语口语评估专家。请评估学生对以下12个问题的回答。
学生在一个音频中依次回答了以下问题：

{questions_text}

**评分标准**（每个问题）：
- 回答完整且正确：2分
- 部分正确或不完整：1分
- 无法回答或完全错误：0分

请返回JSON格式，包含每个问题的评估结果：
{{
  "questions": [
    {{
      "question_num": 1,
      "score": 得分（0-2的数字）,
      "student_answer": "学生实际说的内容",
      "feedback": "简短评价"
    }},
    // ... 共12个问题
  ],
  "fluency_score": 整体流畅度（0-10）,
  "pronunciation_score": 整体发音（0-10）,
  "confidence_score": 整体自信度（0-10）
}}

注意：
1. 只返回JSON，不要包含其他文字
2. 请确保questions数组包含12个问题的评估结果，按顺序对应问题 1 到 12
3. **重要**：feedback字段必须使用中文评价
4. student_answer字段必须保持学生说的英文原话
"""
    
    client = GeminiClient()
    response_text = client.analyze_audio_from_path(audio_path, prompt)
    result = parse_gemini_response(response_text)
    
    # 解析结果
    question_results = result.get("questions", [])
    
    # 如果返回的结果不完整，补充默认值
    if len(question_results) < 12:
        for i in range(len(question_results), 12):
            question_results.append({
                "question_num": i + 1,
                "score": 0,
                "student_answer": "",
                "feedback": "未能识别回答"
            })
    
    # 获取整体评分
    overall_scores = {
        "fluency_score": result.get("fluency_score", 7.0),
        "pronunciation_score": result.get("pronunciation_score", 7.0),
        "confidence_score": result.get("confidence_score", 7.0)
    }
    
    total_score = sum(q.get("score", 0) for q in question_results)
    
    return total_score, question_results, overall_scores

