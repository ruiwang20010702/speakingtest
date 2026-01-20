"""
Report Interpretation Service
Generates AI-powered speech scripts for teacher-parent communication.
按6页组织：cover, radar, vocab, dialogue, roadmap, badge
总时长约10分钟
"""
from typing import Optional, Dict
from dataclasses import dataclass
from loguru import logger

from src.infrastructure.config import get_settings

settings = get_settings()


@dataclass
class ReportInterpretation:
    """AI-generated speech script for teacher-parent communication, organized by 6 pages."""
    pages: Dict[str, str]  # 按页面组织的演讲话术（每页一段字符串）
    full_script: str       # 完整演讲稿（约1500字，10分钟）
    course_selling: Optional[str] = None  # 课程规划演讲稿（约2200字，5分钟）
    usage: Optional[dict] = None  # API 调用的 token 使用情况
    
    def to_dict(self) -> dict:
        """转换为可存储的 dict 格式"""
        return {
            "pages": self.pages,
            "full_script": self.full_script,
            "course_selling": self.course_selling,
        }
    
    def pages_to_json(self) -> dict:
        """返回 pages 和 course_selling 的 dict（用于存储到 interpretation_pages 字段）"""
        result = self.pages.copy()
        if self.course_selling:
            result["course_selling"] = self.course_selling
        return result


from src.adapters.gateways.qwen_client import QwenOmniGateway

