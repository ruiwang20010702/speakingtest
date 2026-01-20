"""
51Talk 课程知识库 - 逻辑层

包含课程体系配置、目标级别计算、课时计算、学习规划生成等核心逻辑。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Any
from .course_data import (
    LEVEL_DATA,
    LEVEL_ORDER,
    LEVEL_GROUPS,
    LEVEL_LESSON_COUNT,
    MILESTONES,
    TARGET_LEVEL_MAP,
    get_level_data,
    get_level_group,
    get_target_level,
    calculate_lessons_needed,
    get_milestone_info,
)


# ==================== 类型定义 ====================

@dataclass
class UnitStats:
    """单元统计信息"""
    vocab_count: int = 0              # 词汇量
    sentence_count: int = 0           # 句式量
    high_freq_word_count: int = 0     # 高频词量
    story_count: int = 0              # 价值观/绘本故事数量
    song_count: int = 0               # 主题儿歌数量
    phonics_count: int = 0            # 拼读/发音数量
    grammar_count: int = 0            # 语法点数量


@dataclass
class UnitInfo:
    """单元信息"""
    unit_number: int                  # 单元编号 (1-18)
    topic: str                        # 单元主题
    title: str = ""                   # 单元标题
    keywords: List[str] = field(default_factory=list)      # 核心词汇
    sentences: List[str] = field(default_factory=list)     # 重点句型
    high_freq_words: List[str] = field(default_factory=list)  # 高频词
    skills: List[str] = field(default_factory=list)        # 培养技能
    stats: Optional[UnitStats] = None                      # 单元统计数据
    curriculum_tags: List[str] = field(default_factory=list)  # 匹配新课标
    grammar: List[str] = field(default_factory=list)       # 语法点
    phonics: List[str] = field(default_factory=list)       # 自然拼读


CourseType = Literal["main", "professional", "review", "elective"]


@dataclass
class CoursePackage:
    """课程搭配信息"""
    course_name: str                  # 课程名称
    lesson_count: Any                 # 课时数量（可以是"不限"等文字）
    course_type: CourseType = "main"  # 课程类型


@dataclass
class LearningPath:
    """学习路线信息"""
    course_packages: List[CoursePackage] = field(default_factory=list)
    package_description: List[str] = field(default_factory=list)
    stage_achievements: List[str] = field(default_factory=list)
    recommended_books: List[str] = field(default_factory=list)


@dataclass
class SuccessCase:
    """优秀学员案例"""
    student_name: str                 # 学员化名
    start_age: int                    # 开始学习时的年龄
    start_level: str                  # 起始级别
    current_level: str                # 当前级别
    study_duration: str               # 学习时长
    lessons_per_week: int             # 每周上课频次
    achievements: List[str] = field(default_factory=list)  # 取得的成果
    parent_feedback: str = ""         # 家长反馈
    key_points: List[str] = field(default_factory=list)    # 关键成功要素


@dataclass
class MilestoneInfo:
    """里程碑信息"""
    name: str                         # 里程碑名称
    main_course_lessons: int          # 累计主修课课时
    cumulative_lessons: int           # 累计总课时（含推荐专业课）
    description: str                  # 能力描述
    abilities: List[str] = field(default_factory=list)  # 达到后孩子能做什么


# ==================== 里程碑配置（详细版） ====================

MILESTONES_DETAILED: Dict[str, MilestoneInfo] = {
    "L3": MilestoneInfo(
        name="入门级完成",
        main_course_lessons=724,   # LS(148) + L0(144) + L1(144) + L2(144) + L3(144)
        cumulative_lessons=868,    # 从零基础累计总课时（含自然拼读48 + 单元复习课等）
        description="具备基础对话交流能力，能进行简单的日常对话",
        abilities=[
            "在纯英文环境能应对日常对话",
            "系统学习自然拼读，为英语的读写打下坚实基础",
            "借助图片能读懂200词文章",
            "能进行三两句话的英文写作",
            "此时词汇量累计1000+"
        ]
    ),
    "L6": MilestoneInfo(
        name="初级完成",
        main_course_lessons=1156,  # 724 + L4(144) + L5(144) + L6(144)
        cumulative_lessons=1366,   # 从零基础累计总课时（含全能新概念等）
        description="阅读能力成型，表达技巧扎实，能读懂简单文章",
        abilities=[
            "能与老师进行自由的情景对话",
            "能表达个人观点和意见，并参与讨论",
            "能读懂常见阅读材料，根据不同阅读目运用不同的策略技巧",
            "能写完整的句子，根据图示写出简单的段落或大纲",
            "能围绕常见话题进行写作"
        ]
    ),
    "L9": MilestoneInfo(
        name="中级完成",
        main_course_lessons=1300,  # 1156 + L7(48) + L8(48) + L9(48)
        cumulative_lessons=2069,   # 从零基础累计总课时（含雅思口语等高阶课程）
        description="英语思维建立，接近母语表达水平",
        abilities=[
            "能无障碍使用英语应对生活各种场景，与母语使用者进行全方位的交流",
            "学习更多种类的阅读技巧之后，能够在基本没有图片辅助的情况下，进行章节阅读，阅读量突破10万+",
            "能够就熟悉话题完成200-300词的篇章写作"
        ]
    )
}


# ==================== 专业课配置 ====================

@dataclass
class ProfessionalCourseConfig:
    """专业课配置"""
    name: str                         # 课程名称
    lesson_count: int                 # 课时数
    course_type: str                  # 课程类型
    start_level: str                  # 适用起始级别
    end_level: str                    # 适用结束级别
    description: str                  # 课程描述
    recommended: bool = False         # 是否强烈推荐


PROFESSIONAL_COURSES: List[ProfessionalCourseConfig] = [
    ProfessionalCourseConfig(
        name="自然拼读",
        lesson_count=48,
        course_type="phonics",
        start_level="LS",
        end_level="L3",
        description="学习字母和字母组合发音规律，解决单词发音、记忆、拼写困难，实现见词能读、听音能写",
        recommended=True
    ),
    ProfessionalCourseConfig(
        name="单元强化复习课",
        lesson_count=18,  # 每级别18课时
        course_type="review",
        start_level="LS",
        end_level="L2",
        description="多场景练习，强化巩固整个单元知识点",
        recommended=True
    ),
    ProfessionalCourseConfig(
        name="全能新概念",
        lesson_count=288,
        course_type="new_concept",
        start_level="L2",
        end_level="L6",
        description="对词汇、语法、篇章及听说四个模块进行逐层讲解，逐步构建语言能力体系",
        recommended=True
    ),
    ProfessionalCourseConfig(
        name="全能英语进阶",
        lesson_count=120,
        course_type="advanced",
        start_level="L5",
        end_level="L9",
        description="用英语学习不同文化知识，帮助学员运用英语和英文思维进行探索和思考",
        recommended=True
    ),
    ProfessionalCourseConfig(
        name="雅思口语5.5",
        lesson_count=144,
        course_type="ielts",
        start_level="L6",
        end_level="L9",
        description="结合雅思口语评分标准打造，词汇、句型和模板，助力雅思5.5分",
        recommended=False
    ),
    ProfessionalCourseConfig(
        name="雅思口语6.5",
        lesson_count=144,
        course_type="ielts",
        start_level="L7",
        end_level="L9",
        description="结合雅思口语评分标准打造，词汇、句型和模板，助力雅思6.5分",
        recommended=False
    ),
    ProfessionalCourseConfig(
        name="雅思口语7.5",
        lesson_count=144,
        course_type="ielts",
        start_level="L8",
        end_level="L9",
        description="结合雅思口语评分标准打造，词汇、句型和模板，助力雅思7.5分",
        recommended=False
    ),
    ProfessionalCourseConfig(
        name="自由会话",
        lesson_count=0,  # 不限
        course_type="free_talk",
        start_level="L3",
        end_level="L9",
        description="借助思维导图打开思路，积累不同话题中的精妙表达，自如表达观点",
        recommended=False
    )
]


# ==================== 核心逻辑函数 ====================

def normalize_level_code(level: str) -> str:
    """标准化级别代码"""
    return level.upper().replace("LEVEL ", "").replace("LEVEL", "").strip()


def get_levels_to_target(current_level: str, target_level: str) -> List[str]:
    """
    获取从当前级别到目标级别需要学习的级别列表
    
    Args:
        current_level: 当前级别代码
        target_level: 目标级别代码
        
    Returns:
        需要学习的级别列表（不包含当前级别）
    """
    current = normalize_level_code(current_level)
    target = normalize_level_code(target_level)
    
    if current not in LEVEL_ORDER or target not in LEVEL_ORDER:
        return []
    
    current_idx = LEVEL_ORDER.index(current)
    target_idx = LEVEL_ORDER.index(target)
    
    if current_idx >= target_idx:
        return []
    
    # 返回从下一级别到目标级别的所有级别（不包含当前级别）
    return list(LEVEL_ORDER[current_idx + 1: target_idx + 1])


def get_applicable_professional_courses(
    current_level: str,
    target_level: str
) -> List[ProfessionalCourseConfig]:
    """
    获取学习路径中适用的专业课
    
    Args:
        current_level: 当前级别
        target_level: 目标级别
        
    Returns:
        适用的专业课列表
    """
    current = normalize_level_code(current_level)
    target = normalize_level_code(target_level)
    
    if current not in LEVEL_ORDER or target not in LEVEL_ORDER:
        return []
    
    current_idx = LEVEL_ORDER.index(current)
    target_idx = LEVEL_ORDER.index(target)
    
    result = []
    for course in PROFESSIONAL_COURSES:
        course_start_idx = LEVEL_ORDER.index(course.start_level)
        course_end_idx = LEVEL_ORDER.index(course.end_level)
        
        # 检查学习路径是否与课程适用范围有交集
        if not (target_idx < course_start_idx or current_idx >= course_end_idx):
            result.append(course)
    
    return result


def get_recommended_professional_courses(
    current_level: str,
    target_level: str
) -> List[ProfessionalCourseConfig]:
    """
    获取推荐的专业课（仅返回 recommended=True 的）
    """
    return [
        c for c in get_applicable_professional_courses(current_level, target_level)
        if c.recommended
    ]


@dataclass
class LearningPlanDetail:
    """学习规划详情"""
    current_level: str                # 当前级别
    target_level: str                 # 目标级别
    levels_to_learn: List[str]        # 需要学习的级别列表
    main_courses: List[Dict[str, Any]]  # 主修课明细
    main_course_total_lessons: int    # 主修课总课时
    professional_courses: List[Dict[str, Any]]  # 推荐专业课明细
    professional_course_total_lessons: int  # 专业课总课时
    required_lessons: int             # 个性化总课时
    level_span: int                   # 跨越级数
    current_stage: str                # 当前所属阶段
    target_stage: str                 # 目标所属阶段
    reaches_milestone: bool           # 是否到达里程碑节点
    milestone_info: Optional[MilestoneInfo] = None  # 到达的里程碑信息


def calculate_learning_plan(
    current_level: str,
    target_level: str = None
) -> LearningPlanDetail:
    """
    计算完整的学习规划
    
    Args:
        current_level: 当前级别
        target_level: 目标级别（如果为 None 则使用推荐目标级别）
        
    Returns:
        学习规划详情
    """
    current = normalize_level_code(current_level)
    target = normalize_level_code(target_level) if target_level else get_target_level(current)
    
    levels_to_learn = get_levels_to_target(current, target)
    
    # 计算主修课明细
    main_courses = []
    for level in levels_to_learn:
        lesson_count = LEVEL_LESSON_COUNT.get(level, 0)
        course_name = f"CEJ Level {level.replace('L', '') if level != 'LS' else 'S'}"
        main_courses.append({
            "level": level,
            "course_name": course_name,
            "lesson_count": lesson_count
        })
    
    main_course_total = sum(c["lesson_count"] for c in main_courses)
    
    # 获取推荐专业课
    recommended = get_recommended_professional_courses(current, target)
    professional_courses = [
        {
            "course_name": c.name,
            "lesson_count": c.lesson_count,
            "description": c.description
        }
        for c in recommended if c.lesson_count > 0
    ]
    
    professional_total = sum(c["lesson_count"] for c in professional_courses)
    
    # 检查是否到达里程碑
    reaches_milestone = target in ["L3", "L6", "L9"]
    milestone_info = MILESTONES_DETAILED.get(target) if reaches_milestone else None
    
    return LearningPlanDetail(
        current_level=current,
        target_level=target,
        levels_to_learn=levels_to_learn,
        main_courses=main_courses,
        main_course_total_lessons=main_course_total,
        professional_courses=professional_courses,
        professional_course_total_lessons=professional_total,
        required_lessons=main_course_total + professional_total,
        level_span=len(levels_to_learn),
        current_stage=get_level_group(current),
        target_stage=get_level_group(target),
        reaches_milestone=reaches_milestone,
        milestone_info=milestone_info
    )


@dataclass
class LearningDuration:
    """学习周期估算"""
    weeks: int
    months: int
    years: float
    description: str


def estimate_learning_duration(
    total_lessons: int,
    lessons_per_week: int = 3
) -> LearningDuration:
    """
    估算学习周期
    
    Args:
        total_lessons: 总课时数
        lessons_per_week: 每周课时数（默认3节）
        
    Returns:
        学习周期估算
    """
    import math
    
    weeks = math.ceil(total_lessons / lessons_per_week)
    months = round(weeks / 4.33)  # 平均每月4.33周
    years = round(months / 12 * 10) / 10  # 保留一位小数
    
    if months < 12:
        description = f"约{months}个月"
    elif years < 2:
        description = f"约1年{months - 12}个月"
    else:
        description = f"约{years}年"
    
    return LearningDuration(
        weeks=weeks,
        months=months,
        years=years,
        description=description
    )


# ==================== Prompt 生成函数 ====================

def generate_369_system_intro() -> str:
    """
    生成 CEJ 体系介绍文案（用于 AI 生成）
    """
    l3 = MILESTONES_DETAILED["L3"]
    l6 = MILESTONES_DETAILED["L6"]
    l9 = MILESTONES_DETAILED["L9"]
    
    return f"""
