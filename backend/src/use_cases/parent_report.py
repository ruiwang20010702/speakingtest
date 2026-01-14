"""
Parent Report Use Case
Generates fused report data for parent H5 viewing.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from loguru import logger


@dataclass
class RadarDimension:
    """Single dimension in the radar chart (0-100 scale)."""
    subject: str
    score: float  # 0-100
    fullMark: int = 100
    icon: str = ""
    comment: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class WordStatus:
    """Status of a single word in Part 1."""
    text: str
    status: str  # 'perfect', 'unclear', 'failed'
    score: float = 0


@dataclass
class DialogueSample:
    """Sample dialogue for best/weak performance."""
    question_no: int
    question: str
    answer: str
    score: str  # 'S', 'A', 'B', 'C'
    feedback: str


@dataclass
class Part1Detail:
    """Part 1 (word reading) detail."""
    score: float
    words: List[WordStatus] = field(default_factory=list)


@dataclass
class Part2Detail:
    """Part 2 (Q&A) detail."""
    score: float
    best_sample: Optional[DialogueSample] = None
    weak_sample: Optional[DialogueSample] = None
    transcript: str = ""


@dataclass
class Suggestion:
    """Learning suggestions."""
    highlights: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    plan: List[str] = field(default_factory=list)


@dataclass
class StudentInfo:
    """Student basic info."""
    name: str
    level: str


@dataclass
class OverallScore:
    """Overall score summary."""
    total_score: float
    star_level: int


@dataclass
class ParentReportData:
    """Complete parent report data structure."""
    student: StudentInfo
    overall: OverallScore
    radar: List[RadarDimension]
    part1: Part1Detail
    part2: Part2Detail
    suggestion: Suggestion


class ScoreFusionService:
    """
    Fuse Part 1 and Part 2 scores into unified 5-dimension radar chart.
    
    All scores are 0-100 scale.
    
    Fusion Strategy:
    - Fluency: Part1_Fluency * 0.4 + Part2_Fluency * 0.6
    - Pronunciation: Part1_Pronunciation * 0.4 + Part2_Pronunciation * 0.6
    - Confidence: Part2_Confidence (only Part 2 has this)
    - Vocabulary: Part1_Accuracy * 0.3 + Part2_Vocabulary * 0.7
    - Sentence: Part1_Integrity * 0.2 + Part2_Sentence * 0.8
    """
    
    # Rating thresholds (0-100 scale)
    RATING_EXCELLENT = 80
    RATING_GOOD = 60
    RATING_FAIR = 40
    RATING_POOR = 20
    
    def fuse_scores(
        self,
        part1_raw: Optional[dict],
        part2_raw: Optional[dict]
    ) -> List[RadarDimension]:
        """
        Fuse Part 1 and Part 2 raw results into 5-dimension radar data.
        
        Args:
            part1_raw: Part 1 raw result from Qwen (contains accuracy, fluency, pronunciation, integrity)
            part2_raw: Part 2 raw result from Qwen (contains fluency, pronunciation, confidence, vocabulary, sentence)
            
        Returns:
            List of 5 RadarDimension objects
        """
        # Extract Part 1 scores (defaults to 0 if missing)
        p1_fluency = self._safe_get(part1_raw, "fluency_score", 0)
        p1_pronunciation = self._safe_get(part1_raw, "pronunciation_score", 0)
        p1_accuracy = self._safe_get(part1_raw, "accuracy_score", 0)
        p1_integrity = self._safe_get(part1_raw, "integrity_score", 0)
        
        # Extract Part 2 scores (defaults to 0 if missing)
        p2_fluency = self._safe_get(part2_raw, "fluency_score", 0)
        p2_pronunciation = self._safe_get(part2_raw, "pronunciation_score", 0)
        p2_confidence = self._safe_get(part2_raw, "confidence_score", 0)
        p2_vocabulary = self._safe_get(part2_raw, "vocabulary_score", 0)
        p2_sentence = self._safe_get(part2_raw, "sentence_score", 0)
        
        # Fusion calculations
        fused_fluency = self._fuse(p1_fluency, p2_fluency, 0.4, 0.6)
        fused_pronunciation = self._fuse(p1_pronunciation, p2_pronunciation, 0.4, 0.6)
        fused_confidence = p2_confidence  # Only Part 2 has this
        fused_vocabulary = self._fuse(p1_accuracy, p2_vocabulary, 0.3, 0.7)
        fused_sentence = self._fuse(p1_integrity, p2_sentence, 0.2, 0.8)
        
        logger.debug(
            f"Score Fusion: fluency={fused_fluency:.1f}, pronunciation={fused_pronunciation:.1f}, "
            f"confidence={fused_confidence:.1f}, vocabulary={fused_vocabulary:.1f}, sentence={fused_sentence:.1f}"
        )
        
        return [
            RadarDimension(
                subject="流利度",
                score=round(fused_fluency, 1),
                icon="fluency",
                comment=self._get_fluency_comment(fused_fluency),
                tags=self._get_fluency_tags(fused_fluency)
            ),
            RadarDimension(
                subject="发音",
                score=round(fused_pronunciation, 1),
                icon="pronunciation",
                comment=self._get_pronunciation_comment(fused_pronunciation),
                tags=self._get_pronunciation_tags(fused_pronunciation)
            ),
            RadarDimension(
                subject="自信度",
                score=round(fused_confidence, 1),
                icon="confidence",
                comment=self._get_confidence_comment(fused_confidence),
                tags=self._get_confidence_tags(fused_confidence)
            ),
            RadarDimension(
                subject="词汇",
                score=round(fused_vocabulary, 1),
                icon="vocab",
                comment=self._get_vocabulary_comment(fused_vocabulary),
                tags=self._get_vocabulary_tags(fused_vocabulary)
            ),
            RadarDimension(
                subject="整句输出",
                score=round(fused_sentence, 1),
                icon="sentence",
                comment=self._get_sentence_comment(fused_sentence),
                tags=self._get_sentence_tags(fused_sentence)
            ),
        ]
    
    def _safe_get(self, data: Optional[dict], key: str, default: float = 0) -> float:
        """Safely extract numeric value from dict."""
        if not data:
            return default
        val = data.get(key, default)
        try:
            return float(val) if val is not None else default
        except (TypeError, ValueError):
            return default
    
    def _fuse(self, score1: float, score2: float, weight1: float, weight2: float) -> float:
        """Fuse two scores with given weights."""
        # If both scores are 0, return 0
        if score1 == 0 and score2 == 0:
            return 0
        # If only one is available, use that one with full weight
        if score1 == 0:
            return score2
        if score2 == 0:
            return score1
        return score1 * weight1 + score2 * weight2
    
    def _get_rating_level(self, score: float) -> str:
        """Get rating level based on score."""
        if score >= self.RATING_EXCELLENT:
            return "杰出"
        elif score >= self.RATING_GOOD:
            return "优秀"
        elif score >= self.RATING_FAIR:
            return "良好"
        elif score >= self.RATING_POOR:
            return "及格"
        else:
            return "待提升"
    
    # ---- Fluency Comments & Tags ----
    def _get_fluency_comment(self, score: float) -> str:
        level = self._get_rating_level(score)
        if score >= 80:
            return f"等级：{level} - 语速流畅自然，节奏感强，断句清晰准确。"
        elif score >= 60:
            return f"等级：{level} - 整体连贯，偶有轻微停顿，节奏感较好。"
        elif score >= 40:
            return f"等级：{level} - 语速尚可，有不自然的停顿，需加强连贯性。"
        else:
            return f"等级：{level} - 断断续续，需要更多练习以提升流畅度。"
    
    def _get_fluency_tags(self, score: float) -> List[str]:
        if score >= 80:
            return ["节奏清晰", "断句准确"]
        elif score >= 60:
            return ["整体连贯", "偶有停顿"]
        else:
            return ["需加强连贯"]
    
    # ---- Pronunciation Comments & Tags ----
    def _get_pronunciation_comment(self, score: float) -> str:
        level = self._get_rating_level(score)
        if score >= 80:
            return f"等级：{level} - 发音地道清晰，元音饱满，辅音准确。"
        elif score >= 60:
            return f"等级：{level} - 发音清晰，偶有轻微口音，整体易于理解。"
        elif score >= 40:
            return f"等级：{level} - 发音尚可，部分元音或辅音需要纠正。"
        else:
            return f"等级：{level} - 发音有明显错误，建议跟读标准音频练习。"
    
    def _get_pronunciation_tags(self, score: float) -> List[str]:
        if score >= 80:
            return ["发音地道", "易于理解"]
        elif score >= 60:
            return ["发音清晰", "轻微口音"]
        else:
            return ["需纠正发音"]
    
    # ---- Confidence Comments & Tags ----
    def _get_confidence_comment(self, score: float) -> str:
        level = self._get_rating_level(score)
        if score >= 80:
            return f"等级：{level} - 声音洪亮，主动表达，自信满满！"
        elif score >= 60:
            return f"等级：{level} - 表达主动，声音适中，愿意分享想法。"
        elif score >= 40:
            return f"等级：{level} - 表达较为被动，声音偏小，需鼓励更多开口。"
        else:
            return f"等级：{level} - 表达被动，需要更多鼓励和练习机会。"
    
    def _get_confidence_tags(self, score: float) -> List[str]:
        if score >= 80:
            return ["声音洪亮", "主动分享", "自信满满"]
        elif score >= 60:
            return ["表达主动", "愿意沟通"]
        else:
            return ["需更多鼓励"]
    
    # ---- Vocabulary Comments & Tags ----
    def _get_vocabulary_comment(self, score: float) -> str:
        level = self._get_rating_level(score)
        if score >= 80:
            return f"等级：{level} - 单词发音准确无误，词汇基础扎实。"
        elif score >= 60:
            return f"等级：{level} - 绝大多数单词准确，偶有轻微错误。"
        elif score >= 40:
            return f"等级：{level} - 大部分单词正确，部分需要纠正。"
        else:
            return f"等级：{level} - 词汇基础需加强，建议每日跟读练习。"
    
    def _get_vocabulary_tags(self, score: float) -> List[str]:
        if score >= 80:
            return ["准确率高", "基础扎实"]
        elif score >= 60:
            return ["词汇良好", "偶有错误"]
        else:
            return ["需加强基础"]
    
    # ---- Sentence Comments & Tags ----
    def _get_sentence_comment(self, score: float) -> str:
        level = self._get_rating_level(score)
        if score >= 80:
            return f"等级：{level} - 能完整输出长句，逻辑清晰，句式多样。"
        elif score >= 60:
            return f"等级：{level} - 整句表达流畅，偶有自我纠正，连贯恰当。"
        elif score >= 40:
            return f"等级：{level} - 能用简单句回答，复杂句式需要加强。"
        else:
            return f"等级：{level} - 主要用词组回答，建议练习完整句子输出。"
    
    def _get_sentence_tags(self, score: float) -> List[str]:
        if score >= 80:
            return ["逻辑连贯", "句式多样"]
        elif score >= 60:
            return ["表达流畅", "自我纠正"]
        else:
            return ["需练习整句"]


class ParentReportService:
    """
    Generate complete parent report data.
    """
    
    def __init__(self):
        self.fusion_service = ScoreFusionService()
    
    def generate_report(
        self,
        student_name: str,
        level: str,
        total_score: float,
        star_level: int,
        part1_score: float,
        part2_score: float,
        part1_raw: Optional[dict],
        part2_raw: Optional[dict],
        part2_transcript: str,
        test_items: List[dict],
        interpretation: Optional[dict] = None
    ) -> ParentReportData:
        """
        Generate complete report data for parent H5.
        
        Args:
            student_name: Student's name
            level: Test level (e.g., "Level 2")
            total_score: Overall total score (0-100)
            star_level: Star level (1-5)
            part1_score: Part 1 total score (0-100)
            part2_score: Part 2 total score (0-100)
            part1_raw: Part 1 raw result dict from Qwen
            part2_raw: Part 2 raw result dict from Qwen
            part2_transcript: Part 2 transcript text
            test_items: List of test items (Part 2 questions)
            interpretation: Optional pre-generated interpretation
            
        Returns:
            ParentReportData object
        """
        # 1. Fuse radar scores
        radar = self.fusion_service.fuse_scores(part1_raw, part2_raw)
        
        # 2. Build Part 1 detail
        part1 = self._build_part1_detail(part1_score, part1_raw)
        
        # 3. Build Part 2 detail
        part2 = self._build_part2_detail(part2_score, part2_raw, part2_transcript, test_items)
        
        # 4. Build suggestions
        suggestion = self._build_suggestion(interpretation, radar)
        
        return ParentReportData(
            student=StudentInfo(name=student_name, level=level),
            overall=OverallScore(total_score=round(total_score, 1), star_level=star_level),
            radar=radar,
            part1=part1,
            part2=part2,
            suggestion=suggestion
        )
    
    def _build_part1_detail(self, score: float, raw: Optional[dict]) -> Part1Detail:
        """Build Part 1 detail from raw result."""
        words = []
        if raw and "details" in raw:
            for item in raw.get("details", []):
                word_score = item.get("score", 0)
                # Determine status based on score
                if word_score >= 80:
                    status = "perfect"
                elif word_score >= 50:
                    status = "unclear"
                else:
                    status = "failed"
                
                words.append(WordStatus(
                    text=item.get("content", ""),
                    status=status,
                    score=word_score
                ))
        
        return Part1Detail(score=round(score, 1), words=words)
    
    def _build_part2_detail(
        self,
        score: float,
        raw: Optional[dict],
        transcript: str,
        test_items: List[dict]
    ) -> Part2Detail:
        """Build Part 2 detail with best/weak samples."""
        best_sample = None
        weak_sample = None
        
        if test_items:
            # Sort by score to find best and worst
            sorted_items = sorted(test_items, key=lambda x: x.get("score", 0), reverse=True)
            
            # Best sample (highest score)
            if sorted_items:
                best = sorted_items[0]
                best_sample = DialogueSample(
                    question_no=best.get("question_no", 0),
                    question=best.get("question", ""),
                    answer=best.get("evidence", ""),
                    score=self._score_to_grade(best.get("score", 0)),
                    feedback=best.get("feedback", "表现优秀！")
                )
            
            # Weak sample (lowest score, but only if different from best)
            if len(sorted_items) > 1:
                weak = sorted_items[-1]
                if weak.get("score", 0) < sorted_items[0].get("score", 0):
                    weak_sample = DialogueSample(
                        question_no=weak.get("question_no", 0),
                        question=weak.get("question", ""),
                        answer=weak.get("evidence", ""),
                        score=self._score_to_grade(weak.get("score", 0)),
                        feedback=weak.get("feedback", "需要更多练习。")
                    )
        
        return Part2Detail(
            score=round(score, 1),
            best_sample=best_sample,
            weak_sample=weak_sample,
            transcript=transcript or ""
        )
    
    def _score_to_grade(self, score: int) -> str:
        """Convert 0-2 score to letter grade."""
        if score == 2:
            return "S"
        elif score == 1:
            return "A"
        else:
            return "B"
    
    def _build_suggestion(
        self,
        interpretation: Optional[dict],
        radar: List[RadarDimension]
    ) -> Suggestion:
        """Build suggestions from interpretation or generate from radar."""
        if interpretation:
            return Suggestion(
                highlights=interpretation.get("highlights", []),
                weaknesses=interpretation.get("weaknesses", []),
                plan=interpretation.get("suggestions", [])
            )
        
        # Generate basic suggestions from radar data
        highlights = []
        weaknesses = []
        plan = []
        
        # Find strengths (score >= 80) and weaknesses (score < 60)
        for dim in radar:
            if dim.score >= 80:
                highlights.append(f"{dim.subject}表现优秀")
            elif dim.score < 60:
                weaknesses.append(f"{dim.subject}有提升空间")
        
        # Default suggestions
        if not plan:
            plan = [
                "每天跟读 10 分钟标准音频",
                "多用完整句子回答问题",
                "保持自信，大声开口练习"
            ]
        
        return Suggestion(
            highlights=highlights or ["本次测评表现稳定"],
            weaknesses=weaknesses or ["暂无明显短板"],
            plan=plan
        )
