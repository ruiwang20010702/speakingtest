"""
评分 API
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from typing import List
from pathlib import Path

from database import get_db
from models import TestRecord, PartScore, AudioFile
from schemas import TestResultResponse, PartScoreResponse
from services.gemini_scorer import evaluate_part1, evaluate_part2, evaluate_part3, calculate_star_rating
from services.part3_evaluator import evaluate_part3_single_question
from api.questions import QUESTIONS_FILE

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@router.post("/evaluate", response_model=TestResultResponse)
async def evaluate_test(
    student_name: str = Form(...),
    level: str = Form(...),
    unit: str = Form(...),
    part1_audio: UploadFile = File(...),
    part2_audio: UploadFile = File(...),
    # Part 3: 接收12个音频文件
    part3_audio_1: UploadFile = File(...),
    part3_audio_2: UploadFile = File(...),
    part3_audio_3: UploadFile = File(...),
    part3_audio_4: UploadFile = File(...),
    part3_audio_5: UploadFile = File(...),
    part3_audio_6: UploadFile = File(...),
    part3_audio_7: UploadFile = File(...),
    part3_audio_8: UploadFile = File(...),
    part3_audio_9: UploadFile = File(...),
    part3_audio_10: UploadFile = File(...),
    part3_audio_11: UploadFile = File(...),
    part3_audio_12: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    评估学生的口语测试
    
    Args:
        student_name: 学生姓名
        level: 级别（如 level1）
        unit: 单元（如 unit1-3）
        part1_audio: Part 1 音频文件
        part2_audio: Part 2 音频文件
        part3_audio_1 to part3_audio_12: Part 3的12个问题音频文件
        db: 数据库会话
    
    Returns:
        测试结果
    """
    try:
        # 1. 读取题目数据
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            questions_data = json.load(f)
        
        # 查找对应的题目
        level_data = next((lv for lv in questions_data["levels"] if lv["level_id"] == level), None)
        if not level_data:
            raise HTTPException(status_code=404, detail=f"Level {level} not found")
        
        section_data = next((s for s in level_data["sections"] if s["section_id"] == unit), None)
        if not section_data:
            raise HTTPException(status_code=404, detail=f"Unit {unit} not found")
        
        parts = section_data["parts"]
        
        #2. 保存音频文件并记录大小用于成本计算
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)
        
        audio_files = {}
        audio_sizes = {}  # 记录音频文件大小
        
        # 保存 Part 1 和 Part 2
        for part_num, audio_file in enumerate([part1_audio, part2_audio], 1):
            file_path = upload_dir / f"{student_name}_{level}_{unit}_part{part_num}_{audio_file.filename}"
            content = await audio_file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            audio_files[part_num] = str(file_path)
            audio_sizes[part_num] = len(content)
        
        # 保存 Part 3 的12个音频文件
        part3_audio_files = [
            part3_audio_1, part3_audio_2, part3_audio_3, part3_audio_4,
            part3_audio_5, part3_audio_6, part3_audio_7, part3_audio_8,
            part3_audio_9, part3_audio_10, part3_audio_11, part3_audio_12
        ]
        
        part3_files = {}
        part3_sizes = {}
        for q_num, audio_file in enumerate(part3_audio_files, 1):
            file_path = upload_dir / f"{student_name}_{level}_{unit}_part3_q{q_num}_{audio_file.filename}"
            content = await audio_file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            part3_files[q_num] = str(file_path)
            part3_sizes[q_num] = len(content)

        # 3. 使用 Gemini评分（全局并发 - Part 1/2/3 + Part 3的12个问题）
        from services.cost_calculator import estimate_tokens, calculate_cost
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        total_input_tokens = 0
        total_output_tokens = 0
        scores = []
        
        # Part 1/2 评估函数（异步包装）
        async def evaluate_part_async(part_num, audio_path, audio_size, eval_func, *args):
            """异步评估Part 1或Part 2"""
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                score, result = await loop.run_in_executor(executor, eval_func, audio_path, *args)
            return part_num, score, result, audio_size
        
        # Part 1 数据准备
        part1_data = next(p for p in parts if p["part_id"] == 1)
        words_part1 = [item["word"] for item in part1_data["items"]]
        
        # Part 2 数据准备
        part2_data = next(p for p in parts if p["part_id"] == 2)
        words_part2 = [item["word"] for item in part2_data.get("words", [])]
        sentences_part2 = [item["text"] for item in part2_data.get("sentences", [])]
        
        # Part 3 数据准备
        part3_data = next(p for p in parts if p["part_id"] == 3)
        dialogues_part3 = part3_data["dialogues"]
        
        # 启动 Part 1/2 评估任务
        part1_task = evaluate_part_async(1, audio_files[1], audio_sizes[1], evaluate_part1, words_part1)
        part2_task = evaluate_part_async(2, audio_files[2], audio_sizes[2], evaluate_part2, words_part2, sentences_part2)
        
        # Part 3的12个问题评估任务
        async def evaluate_question_async(q_num, dialogue, audio_path, audio_size):
            """异步评估单个问题"""
            single_q_prompt = f"""你是专业的英语口语评估专家。学生需要回答问题：
Teacher: {dialogue['teacher']}
Expected answers: {' / '.join(dialogue.get('student_options', []))}

评分标准：回答正确且完整2分，部分正确1分，错误0分。

返回JSON：
{{
  "score": 得分（0-2）,
  "student_answer": "学生的回答",
  "feedback": "评价",
  "fluency_score": 流畅度（0-10）,
  "pronunciation_score": 发音（0-10）,
  "confidence_score": 自信度（0-10）
}}
"""
            q_tokens = estimate_tokens(single_q_prompt, audio_size)
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                score_q, result_q = await loop.run_in_executor(
                    executor,
                    evaluate_part3_single_question,
                    audio_path,
                    dialogue,
                    q_num
                )
            
            return {
                "question_num": q_num,
                "score": score_q,
               "student_answer": result_q.get("student_answer", ""),
                "feedback": result_q.get("feedback", ""),
                "fluency_score": result_q.get("fluency_score"),
                "pronunciation_score": result_q.get("pronunciation_score"),
                "confidence_score": result_q.get("confidence_score"),
                "tokens": q_tokens
            }
        
        # 创建Part 3的12个任务
        part3_tasks = []
        for q_num in range(1, 13):
            dialogue = dialogues_part3[q_num - 1]
            task = evaluate_question_async(q_num, dialogue, part3_files[q_num], part3_sizes[q_num])
            part3_tasks.append(task)
        
        # 🚀 全局并发：Part 1 + Part 2 + Part 3的12个问题 = 共14个任务同时执行
        print("🚀 开始并发评分：Part 1 + Part 2 + Part 3（12个问题）...")
        all_results = await asyncio.gather(part1_task, part2_task, *part3_tasks)
        print("✅ 并发评分完成！")
        
        # 解析 Part 1 结果
        part1_num, score1, result1, _ = all_results[0]
        scores.append({
            "part_number": 1,
            "score": score1,
            "max_score": 20,
            "feedback": result1.get("feedback", ""),
            "correct_items": result1.get("correct_words", []),
            "incorrect_items": result1.get("incorrect_words", [])
        })
        
        # 解析 Part 2 结果
        part2_num, score2, result2, _ = all_results[1]
        scores.append({
            "part_number": 2,
            "score": score2,
            "max_score": 16,
            "feedback": result2.get("feedback", ""),
            "correct_items": result2.get("correct_words", []),
            "incorrect_items": result2.get("incorrect_words", [])
        })
        
        # 解析 Part 3 结果（从索引2开始的12个结果）
        part3_question_results = all_results[2:]
        part3_total_score = sum(r["score"] for r in part3_question_results)
        part3_all_feedback = [f"Q{r['question_num']}: {r['feedback']}" for r in part3_question_results]
        
        # Part 1/2 token估算（使用音频大小）
        from services.gemini_scorer import create_part1_prompt, create_part2_prompt
        part1_prompt = create_part1_prompt(words_part1)
        part1_tokens = estimate_tokens(part1_prompt, audio_sizes[1])
        total_input_tokens += part1_tokens["input_tokens"]
        total_output_tokens += part1_tokens["output_tokens"]
        
        part2_prompt = create_part2_prompt(words_part2, sentences_part2)
        part2_tokens = estimate_tokens(part2_prompt, audio_sizes[2])
        total_input_tokens += part2_tokens["input_tokens"]
        total_output_tokens += part2_tokens["output_tokens"]

        for result in part3_question_results:
            total_input_tokens += result["tokens"]["input_tokens"]
            total_output_tokens += result["tokens"]["output_tokens"]
        
        scores.append({
            "part_number": 3,
            "score": part3_total_score,
            "max_score": 24,
            "feedback": "\n".join(part3_all_feedback),
            "correct_items": [],
            "incorrect_items": []
        })

        
        # 4. 计算总分和星级
        total_score = score1 + score2 + part3_total_score
        star_rating = calculate_star_rating(total_score)

        
        # 从所有Part 3问题结果中提取流畅度等评估（计算平均值）
        fluency_scores = [r.get("fluency_score") for r in part3_question_results if r.get("fluency_score")]
        pronunciation_scores = [r.get("pronunciation_score") for r in part3_question_results if r.get("pronunciation_score")]
        confidence_scores = [r.get("confidence_score") for r in part3_question_results if r.get("confidence_score")]
        
        fluency_score = sum(fluency_scores) / len(fluency_scores) if fluency_scores else 8.0
        pronunciation_score = sum(pronunciation_scores) / len(pronunciation_scores) if pronunciation_scores else 7.0
        confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 8.0

        
        # 6. 计算API成本（区分文本token和音频token）
        # token已经在前面累加完成，直接计算成本
        total_text_tokens = 0
        total_audio_tokens = 0
        
        # 简化估算文本和音频token
        for audio_size in [audio_sizes[1], audio_sizes[2]]:
            total_audio_tokens += int((audio_size / (16 * 1024)) * 32)  # 音频token估算
        
        # Part 3音频token已在循环中累加
        for q_num in range(1, 13):
            total_audio_tokens += int((part3_sizes[q_num] / (16 * 1024)) * 32)
        
        # 文本token粗略估算
        total_text_tokens = total_input_tokens - total_audio_tokens
        if total_text_tokens < 0:
            total_text_tokens = total_input_tokens // 3  # 粗略估算

        
        total_tokens = total_input_tokens + total_output_tokens
        api_cost = calculate_cost(total_text_tokens, total_audio_tokens, total_output_tokens)
        
        print(f"💰 成本统计: {total_tokens} tokens, ${api_cost:.4f}")
        print(f"   文本: {total_text_tokens} tokens, 音频: {total_audio_tokens} tokens, 输出: {total_output_tokens} tokens")

        
        # 7. 保存到数据库
        test_record = TestRecord(
            student_name=student_name,
            level=level,
            unit=unit,
            total_score=total_score,
            star_rating=star_rating,
            fluency_score=fluency_score,
            pronunciation_score=pronunciation_score,
            confidence_score=confidence_score,
            total_tokens=total_tokens,
            api_cost=api_cost
        )
        db.add(test_record)
        db.flush()  # 获取 test_record.id
        
        # 保存分项评分
        for score_data in scores:
            part_score = PartScore(
                test_record_id=test_record.id,
                part_number=score_data["part_number"],
                score=score_data["score"],
                max_score=score_data["max_score"],
                feedback=score_data["feedback"],
                correct_items=json.dumps(score_data["correct_items"], ensure_ascii=False),
                incorrect_items=json.dumps(score_data["incorrect_items"], ensure_ascii=False)
            )
            db.add(part_score)
        
        # 保存音频文件记录
        for part_num, file_path in audio_files.items():
            audio_record = AudioFile(
                test_record_id=test_record.id,
                part_number=part_num,
                file_path=file_path,
                duration=0  # 可以后续添加音频时长检测
            )
            db.add(audio_record)
        
        db.commit()
        db.refresh(test_record)
        
        # 6. 返回结果
        return TestResultResponse(
            id=test_record.id,
            student_name=test_record.student_name,
            level=test_record.level,
            unit=test_record.unit,
            total_score=test_record.total_score,
            star_rating=test_record.star_rating,
            created_at=test_record.created_at,
            part_scores=[
                PartScoreResponse(
                    part_number=ps.part_number,
                    score=ps.score,
                    max_score=ps.max_score,
                    feedback=ps.feedback,
                    correct_items=json.loads(ps.correct_items) if ps.correct_items else [],
                    incorrect_items=json.loads(ps.incorrect_items) if ps.incorrect_items else []
                )
                for ps in test_record.part_scores
            ]
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"评分失败: {str(e)}")