## 51Talk CEJ 课程体系【必须引用以下数据】

╔══════════════════════════════════════════════════════════════════╗
║ ⚠️ 重要：CEJ体系的关键里程碑是Level 3、Level 6、Level 9         ║
║ • 不是"3个阶段"、"6个阶段"的意思！                               ║
║ • 里程碑的课时是从Level S开始的累计课时，不是单个级别课时        ║
║ • 单个级别课时约144课时，但里程碑累计课时是几百到上千课时        ║
╚══════════════════════════════════════════════════════════════════╝

❌ 错误说法示例（绝对禁止！）：
- ❌ "完成3个阶段，累计144课时" — 错误！
- ❌ "完成6个阶段，累计288课时" — 错误！

✅ 正确说法（必须这样说）：
- ✅ "学完Level 3（入门级），累计约{l3.cumulative_lessons}课时"
- ✅ "学完Level 6（初级），累计约{l6.cumulative_lessons}课时"

### 🎯 第一个里程碑：学完 Level 3（入门级毕业）
- 【真实数据】从零基础（Level S）学到Level 3，累计约 {l3.cumulative_lessons} 课时
- 参考话术："从零基础学到L3，累计约{l3.cumulative_lessons}课时"
- 【真实数据】达到水平：{l3.description}
- 【达到后能做什么】{'; '.join(l3.abilities)}

