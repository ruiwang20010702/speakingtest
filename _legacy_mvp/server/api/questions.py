"""
题目相关 API
"""
from fastapi import APIRouter, HTTPException
import json
from pathlib import Path

router = APIRouter(prefix="/api/questions", tags=["questions"])

# 题库文件路径 (在 server 目录下)
QUESTIONS_DIR = Path(__file__).parent.parent
QUESTIONS_FILE = QUESTIONS_DIR / "test_questions_level1.json"


@router.get("/levels")
async def get_levels():
    """获取可用的级别列表"""
    return {
        "levels": [
            {"id": "level1", "name": "Level 1"}
            # 可以扩展更多级别
        ]
    }


@router.get("/{level}/{unit}")
async def get_questions(level: str, unit: str):
    """
    获取指定级别和单元的题目
    
    Args:
        level: 级别（如 level1）
        unit: 单元（如 unit1-3）
    
    Returns:
        题目数据
    """
    try:
        # 读取题库文件
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            questions_data = json.load(f)
        
        # 查找对应的 level
        level_data = None
        for lv in questions_data.get("levels", []):
            if lv.get("level_id") == level:
                level_data = lv
                break
        
        if not level_data:
            raise HTTPException(status_code=404, detail=f"Level {level} not found")
        
        # 查找对应的 section (unit)
        section_data = None
        for section in level_data.get("sections", []):
            if section.get("section_id") == unit:
                section_data = section
                break
        
        if not section_data:
            raise HTTPException(status_code=404, detail=f"Unit {unit} not found in {level}")
        
        return {
            "level": level,
            "level_name": level_data.get("level_name"),
            "unit": unit,
            "unit_name": section_data.get("section_name"),
            "parts": section_data.get("parts", [])
        }
    
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Questions file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Questions file format error")