class ReportInterpretationService:
    """
    Generates speech script for teacher-to-parent communication.
    
    Uses LLM (Qwen) for generation, with rule-based fallback.
    """
    
    def __init__(self, qwen_gateway: QwenOmniGateway):
        self.qwen = qwen_gateway
    
    async def generate(
        self,
        student_name: str,
        level: str,
        total_score: float,
        part1_score: float,
        part2_score: Optional[float],
        star_level: int,
        part1_details: Optional[dict] = None,
        part2_items: Optional[list] = None,
        radar_data: Optional[list] = None,
    ) -> ReportInterpretation:
        """
        Generate speech script based on test results using LLM.
        """
        # Call LLM with course selling enabled
        result = await self.qwen.generate_report_interpretation(
            student_name=student_name,
            level=level,
            total_score=total_score,
            part1_score=part1_score,
            part2_score=part2_score,
            star_level=star_level,
            part1_details=part1_details,
            part2_items=part2_items,
            radar_data=radar_data,
            include_course_selling=True,  # 启用课程规划生成
            target_level=None,  # 使用推荐目标级别
        )
        
        if result.success:
            return ReportInterpretation(
                pages=result.pages,
                full_script=result.full_script,
                course_selling=result.course_selling,
                usage=result.usage
            )
        else:
            logger.error(f"LLM interpretation failed: {result.error}. Falling back to rules.")
            fallback_result = self._generate_rule_based(
                student_name, level, total_score, part1_score, 
                part2_score, star_level, part1_details, part2_items
            )
            fallback_result.usage = result.usage
            return fallback_result

    def _generate_rule_based(
        self,
        student_name: str,
        level: str,
        total_score: float,
        part1_score: float,
        part2_score: Optional[float],
        star_level: int,
        part1_details: Optional[dict] = None,
        part2_items: Optional[list] = None
    ) -> ReportInterpretation:
        """Fallback: Rule-based generation (演讲稿格式)."""
        
        star_emoji = "⭐" * star_level
        
        # ========== Cover 页 ==========
        cover = f"""各位家长，大家好！今天我来和您分享{student_name}同学的英语口语测评报告。

这次测评{student_name}同学获得了 {total_score:.1f} 分，评定为 {star_level} 星 ({star_emoji})。我们的评分体系共有 5 星，{star_level} 星说明孩子的口语能力处于{'优秀' if star_level >= 4 else '良好' if star_level >= 3 else '入门'}水平。接下来，让我们一起来看看具体的表现分析。"""

        # ========== Radar 页 ==========
        radar_highlights = []
        radar_issues = []
        
        if part1_score >= 80:
            radar_highlights.append("发音和词汇基础扎实")
        if part2_score and part2_score >= 80:
            radar_highlights.append("整句输出能力和流利度较好")
        if part1_score < 60:
            radar_issues.append("发音准确度")
        if part2_score and part2_score < 60:
            radar_issues.append("句型表达和流利度")
        
        radar = f"""这是{student_name}同学的五维能力图谱，展示了孩子在流利度、发音、自信度、词汇、整句输出这五个维度的表现。

{'从图中可以看到，' + '、'.join(radar_highlights) + '，这是非常值得肯定的。' if radar_highlights else ''}{'不过' if radar_highlights and radar_issues else '我们注意到'}{'' if not radar_issues else '，'.join(radar_issues) + '还有提升空间。'}

建议家长在家可以多和孩子进行简单的英语对话，每天 5-10 分钟的练习就能有明显进步。"""

        # ========== Vocab 页 ==========
        vocab_good = []
        vocab_weak = []
        
        if part1_details and "words" in part1_details:
            words = part1_details["words"]
            perfect_words = [w["text"] for w in words if w.get("score", 0) >= 80][:3]
            weak_words = [w["text"] for w in words if w.get("score", 100) < 60][:3]
            
            if perfect_words:
                vocab_good = perfect_words
            if weak_words:
                vocab_weak = weak_words
        
        vocab = f"""接下来是词汇能量站，这里展示了 Part 1 朗读环节中每个单词的掌握情况。绿色表示发音完美，黄色表示需要改进，红色表示需要重点练习。

{f"像 {', '.join(vocab_good)} 这些单词，孩子读得非常标准，说明对这类词汇已经掌握得很好了。" if vocab_good else ""}

{f"而 {', '.join(vocab_weak)} 这几个单词还需要多加练习。" if vocab_weak else "整体词汇发音表现稳定。"}

建议每天花 10 分钟跟读练习，可以用点读笔或者 APP 来帮助纠正发音。"""

        # ========== Dialogue 页 ==========
        dialogue_good = 0
        dialogue_weak = 0
        
        if part2_items:
            dialogue_good = sum(1 for item in part2_items if item.get("score") == 2)
            dialogue_weak = sum(1 for item in part2_items if item.get("score") == 0)
        
        dialogue = f"""这一页展示的是问答环节的表现。Part 2 一共有 12 道问答题，考察孩子用英语回答问题的能力。

{f"{student_name}同学在这个环节表现不错，有 {dialogue_good} 道题获得了满分，说明孩子能够理解问题并给出正确的回答。" if dialogue_good >= 6 else f"孩子能够回答部分问题，{dialogue_good} 道题获得满分。"}

{f"有 {dialogue_weak} 道题还没能正确回答，主要是因为对题目不够熟悉或者表达不够完整。" if dialogue_weak >= 3 else ""}

建议平时多和孩子练习简单的问答，比如 "What's your name?" "How old are you?" 这类基础句型，帮助孩子建立英语问答的习惯。"""

        # ========== Roadmap 页 ==========
        suggestions = []
        if star_level >= 4:
            suggestions = [
                "继续保持每日 10 分钟朗读练习",
                "可以尝试更高难度 Level 的学习",
                "多参与英语对话场景练习"
            ]
        elif star_level >= 3:
            suggestions = [
                "每天跟读 10 个核心词汇，注意发音",
                "每周完成 3 次问答练习",
                "多听英语儿歌和故事"
            ]
        else:
            suggestions = [
                "每天回听录音，对照标准发音纠正",
                "先从基础词汇发音开始练习",
                "建议增加外教课频次"
            ]
        
        roadmap = f"""现在让我们来做一个总结，并制定一个成长计划。

{student_name}同学这次测评{'表现出色' if star_level >= 4 else '表现稳定' if star_level >= 3 else '还有很大进步空间'}。{'最大的亮点是' + ('、'.join(radar_highlights) if radar_highlights else '学习态度认真')}。{'需要重点提升的是' + ('、'.join(radar_issues) if radar_issues else '整体流利度') + '。' if radar_issues else ''}

为了帮助孩子继续进步，我给家长几点建议：
{chr(10).join([f"第{i+1}，{s}" for i, s in enumerate(suggestions)])}

语言学习最重要的是坚持，每天一点点积累，一定会看到明显的进步。"""

        # ========== Badge 页 ==========
        badge_titles = {
            5: "口语小达人",
            4: "语言之星",
            3: "进步之星",
            2: "勤学小将",
            1: "成长新星"
        }
        badge_title = badge_titles.get(star_level, "成长新星")
        
        badge = f"""最后，恭喜{student_name}同学获得「{badge_title}」徽章！这是对孩子努力的肯定。

{star_level} 星的评定说明孩子在同龄人中{'处于领先水平' if star_level >= 4 else '表现良好' if star_level >= 3 else '正在成长中'}。我相信只要坚持练习，下次一定能获得更好的成绩！

以上就是{student_name}同学这次口语测评的完整报告解读。各位家长如果有任何问题，欢迎随时和我沟通。谢谢大家！"""

        # ========== 组合完整演讲稿 ==========
        pages = {
            "cover": cover,
            "radar": radar,
            "vocab": vocab,
            "dialogue": dialogue,
            "roadmap": roadmap,
            "badge": badge,
        }
        
        full_script = f"""{cover}

{radar}

{vocab}

{dialogue}

{roadmap}

{badge}"""
        
        return ReportInterpretation(
            pages=pages,
            full_script=full_script
        )