### 🎯 第二个里程碑：学完 Level 6（初级毕业）
- 【真实数据】从零基础（Level S）学到Level 6，累计约 {l6.cumulative_lessons} 课时
- 参考话术："从零基础学到L6，累计约{l6.cumulative_lessons}课时"
- 【真实数据】达到水平：{l6.description}
- 【达到后能做什么】{'; '.join(l6.abilities)}

### 🎯 第三个里程碑：学完 Level 9（中级毕业）
- 【真实数据】从零基础（Level S）学到Level 9，累计约 {l9.cumulative_lessons} 课时
- 参考话术："从零基础学到L9，累计约{l9.cumulative_lessons}课时"
- 【真实数据】达到水平：{l9.description}
- 【达到后能做什么】{'; '.join(l9.abilities)}

### 级别阶段划分
- **启蒙级**（Level S、Level 0）：语言兴趣建立，基础语感培养
- **入门级**（Level 1、2、3）：基础对话交流，自然拼读，基础语法
- **初级**（Level 4、5、6）：阅读能力训练，语言核心能力与表达技巧
- **中级**（Level 7、8、9）：英语思维建立，高阶词汇，母语表达习惯

### ⚠️ 单级别课时数【必须牢记，严禁自己计算！】
| 级别 | 主修课课时 |
|------|-----------|
| Level S | 148课时 |
| Level 0 | 144课时 |
| Level 1 | 144课时 |
| Level 2 | 144课时 |
| Level 3 | 144课时 |
| Level 4 | 144课时 |
| Level 5 | 144课时 |
| Level 6 | 144课时 |
| Level 7 | 48课时 |
| Level 8 | 48课时 |
| Level 9 | 48课时 |

