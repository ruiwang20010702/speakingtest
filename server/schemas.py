"""
Pydantic 数据模型
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class PartScoreResponse(BaseModel):
    """分项评分响应"""
    part_number: int
    score: float
    max_score: float
    feedback: str
    correct_items: List[str]
    incorrect_items: List[str]

    class Config:
        from_attributes = True


class TestResultResponse(BaseModel):
    """测试结果响应"""
    id: int
    student_name: str
    level: str
    unit: str
    total_score: float
    star_rating: int
    fluency_score: float = 0  # 流畅度 (0-10)
    pronunciation_score: float = 0  # 发音 (0-10)
    confidence_score: float = 0  # 自信度 (0-10)
    total_tokens: int = 0  # 总token数
    api_cost: float = 0.0  # API成本（美元）
    created_at: datetime
    part_scores: List[PartScoreResponse]

    class Config:
        from_attributes = True



class EvaluateRequest(BaseModel):
    """评分请求"""
    student_name: str
    level: str
    unit: str
    # 前端会上传三个音频文件，通过 FormData 发送


class QuestionResponse(BaseModel):
    """题目响应"""
    level: str
    unit: str
    sections: list  # 从 JSON 直接返回
