import pytest
from src.use_cases.parent_report import ScoreFusionService, ParentReportService, ParentReportData

class TestScoreFusionService:
    @pytest.fixture
    def service(self):
        return ScoreFusionService()

    def test_fuse_scores_full_data(self, service):
        """Test fusion when both parts have data."""
        part1_raw = {
            "fluency_score": 80,
            "pronunciation_score": 90,
            "accuracy_score": 70,
            "integrity_score": 100
        }
        part2_raw = {
            "fluency_score": 90,
            "pronunciation_score": 80,
            "confidence_score": 95,
            "vocabulary_score": 85,
            "sentence_score": 75
        }
        
        radar = service.fuse_scores(part1_raw, part2_raw)
        
        # Fluency: 80 * 0.4 + 90 * 0.6 = 32 + 54 = 86
        assert radar[0].subject == "流利度"
        assert radar[0].score == 86.0
        
        # Pronunciation: 90 * 0.4 + 80 * 0.6 = 36 + 48 = 84
        assert radar[1].subject == "发音"
        assert radar[1].score == 84.0
        
        # Confidence: Only Part 2 = 95
        assert radar[2].subject == "自信度"
        assert radar[2].score == 95.0
        
        # Vocabulary: 70 * 0.3 + 85 * 0.7 = 21 + 59.5 = 80.5
        assert radar[3].subject == "词汇"
        assert radar[3].score == 80.5
        
        # Sentence: 100 * 0.2 + 75 * 0.8 = 20 + 60 = 80
        assert radar[4].subject == "整句输出"
        assert radar[4].score == 80.0

    def test_fuse_scores_missing_part1(self, service):
        """Test fusion when Part 1 is missing."""
        part1_raw = None
        part2_raw = {
            "fluency_score": 90,
            "pronunciation_score": 80,
            "confidence_score": 95,
            "vocabulary_score": 85,
            "sentence_score": 75
        }
        
        radar = service.fuse_scores(part1_raw, part2_raw)
        
        # Should use Part 2 scores directly as per _fuse implementation
        assert radar[0].score == 90.0
        assert radar[1].score == 80.0
        assert radar[2].score == 95.0
        assert radar[3].score == 85.0
        assert radar[4].score == 75.0

    def test_fuse_scores_missing_part2(self, service):
        """Test fusion when Part 2 is missing."""
        part1_raw = {
            "fluency_score": 80,
            "pronunciation_score": 90,
            "accuracy_score": 70,
            "integrity_score": 100
        }
        part2_raw = None
        
        radar = service.fuse_scores(part1_raw, part2_raw)
        
        # Should use Part 1 scores directly (except Confidence which will be 0)
        assert radar[0].score == 80.0
        assert radar[1].score == 90.0
        assert radar[2].score == 0.0
        assert radar[3].score == 70.0
        assert radar[4].score == 100.0

class TestParentReportService:
    @pytest.fixture
    def service(self):
        return ParentReportService()

    def test_generate_report_basic(self, service):
        """Test the full report generation with mock data."""
        part1_raw = {
            "details": [
                {"content": "apple", "score": 95},
                {"content": "banana", "score": 60},
                {"content": "cherry", "score": 30}
            ]
        }
        part2_items = [
            {"question_no": 1, "question": "Q1", "evidence": "Ans 1", "score": 2, "feedback": "Good"},
            {"question_no": 2, "question": "Q2", "evidence": "Ans 2", "score": 0, "feedback": "Poor"}
        ]
        
        report = service.generate_report(
            student_name="小明",
            level="L2",
            total_score=85.5,
            star_level=4,
            part1_score=80.0,
            part2_score=91.0,
            part1_raw=part1_raw,
            part2_raw={"fluency_score": 90},
            part2_transcript="Hello world",
            test_items=part2_items
        )
        
        assert isinstance(report, ParentReportData)
        assert report.student.name == "小明"
        assert report.overall.star_level == 4
        
        # Check Part 1 words
        assert len(report.part1.words) == 3
        assert report.part1.words[0].status == "perfect"
        assert report.part1.words[1].status == "unclear"
        assert report.part1.words[2].status == "failed"
        
        # Check Part 2 samples
        assert report.part2.best_sample.question_no == 1
        assert report.part2.best_sample.score == "S"
        assert report.part2.weak_sample.question_no == 2
        assert report.part2.weak_sample.score == "B"
        
        # Check default suggestions (since no interpretation provided)
        assert len(report.suggestion.plan) == 3
        assert "流利度表现优秀" in report.suggestion.highlights or "本次测评表现稳定" in report.suggestion.highlights