❌ 绝对禁止的错误：
- ❌ "CEJ Level 1需要144课时，Level 2需要192课时" — 大错特错！每个级别都是固定课时！
- ❌ "Level 3需要288课时" — 错误！288是全能新概念专业课的课时，不是主修课！
- ❌ 自己计算或累加课时 — 必须直接引用上表数据！
""".strip()


def generate_learning_plan_text(plan: LearningPlanDetail, lessons_per_week: int = 5) -> str:
    """
    生成学习规划文案（用于 AI 生成）
    
    Args:
        plan: 学习规划详情
        lessons_per_week: 每周课时数（默认5节）
        
    Returns:
        学习规划文案
    """
    text = f"""
## 学习规划详情【核心数据，必须在演讲中引用】

⚠️ 以下课时数据为官方真实数据，演讲时必须准确引用，严禁编造或使用其他数字！

### 📍 当前位置
- 【真实数据】当前级别：{plan.current_level}
- 【真实数据】所属阶段：{plan.current_stage}

### 🎯 目标规划
- 【真实数据】目标级别：{plan.target_level}
- 【真实数据】目标阶段：{plan.target_stage}
- 【真实数据】跨越级数：{plan.level_span} 个级别
"""
    
    if plan.reaches_milestone and plan.milestone_info:
        text += f"- 【真实数据】🏆 达到里程碑：{plan.milestone_info.name}\n"
    
    text += f"""
### 📚 从{plan.current_level}到{plan.target_level}的主修课课时明细

╔═══════════════════════════════════════════════════════════════════════════╗
║ 🚨🚨🚨 AI必读 - 课时数据核对表 🚨🚨🚨                                      ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ 以下是【唯一正确的主修课课时数据】，必须逐字引用，禁止任何修改！          ║
╚═══════════════════════════════════════════════════════════════════════════╝

