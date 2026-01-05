"""
评分 API
支持两种评测引擎：讯飞语音评测（专业）和 Gemini AI（通用）
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from typing import List
from pathlib import Path

from database import get_db
from models import TestRecord, PartScore, AudioFile
from schemas import TestResultResponse, PartScoreResponse
from services.gemini_scorer import evaluate_part1, calculate_star_rating
from services.part3_evaluator import evaluate_part3_single_question
from services.xfyun_scorer import (
    evaluate_words_with_xfyun, 
    evaluate_part2_all_with_xfyun,
    is_xfyun_configured
)
from api.questions import QUESTIONS_FILE

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@router.post("/evaluate", response_model=TestResultResponse)
async def evaluate_test(
    student_name: str = Form(...),
    level: str = Form(...),
    unit: str = Form(...),
    part1_audio: UploadFile = File(...),
    part2_audio: UploadFile = File(...),  # Part 2 问答: 一个音频文件包含所有12个问题的回答
    db: Session = Depends(get_db)
):
    """
    评估学生的口语测试
    
    测试包含两个部分：
    - Part 1: 词汇朗读
    - Part 2: 深度讨论（问答）
    
    Args:
        student_name: 学生姓名
        level: 级别（如 level1）
        unit: 单元（如 unit1-3）
        part1_audio: Part 1 音频文件（词汇朗读）
        part2_audio: Part 2 音频文件（问答，包含所有12个问题的回答）
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
        # 使用环境变量配置的绝对路径
        import os
        UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
        upload_dir = Path(UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 上传目录: {upload_dir.absolute()}")
        
        audio_files = {}
        audio_sizes = {}  # 记录音频文件大小
        
        # 保存 Part 1 词汇朗读
        file_path = upload_dir / f"{student_name}_{level}_{unit}_part1_{part1_audio.filename}"
        content = await part1_audio.read()
        with open(file_path, "wb") as f:
            f.write(content)
        audio_files[1] = str(file_path)
        audio_sizes[1] = len(content)
        
        # 保存 Part 2 音频文件（问答，一个文件包含所有12个问题）
        part2_file_path = upload_dir / f"{student_name}_{level}_{unit}_part2_{part2_audio.filename}"
        part2_content = await part2_audio.read()
        with open(part2_file_path, "wb") as f:
            f.write(part2_content)
        part2_audio_path = str(part2_file_path)
        part2_audio_size = len(part2_content)

        # 3. 评分 - 支持讯飞（专业）或 Gemini（通用）
        from services.cost_calculator import estimate_tokens, calculate_cost
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        total_input_tokens = 0
        total_output_tokens = 0
        scores = []
        
        # Part 1 数据准备（词汇朗读）
        part1_data = next(p for p in parts if p["part_id"] == 1)
        words_part1 = [item["word"] for item in part1_data["items"]]
        
        # Part 2 数据准备（问答 - 使用原来 Part 3 的数据结构）
        part2_data = next(p for p in parts if p["part_id"] == 2)
        dialogues_part2 = part2_data["dialogues"]
        
        # 检查是否使用讯飞评测
        use_xfyun = is_xfyun_configured()
        
        if use_xfyun:
            # ========== 使用讯飞语音评测 ==========
            print("🎯 使用讯飞语音评测引擎")
            
            async def evaluate_with_xfyun_async():
                """使用讯飞进行评测"""
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    # Part 1: 单词评测
                    part1_result = await loop.run_in_executor(
                        executor,
                        evaluate_words_with_xfyun,
                        audio_files[1],
                        words_part1
                    )
                    
                    # Part 2: 问答评测（所有问题）
                    questions = [d["question"] for d in dialogues_part2]
                    part2_result = await loop.run_in_executor(
                        executor,
                        evaluate_part2_all_with_xfyun,
                        part2_audio_path,
                        questions
                    )
                    
                    return part1_result, part2_result
            
            print("🚀 开始讯飞评测：Part 1 + Part 2...")
            xf_part1_result, xf_part2_result = await evaluate_with_xfyun_async()
            print("✅ 讯飞评测完成！")
            
            # 解析 Part 1 讯飞结果
            score1 = xf_part1_result.get("score", 0)
            result1 = {
                "feedback": xf_part1_result.get("feedback", ""),
                "correct_words": xf_part1_result.get("correct_words", []),
                "incorrect_words": xf_part1_result.get("incorrect_words", [])
            }
            
            scores.append({
                "part_number": 1,
                "score": score1,
                "max_score": 20,
                "feedback": result1.get("feedback", ""),
                "correct_items": result1.get("correct_words", []),
                "incorrect_items": result1.get("incorrect_words", [])
            })
            
            # 解析 Part 2 讯飞结果
            part2_total_score = xf_part2_result.get("total_score", 0)
            part2_question_results = xf_part2_result.get("question_scores", [])
            part2_overall_scores = xf_part2_result.get("summary", {
                "fluency_score": 8.0,
                "pronunciation_score": 7.0,
                "confidence_score": 8.0
            })
            part2_all_feedback = [xf_part2_result.get("feedback", "")]
            
            # 讯飞不消耗 Gemini tokens
            total_input_tokens = 0
            total_output_tokens = 0
            
            scores.append({
                "part_number": 2,
                "score": part2_total_score,
                "max_score": 24,
                "feedback": "\n".join(part2_all_feedback),
                "correct_items": [],
                "incorrect_items": []
            })
            
        else:
            # ========== 使用 Gemini AI 评测 ==========
            print("🤖 使用 Gemini AI 评测引擎")
            
            # Part 1 评估函数（异步包装）
            async def evaluate_part_async(part_num, audio_path, audio_size, eval_func, *args):
                """异步评估Part 1"""
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    score, result = await loop.run_in_executor(executor, eval_func, audio_path, *args)
                return part_num, score, result, audio_size
            
            # 启动 Part 1 评估任务
            part1_task = evaluate_part_async(1, audio_files[1], audio_sizes[1], evaluate_part1, words_part1)
            
            # Part 2 评估任务（所有12个问题使用一个音频文件）
            from services.part3_evaluator import evaluate_part2_all
            
            async def evaluate_part2_async(audio_path, audio_size, dialogues):
                """异步评估Part 2的所有12个问题"""
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    total_score, question_results, overall_scores = await loop.run_in_executor(
                        executor,
                        evaluate_part2_all,
                        audio_path,
                        dialogues
                    )
                
                # 计算tokens
                tokens = estimate_tokens("", audio_size)
                
                return {
                    "total_score": total_score,
                    "question_results": question_results,
                    "overall_scores": overall_scores,
                    "tokens": tokens
                }
            
            # 创建 Part 2 任务（所有12个问题）
            part2_task = evaluate_part2_async(part2_audio_path, part2_audio_size, dialogues_part2)
            
            # 🚀 并发：Part 1 + Part 2 = 共2个任务同时执行
            print("🚀 开始 Gemini 并发评分：Part 1 + Part 2...")
            all_results = await asyncio.gather(part1_task, part2_task)
            print("✅ Gemini 评分完成！")
            
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
            part2_result = all_results[1]
            part2_question_results = part2_result["question_results"]
            part2_total_score = part2_result["total_score"]
            part2_overall_scores = part2_result["overall_scores"]
            part2_all_feedback = [f"Q{r.get('question_num', i+1)}: {r.get('feedback', '')}" for i, r in enumerate(part2_question_results)]
            
            # Part 1 token估算（使用音频大小）
            from services.gemini_scorer import create_part1_prompt
            part1_prompt = create_part1_prompt(words_part1)
            part1_tokens = estimate_tokens(part1_prompt, audio_sizes[1])
            total_input_tokens += part1_tokens["input_tokens"]
            total_output_tokens += part1_tokens["output_tokens"]

            # Part 2 token累加
            total_input_tokens += part2_result["tokens"]["input_tokens"]
            total_output_tokens += part2_result["tokens"]["output_tokens"]
            
            scores.append({
                "part_number": 2,
                "score": part2_total_score,
                "max_score": 24,
                "feedback": "\n".join(part2_all_feedback),
                "correct_items": [],
                "incorrect_items": []
            })

        
        # 4. 计算总分和星级（Part 1: 20分 + Part 2: 24分 = 44分满分）
        total_score = score1 + part2_total_score
        star_rating = calculate_star_rating(total_score)

        
        # 从 Part 2 整体评分中提取流畅度等评估
        fluency_score = part2_overall_scores.get("fluency_score", 8.0)
        pronunciation_score = part2_overall_scores.get("pronunciation_score", 7.0)
        confidence_score = part2_overall_scores.get("confidence_score", 8.0)

        
        # 6. 计算API成本（区分文本token和音频token）
        # token已经在前面累加完成，直接计算成本
        total_text_tokens = 0
        total_audio_tokens = 0
        
        # Part 1 音频token估算
        total_audio_tokens += int((audio_sizes[1] / (16 * 1024)) * 32)
        
        # Part 2 音频token
        total_audio_tokens += int((part2_audio_size / (16 * 1024)) * 32)
        
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
        saved_audio_paths = []  # 收集所有音频路径用于清理
        
        # Part 1 词汇录音
        for part_num, file_path in audio_files.items():
            audio_record = AudioFile(
                test_record_id=test_record.id,
                part_number=part_num,
                file_path=file_path,
                file_size=audio_sizes.get(part_num, 0)
            )
            db.add(audio_record)
            saved_audio_paths.append(file_path)
        
        # Part 2 问答音频文件
        audio_record = AudioFile(
            test_record_id=test_record.id,
            part_number=2,  # Part 2
            file_path=part2_audio_path,
            file_size=part2_audio_size
        )
        db.add(audio_record)
        saved_audio_paths.append(part2_audio_path)
        
        db.commit()
        db.refresh(test_record)
        
        # 🗑️ 调度文件清理任务（1小时后删除录音）
        from services.file_cleanup import cleanup_service
        cleanup_service.schedule_cleanup(test_record.id, saved_audio_paths)
        
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
