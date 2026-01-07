"""
Report Interpretation Service
Generates AI-powered report interpretations for parent communication.
"""
from typing import Optional, List
from dataclasses import dataclass
from loguru import logger

from src.infrastructure.config import get_settings

settings = get_settings()


@dataclass
class ReportInterpretation:
    """AI-generated report interpretation for parents."""
    highlights: List[str]       # 亮点 (1-2 items)
    weaknesses: List[str]       # 短板 (1-2 items)
    evidence: List[str]         # 证据点
    suggestions: List[str]      # 行动建议 (1周练习计划)
    parent_script: str          # 家长沟通话术 (完整)


class ReportInterpretationService:
    """
    Generates interpretation for teacher-to-parent communication.
    
    Uses rules-based generation for MVP, can be upgraded to LLM later.
    """
    
    def generate(
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
        """
        Generate interpretation based on test results.
        
        Args:
            student_name: Student's name
            level: Test level (e.g., L1)
            total_score: Total score (0-44)
            part1_score: Part 1 score (0-20)
            part2_score: Part 2 score (0-24)
            star_level: Star rating (1-5)
            part1_details: Raw Part 1 result with word-level scores
            part2_items: Part 2 question items with scores
        """
        highlights = []
        weaknesses = []
        evidence = []
        suggestions = []
        
        # Analyze Part 1 (Vocabulary)
        if part1_score is not None:
            p1_pct = part1_score / 20 * 100
            if p1_pct >= 85:
                highlights.append(f"词汇发音准确率高达 {p1_pct:.0f}%，基础扎实")
            elif p1_pct >= 70:
                highlights.append(f"词汇发音正确率 {p1_pct:.0f}%，表现稳定")
            else:
                weaknesses.append(f"词汇发音正确率 {p1_pct:.0f}%，需加强基础练习")
            
            # Extract weak words from part1_details
            if part1_details and "words" in part1_details:
                weak_words = [
                    w["word"] for w in part1_details["words"]
                    if w.get("score", 100) < 60
                ]
                if weak_words[:3]:
                    evidence.append(f"需重点练习的词汇：{', '.join(weak_words[:3])}")
        
        # Analyze Part 2 (Expression)
        if part2_score is not None and part2_items:
            p2_pct = part2_score / 24 * 100
            perfect_count = sum(1 for item in part2_items if item.get("score") == 2)
            zero_count = sum(1 for item in part2_items if item.get("score") == 0)
            
            if perfect_count >= 8:
                highlights.append(f"问答表达优秀，{perfect_count}/12 题满分")
            elif perfect_count >= 5:
                highlights.append(f"问答表达良好，{perfect_count}/12 题满分")
            
            if zero_count >= 4:
                weaknesses.append(f"有 {zero_count} 题未能正确回答，需加强句型练习")
            
            # Add evidence from items
            for item in part2_items[:2]:
                if item.get("evidence"):
                    evidence.append(f"Q{item['question_no']}: {item['evidence'][:50]}...")
        
        # Generate suggestions based on star level
        if star_level >= 4:
            suggestions = [
                "继续保持每日10分钟朗读练习",
                "可尝试更高难度Level的学习"
            ]
        elif star_level >= 3:
            suggestions = [
                "每天跟读10个核心词汇，注意发音",
                "每周完成3次问答练习"
            ]
        else:
            suggestions = [
                "每天回听录音，对照标准发音纠正",
                "先从基础词汇发音开始，每天5个词",
                "每周与老师进行一次口语互动"
            ]
        
        # Generate parent script
        star_emoji = "⭐" * star_level
        parent_script = self._generate_parent_script(
            student_name=student_name,
            level=level,
            total_score=total_score,
            star_level=star_level,
            star_emoji=star_emoji,
            highlights=highlights,
            weaknesses=weaknesses,
            suggestions=suggestions
        )
        
        return ReportInterpretation(
            highlights=highlights or ["本次测评表现稳定"],
            weaknesses=weaknesses or ["暂无明显短板"],
            evidence=evidence or [],
            suggestions=suggestions,
            parent_script=parent_script
        )
    
    def _generate_parent_script(
        self,
        student_name: str,
        level: str,
        total_score: float,
        star_level: int,
        star_emoji: str,
        highlights: List[str],
        weaknesses: List[str],
        suggestions: List[str]
    ) -> str:
        """Generate the full parent communication script."""
        
        # Opening
        script = f"""【{student_name}同学 {level} 口语测评报告】

您好！{student_name}同学本次口语测评已完成，以下是详细解读：

📊 **综合评分**：{total_score:.1f}/44 分 ({star_emoji})

"""
        
        # Highlights
        if highlights:
            script += "✅ **亮点**：\n"
            for h in highlights:
                script += f"• {h}\n"
            script += "\n"
        
        # Weaknesses
        if weaknesses:
            script += "📌 **需改进**：\n"
            for w in weaknesses:
                script += f"• {w}\n"
            script += "\n"
        
        # Suggestions
        script += "💡 **本周建议**：\n"
        for i, s in enumerate(suggestions, 1):
            script += f"{i}. {s}\n"
        
        script += "\n如有任何问题，欢迎随时联系我！"
        
        return script