"""
    
    # 用表格形式输出
    text += "┌─────────────────┬────────────────┐\n"
    text += "│ 级别名称        │ 课时数（唯一正确值）│\n"
    text += "├─────────────────┼────────────────┤\n"
    for course in plan.main_courses:
        padded_name = course["course_name"].ljust(12)
        text += f"│ {padded_name}   │ {course['lesson_count']} 课时 ✓      │\n"
    text += "├─────────────────┼────────────────┤\n"
    text += f"│ 【主修课合计】  │ {plan.main_course_total_lessons} 课时 ✓     │\n"
    text += "└─────────────────┴────────────────┘\n"
    
    text += f"""
🚫🚫🚫 以下数字是【错误的】，绝对不能出现在你的回答中 🚫🚫🚫
- ❌ 192 — 这个数字是错误的！不存在192课时的级别！
- ❌ 288 — 这是专业课课时，不是主修课！
- ❌ 96 — 不存在96课时的级别！
- ❌ 任何不是上表中列出的数字都是错误的！

✅ 正确的主修课课时：LS=148课时，L0-L6每个都是144课时，L7-L9每个都是48课时！

🔒 你必须使用的主修课数据（复制粘贴即可）：
"""
    for course in plan.main_courses:
        text += f"► {course['course_name']}：{course['lesson_count']} 课时\n"
    text += f"► 主修课总计：{plan.main_course_total_lessons} 课时\n"
    
    if plan.professional_courses:
        text += f"""
### 📖 推荐专业课搭配【这是专业课，不是主修课！】
⚠️ 注意：以下是【专业课】课时，与上面的【主修课】是两回事！
"""
        for course in plan.professional_courses:
            text += f"- 【专业课】{course['course_name']}：{course['lesson_count']} 课时\n"
            text += f"  （{course['description']}）\n"
        text += f"- 【专业课小计】**{plan.professional_course_total_lessons} 课时**（这是专业课，不是主修课！）\n"
    
    # 计算学习周期
    main_duration = estimate_learning_duration(plan.main_course_total_lessons, lessons_per_week)
    total_duration = estimate_learning_duration(plan.required_lessons, lessons_per_week)
    
    has_professional = plan.professional_course_total_lessons > 0
    
    if has_professional:
        text += f"""
### 📊 给家长算课时【必须在演讲中明确告知家长】

#### 📚 主修课课时（核心必学）
- 【必须原样引用】**主修课总计：{plan.main_course_total_lessons} 课时**
- 按每周 {lessons_per_week} 节课计算，主修课预计学习周期：**{main_duration.description}**（约{main_duration.weeks}周）

#### 📖 专业课课时（拓展提升）
- 【必须原样引用】**专业课总计：{plan.professional_course_total_lessons} 课时**

#### 📊 全部课时汇总
- 【必须原样引用】**从{plan.current_level}到{plan.target_level}，主修课+专业课 共需：{plan.required_lessons} 课时**
- 【必须原样引用】全部学完按每周 {lessons_per_week} 节课计算，预计学习周期：**{total_duration.description}**（约{total_duration.weeks}周）

╔══════════════════════════════════════════════════════════════════════════╗
║ ✅ 正确话术示例（必须这样说）：                                          ║
║ "从{plan.current_level}到{plan.target_level}，主修课需要{plan.main_course_total_lessons}课时，专业课{plan.professional_course_total_lessons}课时，   ║
║  总共{plan.required_lessons}课时。按每周{lessons_per_week}节课计算，大约{total_duration.description}"            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    else:
        text += f"""
### 📊 给家长算课时【必须在演讲中明确告知家长】
- 【必须原样引用】**从{plan.current_level}到{plan.target_level}，孩子共需：{plan.main_course_total_lessons} 课时**
- 【必须原样引用】按每周 {lessons_per_week} 节课计算，预计学习周期：**{main_duration.description}**（约{main_duration.weeks}周）

╔══════════════════════════════════════════════════════════════════════════╗
║ ✅ 正确话术示例（必须这样说）：                                          ║
║ "从{plan.current_level}到{plan.target_level}，需要学习{plan.main_course_total_lessons}课时，          ║
║  按每周{lessons_per_week}节课计算，大约{main_duration.description}"                    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    
    text += f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║ 🚨 AI最终核对 - 你的回答中出现的课时数字必须与以下完全一致 🚨               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
"""
    for course in plan.main_courses:
        text += f"║ ✓ {course['course_name']}：必须是 {course['lesson_count']} 课时                                           ║\n"
    text += f"""║ ✓ 主修课总计：必须是 {plan.main_course_total_lessons} 课时                                            ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ ⛔ 如果你的回答中出现192、288等错误数字，说明你没有正确引用数据！           ║
║ ⛔ 每个CEJ Level的主修课都是144课时（除了LS是148），不会递增！              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""
    
    if plan.milestone_info:
        text += f"""
