"""
数据库模型
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class TestRecord(Base):
    """测试记录"""
    __tablename__ = "test_records"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String(100), index=True)
    level = Column(String(20))  # e.g., "level1"
    unit = Column(String(20))   # e.g., "unit1-3"
    total_score = Column(Float)  # 0-60
    star_rating = Column(Integer)  # 0-5
    
    # Gemini AI 评估的额外维度 (0-10分)
    fluency_score = Column(Float, default=0)  # 流畅度
    pronunciation_score = Column(Float, default=0)  # 发音
    confidence_score = Column(Float, default=0)  # 自信度
    
    # API 成本跟踪
    total_tokens = Column(Integer, default=0)  # 总token数
    api_cost = Column(Float, default=0.0)  # API调用成本（美元）
    
    created_at = Column(DateTime, default=datetime.utcnow)

    
    # 关系
    part_scores = relationship("PartScore", back_populates="test_record", cascade="all, delete-orphan")
    audio_files = relationship("AudioFile", back_populates="test_record", cascade="all, delete-orphan")


class PartScore(Base):
    """分项评分"""
    __tablename__ = "part_scores"

    id = Column(Integer, primary_key=True, index=True)
    test_record_id = Column(Integer, ForeignKey("test_records.id"))
    part_number = Column(Integer)  # 1, 2, or 3
    score = Column(Float)
    max_score = Column(Float)
    feedback = Column(Text)  # Gemini 的详细反馈
    correct_items = Column(Text)  # JSON 字符串存储正确项目
    incorrect_items = Column(Text)  # JSON 字符串存储错误项目
    
    # 关系
    test_record = relationship("TestRecord", back_populates="part_scores")


class AudioFile(Base):
    """音频文件记录"""
    __tablename__ = "audio_files"
    
    id = Column(Integer, primary_key=True, index=True)
    test_record_id = Column(Integer, ForeignKey('test_records.id'))
    part_number = Column(Integer)
    file_path = Column(String, nullable=True)  # 可为空，文件删除后设为None
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    deleted_at = Column(DateTime, nullable=True)  # 文件删除时间
    
    # 关系
    test_record = relationship("TestRecord", back_populates="audio_files")
