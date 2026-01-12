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



from src.adapters.gateways.qwen_client import QwenOmniGateway

class ReportInterpretationService:
    """
    Generates interpretation for teacher-to-parent communication.
    
    Uses LLM (Qwen) for generation, with rule-based fallback (optional).
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
        part2_items: Optional[list] = None
    ) -> ReportInterpretation:
        """
        Generate interpretation based on test results using LLM.
        """
        # Call LLM
        result = await self.qwen.generate_report_interpretation(
            student_name=student_name,
            level=level,
            total_score=total_score,
            part1_score=part1_score,
            part2_score=part2_score,
            star_level=star_level,
            part1_details=part1_details,
            part2_items=part2_items
        )
        
        if result.success:
            return ReportInterpretation(
                highlights=result.highlights,
                weaknesses=result.weaknesses,
                evidence=result.evidence,
                suggestions=result.suggestions,
                parent_script=result.parent_script
            )
        else:
            logger.error(f"LLM interpretation failed: {result.error}. Falling back to rules.")
            return self._generate_rule_based(
                student_name, level, total_score, part1_score, 
                part2_score, star_level, part1_details, part2_items
            )

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
        """Fallback: Rule-based generation (Original logic)."""
        highlights = []
        weaknesses = []
        evidence = []
        suggestions = []
        
        # Analyze Part 1 (Vocabulary)
        if part1_score is not None:
            p1_pct = part1_score
            if p1_pct >= 85:
                highlights.append(f"词汇发音准确率高达 {p1_pct:.0f}%，基础扎实")
            elif p1_pct >= 70:
                highlights.append(f"词汇发音正确率 {p1_pct:.0f}%，表现稳定")
            else:
                weaknesses.append(f"词汇发音正确率 {p1_pct:.0f}%，需加强基础练习")
            
            if part1_details and "words" in part1_details:
                weak_words = [
                    w["word"] for w in part1_details["words"]
                    if w.get("score", 100) < 60
                ]
                if weak_words[:3]:
                    evidence.append(f"需重点练习的词汇：{', '.join(weak_words[:3])}")
        
        # Analyze Part 2 (Expression)
        if part2_score is not None and part2_items:
            perfect_count = sum(1 for item in part2_items if item.get("score") == 2)
            zero_count = sum(1 for item in part2_items if item.get("score") == 0)
            
            if perfect_count >= 8:
                highlights.append(f"问答表达优秀，{perfect_count}/12 题满分")
            elif perfect_count >= 5:
                highlights.append(f"问答表达良好，{perfect_count}/12 题满分")
            
            if zero_count >= 4:
                weaknesses.append(f"有 {zero_count} 题未能正确回答，需加强句型练习")
            
            for item in part2_items[:2]:
                if item.get("evidence"):
                    evidence.append(f"Q{item['question_no']}: {item['evidence'][:50]}...")
        
        # Generate suggestions
        if star_level >= 4:
            suggestions = ["继续保持每日10分钟朗读练习", "可尝试更高难度Level的学习"]
        elif star_level >= 3:
            suggestions = ["每天跟读10个核心词汇，注意发音", "每周完成3次问答练习"]
        else:
            suggestions = ["每天回听录音，对照标准发音纠正", "先从基础词汇发音开始"]
        
        # Generate script
        star_emoji = "⭐" * star_level
        parent_script = self._generate_parent_script(
            student_name, level, total_score, star_level, star_emoji,
            highlights, weaknesses, suggestions
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
        script = f"""【{student_name}同学 {level} 口语测评报告】

您好！{student_name}同学本次口语测评已完成，以下是详细解读：

📊 **综合评分**：{total_score:.1f}/44 分 ({star_emoji})

"""
        if highlights:
            script += "✅ **亮点**：\n"
            for h in highlights:
                script += f"• {h}\n"
            script += "\n"
        
        if weaknesses:
            script += "📌 **需改进**：\n"
            for w in weaknesses:
                script += f"• {w}\n"
            script += "\n"
        
        script += "💡 **本周建议**：\n"
        for i, s in enumerate(suggestions, 1):
            script += f"{i}. {s}\n"
        
        script += "\n如有任何问题，欢迎随时联系我！"
        return script
