"""
课程知识库数据模块

包含 Level S 到 Level 9 的所有课程数据，用于报告解读生成。
"""

from .level_ls import LEVEL_LS
from .level_l0 import LEVEL_L0
from .level_l1 import LEVEL_L1
from .level_l2 import LEVEL_L2
from .level_l3 import LEVEL_L3
from .level_l4 import LEVEL_L4
from .level_l5 import LEVEL_L5
from .level_l6 import LEVEL_L6
from .level_l7 import LEVEL_L7
from .level_l8 import LEVEL_L8
from .level_l9 import LEVEL_L9

# 级别数据映射表
LEVEL_DATA = {
    "LS": LEVEL_LS,
    "L0": LEVEL_L0,
    "L1": LEVEL_L1,
    "L2": LEVEL_L2,
    "L3": LEVEL_L3,
    "L4": LEVEL_L4,
    "L5": LEVEL_L5,
    "L6": LEVEL_L6,
    "L7": LEVEL_L7,
    "L8": LEVEL_L8,
    "L9": LEVEL_L9,
}

# 级别顺序
LEVEL_ORDER = ["LS", "L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"]

# 级别分组（用于阶段描述）
LEVEL_GROUPS = {
    "启蒙级": ["LS", "L0"],
    "入门级": ["L1", "L2", "L3"],
    "初级": ["L4", "L5", "L6"],
    "中级": ["L7", "L8", "L9"],
}

# 课时数配置
LEVEL_LESSON_COUNT = {
    "LS": 148,
    "L0": 144,
    "L1": 144,
    "L2": 144,
    "L3": 144,
    "L4": 144,
    "L5": 144,
    "L6": 144,
    "L7": 48,
    "L8": 48,
    "L9": 48,
}

# 里程碑级别
MILESTONES = {
    "L3": {
        "name": "入门级毕业",
        "cefr": "A1",
        "description": "能用英语进行简单的自我介绍，听懂并回答日常基础问题，出国旅游时能进行基础的点餐问路交流",
    },
    "L6": {
        "name": "初级毕业",
        "cefr": "A2",
        "description": "能流利地讲述英文小故事，看英文动画片能听懂大部分对话",
    },
    "L9": {
        "name": "中级毕业",
        "cefr": "B1-B2",
        "description": "能用英语进行主题演讲和辩论，看英文电影基本不需要字幕",
    },
}

# 目标级别映射（当前级别 -> 推荐目标级别，跨3级规则）
TARGET_LEVEL_MAP = {
    "LS": "L2",
    "L0": "L3",
    "L1": "L4",
    "L2": "L5",
    "L3": "L6",
    "L4": "L7",
    "L5": "L8",
    "L6": "L9",
    "L7": "L9",  # L7及以上目标都是L9
    "L8": "L9",
    "L9": "L9",  # 已是最高级别
}


def get_level_data(level_code: str) -> dict:
    """
    根据级别代码获取级别数据
    
    Args:
        level_code: 级别代码，如 "L1", "LS" 等
        
    Returns:
        级别数据字典，如果级别不存在返回 None
    """
    # 标准化级别代码
    normalized = level_code.upper().replace("LEVEL ", "").replace("LEVEL", "").strip()
    return LEVEL_DATA.get(normalized)


def get_level_group(level_code: str) -> str:
    """
    根据级别代码获取所属阶段分组名称
    
    Args:
        level_code: 级别代码
        
    Returns:
        阶段名称，如 "启蒙级", "入门级" 等
    """
    normalized = level_code.upper().replace("LEVEL ", "").replace("LEVEL", "").strip()
    for group_name, levels in LEVEL_GROUPS.items():
        if normalized in levels:
            return group_name
    return "未知阶段"


def get_target_level(current_level: str) -> str:
    """
    根据当前级别获取推荐目标级别
    
    Args:
        current_level: 当前级别代码
        
    Returns:
        推荐目标级别代码
    """
    normalized = current_level.upper().replace("LEVEL ", "").replace("LEVEL", "").strip()
    return TARGET_LEVEL_MAP.get(normalized, "L9")


def calculate_lessons_needed(current_level: str, target_level: str = None) -> dict:
    """
    计算从当前级别到目标级别所需的课时
    
    注意：不包含当前级别的课时（因为学生已在当前级别学习）
    
    Args:
        current_level: 当前级别代码
        target_level: 目标级别代码，如果为 None 则使用推荐目标级别
        
    Returns:
        包含课时明细和总课时的字典
    """
    current = current_level.upper().replace("LEVEL ", "").replace("LEVEL", "").strip()
    
    if target_level is None:
        target = get_target_level(current)
    else:
        target = target_level.upper().replace("LEVEL ", "").replace("LEVEL", "").strip()
    
    if current not in LEVEL_ORDER or target not in LEVEL_ORDER:
        return {"details": [], "total": 0, "error": "无效的级别代码"}
    
    current_idx = LEVEL_ORDER.index(current)
    target_idx = LEVEL_ORDER.index(target)
    
    if target_idx <= current_idx:
        return {"details": [], "total": 0, "note": "目标级别必须高于当前级别"}
    
    # 计算从当前级别的下一级到目标级别（含）的课时
    details = []
    total = 0
    
    for i in range(current_idx + 1, target_idx + 1):
        level = LEVEL_ORDER[i]
        lessons = LEVEL_LESSON_COUNT[level]
        details.append({"level": level, "lessons": lessons})
        total += lessons
    
    return {
        "current_level": current,
        "target_level": target,
        "details": details,
        "total": total,
    }


def get_milestone_info(level_code: str) -> dict:
    """
    获取指定级别的里程碑信息（如果是里程碑级别）
    
    Args:
        level_code: 级别代码
        
    Returns:
        里程碑信息字典，如果不是里程碑级别返回 None
    """
    normalized = level_code.upper().replace("LEVEL ", "").replace("LEVEL", "").strip()
    return MILESTONES.get(normalized)


__all__ = [
    # 数据
    "LEVEL_DATA",
    "LEVEL_ORDER",
    "LEVEL_GROUPS",
    "LEVEL_LESSON_COUNT",
    "MILESTONES",
    "TARGET_LEVEL_MAP",
    # 单独的级别数据
    "LEVEL_LS",
    "LEVEL_L0",
    "LEVEL_L1",
    "LEVEL_L2",
    "LEVEL_L3",
    "LEVEL_L4",
    "LEVEL_L5",
    "LEVEL_L6",
    "LEVEL_L7",
    "LEVEL_L8",
    "LEVEL_L9",
    # 工具函数
    "get_level_data",
    "get_level_group",
    "get_target_level",
    "calculate_lessons_needed",
    "get_milestone_info",
]
