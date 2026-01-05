"""
讯飞语音评测评分服务
使用讯飞 WebAPI 进行专业语音评测
"""
from typing import Dict, List, Tuple
from services.xfyun_client import get_xfyun_client


def evaluate_words_with_xfyun(audio_path: str, words: List[str]) -> Dict:
    """
    使用讯飞评测 Part 1 单词朗读
    
    Args:
        audio_path: 音频文件路径
        words: 需要朗读的单词列表
    
    Returns:
        评测结果
    """
    client = get_xfyun_client()
    if client is None:
        return {
            "error": "讯飞客户端未配置",
            "score": 0,
            "details": []
        }
    
    try:
        # 将单词列表拼接成句子进行评测
        # 讯飞对于单词列表，可以用空格分隔作为句子评测
        text = " ".join(words)
        
        print(f"📊 讯飞评测 Part 1: {len(words)} 个单词")
        
        result = client.evaluate_audio(
            audio_path=audio_path,
            text=text,
            category="read_sentence",  # 用句子模式评测单词序列
            language="en_us"
        )
        
        if result["status"] == "error":
            print(f"❌ 讯飞评测失败: {result['error']}")
            return {
                "error": result["error"],
                "score": 0,
                "details": []
            }
        
        # 解析评测数据
        data = result.get("data", {})
        
        # 计算单词正确数
        details = data.get("details", [])
        correct_count = 0
        incorrect_words = []
        correct_words = []
        word_results = []
        
        for i, detail in enumerate(details):
            word = detail.get("content", "")
            score = detail.get("total_score", 0)
            dp_message = detail.get("dp_message", "0")
            
            # 评分>=60 且没有错误标记视为正确
            is_correct = score >= 60 and dp_message == "0"
            
            if is_correct:
                correct_count += 1
                correct_words.append(word)
            else:
                incorrect_words.append(word)
            
            word_results.append({
                "word": word,
                "correct": is_correct,
                "score": score,
                "dp_message": _get_dp_message_text(dp_message)
            })
        
        return {
            "score": correct_count,
            "total": len(words),
            "correct_words": correct_words,
            "incorrect_words": incorrect_words,
            "word_results": word_results,
            "accuracy_score": data.get("accuracy_score", 0),
            "fluency_score": data.get("fluency_score", 0),
            "feedback": _generate_part1_feedback(word_results, data)
        }
        
    except Exception as e:
        print(f"❌ 讯飞评测异常: {str(e)}")
        return {
            "error": str(e),
            "score": 0,
            "details": []
        }


def evaluate_sentence_with_xfyun(audio_path: str, question: str, 
                                  question_index: int = 0) -> Dict:
    """
    使用讯飞评测 Part 2 口语回答
    
    注意：讯飞语音评测主要针对朗读类评测，对于自由回答类问题
    我们评测流利度和发音准确性，而不是内容
    
    Args:
        audio_path: 音频文件路径
        question: 问题文本（用于参考）
        question_index: 问题序号
    
    Returns:
        评测结果
    """
    client = get_xfyun_client()
    if client is None:
        return {
            "error": "讯飞客户端未配置",
            "scores": {"pronunciation": 0, "fluency": 0}
        }
    
    try:
        # 对于自由回答，我们使用篇章模式进行评测
        # 讯飞会评测发音准确度和流利度
        # 由于是自由回答，我们设置一个通用的评测文本
        
        print(f"📊 讯飞评测 Part 2 问题 {question_index + 1}")
        
        # 对于自由回答，讯飞需要知道学生应该说什么
        # 但由于是开放式回答，我们使用"自由说"模式
        # 讯飞的 read_chapter 模式可以评测较长的内容
        
        # 注意：讯飞评测要求有参考文本，对于自由回答场景
        # 我们可以设置一个宽松的参考或使用语音转写后再评测
        # 这里我们使用问题作为参考文本的一部分
        
        result = client.evaluate_audio(
            audio_path=audio_path,
            text=question,  # 使用问题作为参考
            category="read_sentence",
            language="en_us"
        )
        
        if result["status"] == "error":
            print(f"❌ 讯飞评测失败: {result['error']}")
            return {
                "error": result["error"],
                "scores": {"pronunciation": 0, "fluency": 0}
            }
        
        data = result.get("data", {})
        
        # 从评测结果提取分数（讯飞分数通常是0-100）
        # 我们需要转换为0-4或0-2的量表
        accuracy = data.get("accuracy_score", 0)  # 准确度 0-100
        fluency = data.get("fluency_score", 0)    # 流利度 0-100
        total = data.get("total_score", 0)        # 总分 0-100
        
        # 转换为 0-2 量表（Part 2 每项满分2分）
        pronunciation_score = round((accuracy / 100) * 2, 1)
        fluency_score = round((fluency / 100) * 2, 1)
        
        return {
            "scores": {
                "pronunciation": pronunciation_score,
                "fluency": fluency_score
            },
            "raw_scores": {
                "accuracy": accuracy,
                "fluency": fluency,
                "total": total
            },
            "details": data.get("details", []),
            "feedback": _generate_part2_feedback(accuracy, fluency)
        }
        
    except Exception as e:
        print(f"❌ 讯飞评测异常: {str(e)}")
        return {
            "error": str(e),
            "scores": {"pronunciation": 0, "fluency": 0}
        }