@router.get("/history", response_model=List[TestResultResponse])
async def get_all_history(db: Session = Depends(get_db)):
    """
    获取所有学生的历史测试记录
    
    Args:
        db: 数据库会话
    
    Returns:
        所有测试记录列表
    """
    records = db.query(TestRecord).order_by(TestRecord.created_at.desc()).all()
    
    return [
        TestResultResponse(
            id=record.id,
            student_name=record.student_name,
            level=record.level,
            unit=record.unit,
            total_score=record.total_score,
            star_rating=record.star_rating,
            created_at=record.created_at,
            part_scores=[
                PartScoreResponse(
                    part_number=ps.part_number,
                    score=ps.score,
                    max_score=ps.max_score,
                    feedback=ps.feedback,
                    correct_items=json.loads(ps.correct_items) if ps.correct_items else [],
                    incorrect_items=json.loads(ps.incorrect_items) if ps.incorrect_items else []
                )
                for ps in record.part_scores
            ]
        )
        for record in records
    ]


@router.get("/history/{student_name}", response_model=List[TestResultResponse])
async def get_history(student_name: str, db: Session = Depends(get_db)):
    """
    获取学生的历史测试记录
    
    Args:
        student_name: 学生姓名
        db: 数据库会话
    
    Returns:
        测试记录列表
    """
    records = db.query(TestRecord).filter(
        TestRecord.student_name == student_name
    ).order_by(TestRecord.created_at.desc()).all()
    
    return [
        TestResultResponse(
            id=record.id,
            student_name=record.student_name,
            level=record.level,
            unit=record.unit,
            total_score=record.total_score,
            star_rating=record.star_rating,
            created_at=record.created_at,
            part_scores=[
                PartScoreResponse(
                    part_number=ps.part_number,
                    score=ps.score,
                    max_score=ps.max_score,
                    feedback=ps.feedback,
                    correct_items=json.loads(ps.correct_items) if ps.correct_items else [],
                    incorrect_items=json.loads(ps.incorrect_items) if ps.incorrect_items else []
                )
                for ps in record.part_scores
            ]
        )
        for record in records
    ]


@router.get("/result/{result_id}", response_model=TestResultResponse)
async def get_result_by_id(result_id: int, db: Session = Depends(get_db)):
    """
    根据 ID 获取单个测试结果
    
    Args:
        result_id: 测试记录 ID
        db: 数据库会话
    
    Returns:
        测试结果
    """
    record = db.query(TestRecord).filter(TestRecord.id == result_id).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="测试记录不存在")
    
    return TestResultResponse(
        id=record.id,
        student_name=record.student_name,
        level=record.level,
        unit=record.unit,
        total_score=record.total_score,
        star_rating=record.star_rating,
        created_at=record.created_at,
        part_scores=[
            PartScoreResponse(
                part_number=ps.part_number,
                score=ps.score,
                max_score=ps.max_score,
                feedback=ps.feedback,
                correct_items=json.loads(ps.correct_items) if ps.correct_items else [],
                incorrect_items=json.loads(ps.incorrect_items) if ps.incorrect_items else []
            )
            for ps in record.part_scores
        ]
    )