### 🏆 完成目标后能达到的水平
{plan.milestone_info.description}
"""
    
    return text.strip()


def generate_current_stage_analysis(level_code: str) -> str:
    """
    生成当前阶段分析文案
    
    Args:
        level_code: 当前级别代码
        
    Returns:
        当前阶段分析文案
    """
    level = normalize_level_code(level_code)
    level_data = get_level_data(level)
    
    if not level_data:
        return f"无法获取级别 {level} 的数据"
    
    stage = get_level_group(level)
    
    # 计算词汇量和句子量
    total_vocab = 0
    total_sentences = 0
    unit_topics = []
    sample_sentences = []
    
    for unit in level_data.get("units", []):
        stats = unit.get("stats", {})
        total_vocab += stats.get("vocabCount", 0)
        total_sentences += stats.get("sentenceCount", 0)
        unit_topics.append(unit.get("topic", ""))
        
        # 收集示例句型
        if "keywords" in unit:
            keywords = unit.get("keywords", [])
            if keywords:
                sample_sentences.extend(keywords[:2])
    
    text = f"""
## 2.4 孩子现状分析【必须引用以下真实数据】

### 当前级别：{level_data.get('levelName', level)}
- 所属阶段：{stage}
- 预计学习时长：{level_data.get('estimatedDuration', '未知')}

### 学习内容数据【必须引用】
- 词汇量：{total_vocab} 个词汇
- 句子量：{total_sentences} 个句子
- 单元主题：{', '.join(unit_topics[:6])}等

### 学习目标【必须引用】
"""
    for goal in level_data.get("learningGoals", [])[:3]:
        text += f"- {goal}\n"
    
    text += """
### 核心能力培养【必须引用】
"""
    for ability in level_data.get("coreAbilities", [])[:3]:
        text += f"- {ability}\n"
    
    # 亮点
    highlights = level_data.get("highlights", [])
    if highlights:
        text += """
### 级别亮点
"""
        for highlight in highlights[:4]:
            text += f"- {highlight}\n"
    
    return text.strip()


def generate_success_case_text(level_code: str) -> str:
    """
    生成成功案例文案
    
    Args:
        level_code: 级别代码
        
    Returns:
        成功案例文案
    """
    level = normalize_level_code(level_code)
    level_data = get_level_data(level)
    
    if not level_data:
        return ""
    
    success_cases = level_data.get("successCases", [])
    if not success_cases:
        return ""
    
    text = """
## successCases 成功案例【必须从以下数据中选择引用，严禁编造！】

⚠️⚠️⚠️ 警告：以下案例数据是真实学员案例，严禁使用"小明"、"二等奖"等示例内容！
"""
    
    for i, case in enumerate(success_cases, 1):
        text += f"""
### 案例{i}：{case.get('studentName', '匿名同学')}
- 【真实数据】学员名字：{case.get('studentName', '匿名同学')}
- 【真实数据】起始级别：{case.get('startLevel', '未知')}
- 【真实数据】当前级别：{case.get('currentLevel', '未知')}
- 【真实数据】学习时长：{case.get('studyDuration', '未知')}
- 【真实数据】每周课时：{case.get('lessonsPerWeek', 0)} 节
- 【真实数据】取得成就：
"""
        for achievement in case.get("achievements", []):
            text += f"  • {achievement}\n"
        
        if case.get("parentFeedback"):
            text += f"- 【真实数据】家长反馈：\"{case.get('parentFeedback')}\"\n"
        
        text += "- 【真实数据】成功要点：\n"
        for point in case.get("keyPoints", []):
            text += f"  • {point}\n"
    
    return text.strip()


def generate_course_knowledge_prompt(current_level: str, target_level: str = None) -> str:
    """
    生成完整的课程知识库 Prompt
    
    这是主入口函数，用于生成报告解读中成长计划部分所需的全部知识库内容。
    
    Args:
        current_level: 当前级别代码
        target_level: 目标级别代码（如果为 None 则使用推荐目标级别）
        
    Returns:
        完整的课程知识库 Prompt
    """
    current = normalize_level_code(current_level)
    target = normalize_level_code(target_level) if target_level else get_target_level(current)
    
    # 计算学习规划
    plan = calculate_learning_plan(current, target)
    
    # 组装完整 Prompt
    sections = [
        "# 📚 课程知识库【AI 必须引用的官方数据】",
        "",
        "⚠️⚠️⚠️ 重要声明 ⚠️⚠️⚠️",
        "以下所有数据均为 51Talk 官方课程数据，在生成演讲稿时必须原样引用，",
        "严禁编造、修改或使用任何示例数据！违反此规则将导致生成结果无效！",
        "",
        generate_369_system_intro(),
        "",
        generate_current_stage_analysis(current),
        "",
        generate_learning_plan_text(plan),
        "",
        generate_success_case_text(current),
    ]
    
    return "\n".join(sections)


def generate_roadmap_content_guide(current_level: str, target_level: str = None) -> str:
    """
    生成成长计划（roadmap）板块的内容指南
    
    这是用于指导 AI 生成 roadmap 部分内容的详细指南，包含 8 个核心问题。
    
    Args:
        current_level: 当前级别代码
        target_level: 目标级别代码
        
    Returns:
        roadmap 内容指南
    """
    current = normalize_level_code(current_level)
    target = normalize_level_code(target_level) if target_level else get_target_level(current)
    plan = calculate_learning_plan(current, target)
    level_data = get_level_data(current)
    target_data = get_level_data(target)
    
    # 构建主修课课时明细字符串
    main_course_details = []
    for course in plan.main_courses:
        main_course_details.append(f"{course['course_name']}={course['lesson_count']}课时")
    main_course_str = "、".join(main_course_details)
    
    guide = f"""