def evaluate_part2_all_with_xfyun(audio_path: str, questions: List[str]) -> Dict:
    """
    使用讯飞评测整个 Part 2 音频（所有问题一次录音）
    
    Args:
        audio_path: 音频文件路径
        questions: 所有问题列表
    
    Returns:
        评测结果
    """
    client = get_xfyun_client()
    if client is None:
        return {
            "error": "讯飞客户端未配置",
            "total_score": 0,
            "question_scores": []
        }
    
    try:
        print(f"📊 讯飞评测 Part 2: {len(questions)} 个问题的综合回答")
        
        # 将所有问题作为参考文本
        combined_text = " ".join(questions)
        
        result = client.evaluate_audio(
            audio_path=audio_path,
            text=combined_text,
            category="read_chapter",  # 使用篇章模式
            language="en_us"
        )
        
        if result["status"] == "error":
            print(f"❌ 讯飞评测失败: {result['error']}")
            return {
                "error": result["error"],
                "total_score": 0,
                "question_scores": []
            }
        
        data = result.get("data", {})
        
        # 获取整体评分
        accuracy = data.get("accuracy_score", 0)
        fluency = data.get("fluency_score", 0)
        total = data.get("total_score", 0)
        
        # 每个问题的分数（平均分配）
        # Part 2 每个问题最高2分，共12个问题 = 24分
        per_question_max = 2.0
        per_question_score = round((total / 100) * per_question_max, 1)
        
        question_scores = []
        for i, q in enumerate(questions):
            question_scores.append({
                "question_index": i,
                "question": q,
                "score": per_question_score,
                "pronunciation": round((accuracy / 100) * 2, 1),
                "fluency": round((fluency / 100) * 2, 1)
            })
        
        total_score = per_question_score * len(questions)
        
        return {
            "total_score": total_score,
            "question_scores": question_scores,
            "raw_scores": {
                "accuracy": accuracy,
                "fluency": fluency,
                "total": total
            },
            "feedback": _generate_part2_overall_feedback(accuracy, fluency, len(questions)),
            "summary": {
                "average_pronunciation": round((accuracy / 100) * 2, 1),
                "average_fluency": round((fluency / 100) * 2, 1)
            }
        }
        
    except Exception as e:
        print(f"❌ 讯飞评测异常: {str(e)}")
        return {
            "error": str(e),
            "total_score": 0,
            "question_scores": []
        }


def _get_dp_message_text(dp_message: str) -> str:
    """
    将讯飞的 dp_message 代码转换为文字描述
    """
    messages = {
        "0": "正确",
        "16": "漏读",
        "32": "增读",
        "64": "回读",
        "128": "替换"
    }
    return messages.get(dp_message, "未知")


def _generate_part1_feedback(word_results: List[Dict], data: Dict) -> str:
    """
    生成 Part 1 的反馈
    """
    correct_count = sum(1 for w in word_results if w.get("correct", False))
    total_count = len(word_results)
    accuracy = data.get("accuracy_score", 0)
    
    if correct_count == total_count:
        return f"发音表现优秀！所有 {total_count} 个单词都发音正确。准确度评分: {accuracy:.0f}/100"
    elif correct_count >= total_count * 0.8:
        incorrect = [w["word"] for w in word_results if not w.get("correct", False)]
        return f"发音表现良好！{correct_count}/{total_count} 个单词正确。需要注意的单词: {', '.join(incorrect)}。准确度评分: {accuracy:.0f}/100"
    elif correct_count >= total_count * 0.5:
        return f"发音有待提高。{correct_count}/{total_count} 个单词正确。建议多练习发音基础。准确度评分: {accuracy:.0f}/100"
    else:
        return f"需要加强练习。只有 {correct_count}/{total_count} 个单词正确。建议从基础音标开始学习。准确度评分: {accuracy:.0f}/100"


def _generate_part2_feedback(accuracy: float, fluency: float) -> str:
    """
    生成 Part 2 单题的反馈
    """
    avg = (accuracy + fluency) / 2
    
    if avg >= 80:
        return "口语表现优秀，发音清晰流利。"
    elif avg >= 60:
        return "口语表现良好，可以注意提高流利度。"
    elif avg >= 40:
        return "口语有待提高，建议多练习日常对话。"
    else:
        return "需要加强练习，建议从基础句型开始。"


def _generate_part2_overall_feedback(accuracy: float, fluency: float, 
                                      question_count: int) -> str:
    """
    生成 Part 2 整体反馈
    """
    avg = (accuracy + fluency) / 2
    
    feedback_parts = []
    
    # 总体评价
    if avg >= 80:
        feedback_parts.append(f"您完成了全部 {question_count} 个问题的回答，整体表现优秀！")
    elif avg >= 60:
        feedback_parts.append(f"您完成了 {question_count} 个问题的回答，整体表现良好。")
    elif avg >= 40:
        feedback_parts.append(f"您回答了 {question_count} 个问题，有一定进步空间。")
    else:
        feedback_parts.append(f"完成了 {question_count} 个问题，建议继续加强练习。")
    
    # 发音评价
    if accuracy >= 70:
        feedback_parts.append("发音准确度较高。")
    else:
        feedback_parts.append("可以注意提高发音准确度。")
    
    # 流利度评价
    if fluency >= 70:
        feedback_parts.append("表达流利自然。")
    else:
        feedback_parts.append("建议提高表达的流利度，减少停顿。")
    
    return " ".join(feedback_parts)


# 用于检测是否配置了讯飞
def is_xfyun_configured() -> bool:
    """检查讯飞是否已配置"""
    client = get_xfyun_client()
    return client is not None