## roadmap 成长计划内容指南【必须2200字以上！这是最重要的板块！】

采用对话式结构，通过8个核心问题引导家长参与讨论：

### 【问题1：孩子当前处于哪个阶段？】（约250字）
⚠️ 第一段不要用反问句开头！用陈述句直接切入主题。
如：'关于孩子的学习规划，我想先和您聊聊孩子当下处于哪个阶段。'然后直接解答（不要反问）。
⚠️ 必须从课程知识库中获取正确的级别名称和阶段名称！
• Level S、Level 0 = 启蒙级（启蒙起步阶段）
• Level 1、2、3 = 入门级（基础交流阶段）
• Level 4、5、6 = 初级（交流进阶阶段）
• Level 7、8、9 = 中级（流利表达阶段）

【真实数据】当前级别：{current}，所属阶段：{plan.current_stage}
然后介绍这个阶段在整个CEJ体系中的位置。这一段结尾不要反问。

### 【问题2：学习的内容主要是什么？】（约300字）
过渡问题：'那您知道孩子现在这个阶段主要在学什么内容吗？'（这里可以用反问）
⚠️ 必须引用课程知识库"2.4 孩子现状分析"中的【真实数据】！
"""
    
    # 添加当前级别的学习内容数据
    if level_data:
        total_vocab = 0
        total_sentences = 0
        unit_topics = []
        for unit in level_data.get("units", []):
            stats = unit.get("stats", {})
            total_vocab += stats.get("vocabCount", 0)
            total_sentences += stats.get("sentenceCount", 0)
            unit_topics.append(unit.get("topic", ""))
        
        guide += f"""
【真实数据】{current}级别学习内容：
- 词汇量：{total_vocab}个词汇
- 句子量：{total_sentences}个句子
- 单元主题：{', '.join(unit_topics[:6])}等
然后结合孩子课堂上的实际表现举例，如'比如最近的课堂上，他学会了用I like来表达喜好'。
"""
    
    guide += f"""
### 【问题3：提升哪方面能力？】（约250字）
⚠️ 第三段不要用反问句！用陈述句引导。
如：'这个阶段重点培养的是听说能力和自信表达。'然后结合报告数据说明，用孩子的进步案例佐证。这一段不要反问。
"""
    
    if level_data and level_data.get("coreAbilities"):
        guide += f"""
【真实数据】{current}级别核心能力培养：
"""
        for ability in level_data.get("coreAbilities", [])[:3]:
            guide += f"- {ability}\n"
    
    guide += f"""
### 【问题4：目标级别到哪？】（约350字）
关键问题：'那您对孩子的英语学习有什么期待呢？咱们的目标级别想定到哪？'
介绍CEJ体系的里程碑【注意！CEJ体系指Level 3、Level 6、Level 9三个关键里程碑，累计课时是几百到上千！】

⚠️ 介绍每个里程碑时必须说明【达到后能做什么】，引用课程知识库数据！
示例：
- 学完Level 3约{MILESTONES_DETAILED['L3'].cumulative_lessons}课时达到A1水平，孩子就能用英语进行简单的自我介绍、能听懂并回答日常基础问题、出国旅游时能进行基础的点餐问路交流
- 学完Level 6约{MILESTONES_DETAILED['L6'].cumulative_lessons}课时达到A2水平，孩子就能流利地讲述英文小故事、看英文动画片能听懂大部分对话
- 学完Level 9约{MILESTONES_DETAILED['L9'].cumulative_lessons}课时达到B1-B2水平，孩子就能用英语进行主题演讲和辩论、看英文电影基本不需要字幕

⚠️ 目标级别选择规则：目标级别 = 当前级别 + 3
【真实数据】当前级别：{current}，推荐目标级别：{target}
然后根据孩子情况建议合适的目标级别，问'您觉得这个目标合适吗？'

### 【问题5：能学到什么？】（约400字）
展望：'您想知道孩子达到这个目标后能学到什么、能做到什么吗？'
⚠️ 必须先引用课程知识库"2.7 目标级别到哪"中的【stageAchievements阶段能力达成】数据，再用生活场景举例！
⚠️ 注意：必须根据目标级别选择对应的能力描述，不要套用固定模板！
"""
    
    if target_data and target_data.get("learningPath", {}).get("stageAchievements"):
        guide += f"""
【真实数据】达到{target}后的能力达成：
"""
        for achievement in target_data.get("learningPath", {}).get("stageAchievements", []):
            guide += f"- {achievement}\n"
    
    guide += """
结构：①先介绍学术性的能力达成，必须原样引用知识库中【stageAchievements阶段能力达成】的具体内容
②然后用具体生活场景让家长有画面感，场景要与目标级别的能力水平匹配。激发家长期待。

### 【问题6：有没有类似的成功案例？】（约250字）
⚠️⚠️⚠️ 绝对禁止使用下面的示例内容！必须从课程知识库的【successCases】字段获取真实数据！
过渡：'说到这里，我想和您分享一个我们学员的真实案例。'
"""
    
    # 添加成功案例数据
    if level_data and level_data.get("successCases"):
        case = level_data.get("successCases", [{}])[0]
        guide += f"""
【真实数据】成功案例：
- 学员名字：{case.get('studentName', '匿名同学')}
- 起始级别：{case.get('startLevel', current)}
- 学习时长：{case.get('studyDuration', '未知')}
- 每周课时：{case.get('lessonsPerWeek', 0)}节
- 取得成就：{', '.join(case.get('achievements', [])[:3])}
- 家长反馈："{case.get('parentFeedback', '')}"
- 成功要点：{', '.join(case.get('keyPoints', [])[:2])}

🚫🚫🚫 致命错误："小明同学"、"二等奖"、"每天都主动要求上英语课"这些是示例内容，绝对禁止使用！
✅ 正确做法：查看知识库中successCases的实际内容，逐字引用其中的数据。
用真实案例增强家长信心，让家长看到孩子的未来可能性。
"""
    
    guide += f"""
### 【问题7：需要多少课时？】（约300字）
⚠️⚠️⚠️ 绝对禁止自己计算课时！必须逐字从课程知识库的"📚 主修课课时明细"表格中复制！
🚫🚫🚫 致命错误提醒：课时不会随级别递增！LS=148课时，L0-L6每个都是144课时，L7-L9每个都是48课时！

【真实数据】从{current}到{target}的主修课课时明细：
- {main_course_str}
- 主修课合计：{plan.main_course_total_lessons}课时

⚠️⚠️⚠️ 重要逻辑：计算"从当前级别到目标级别"所需课时时，不包含当前级别！因为学生已在当前级别学习！
✅ 正确示例：当前{current}，目标{target}，需计算{main_course_str}，合计{plan.main_course_total_lessons}课时

然后引导家长理解课时安排，问'您平时每周能安排几节课？'

### 【问题8：如何规划学习周期？】（约200字）
根据家长的时间安排，给出具体的学习周期建议：
"""
    
    # 计算不同频率的学习周期
    for freq in [3, 4, 5]:
        duration = estimate_learning_duration(plan.main_course_total_lessons, freq)
        guide += f"- 每周{freq}节课：约{duration.description}（{duration.weeks}周）\n"
    
    guide += f"""
⚠️ 计算公式：总课时 ÷ 每周课时 = 总周数
【真实数据】主修课总计{plan.main_course_total_lessons}课时

最后总结：'所以如果每周X节课，大约X个月就能达到{target}，您觉得这个规划可以吗？'
"""
    
    return guide.strip()


# ==================== 导出 ====================

__all__ = [
    # 类型定义
    "UnitStats",
    "UnitInfo",
    "CoursePackage",
    "LearningPath",
    "SuccessCase",
    "MilestoneInfo",
    "ProfessionalCourseConfig",
    "LearningPlanDetail",
    "LearningDuration",
    # 配置数据
    "LEVEL_DATA",
    "LEVEL_ORDER",
    "LEVEL_GROUPS",
    "LEVEL_LESSON_COUNT",
    "MILESTONES",
    "MILESTONES_DETAILED",
    "TARGET_LEVEL_MAP",
    "PROFESSIONAL_COURSES",
    # 工具函数
    "normalize_level_code",
    "get_level_data",
    "get_level_group",
    "get_target_level",
    "get_levels_to_target",
    "get_applicable_professional_courses",
    "get_recommended_professional_courses",
    "calculate_learning_plan",
    "calculate_lessons_needed",
    "estimate_learning_duration",
    "get_milestone_info",
    # Prompt 生成函数
    "generate_369_system_intro",
    "generate_learning_plan_text",
    "generate_current_stage_analysis",
    "generate_success_case_text",
    "generate_course_knowledge_prompt",
    "generate_roadmap_content_guide",
]
