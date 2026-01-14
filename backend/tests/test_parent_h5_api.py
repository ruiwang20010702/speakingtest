import pytest
from src.adapters.repositories.models import TestModel, ReportShareTokenModel, TestItemModel
from src.use_cases.parent_report import ParentReportData

class TestParentH5API:
    """Integration tests for the Parent H5 Report API."""

    @pytest.mark.asyncio
    async def test_get_parent_h5_report_success(self, client, test_db, teacher_user, student_profile):
        """Test successful retrieval of H5 report data via token."""
        # 1. Create a completed test record with raw results
        test = TestModel(
            student_id=student_profile.user_id,
            level="L2",
            unit="Unit 1",
            status="completed",
            part1_score=85.0,
            part2_score=90.0,
            total_score=87.5,
            star_level=4,
            part1_raw_result={
                "accuracy_score": 80,
                "fluency_score": 85,
                "pronunciation_score": 90,
                "integrity_score": 88,
                "details": [{"content": "apple", "score": 90}]
            },
            part2_raw_result={
                "fluency_score": 92,
                "pronunciation_score": 88,
                "confidence_score": 95,
                "vocabulary_score": 85,
                "sentence_score": 80
            },
            part2_transcript="Hello, how are you today?"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        # Add a test item (Part 2 question)
        item = TestItemModel(
            test_id=test.id,
            question_no=1,
            score=2,
            feedback="Perfect answer.",
            evidence="I am doing great, thank you."
        )
        test_db.add(item)
        await test_db.commit()

        # 2. Create a share token
        share = ReportShareTokenModel(
            token="h5-test-token-999",
            test_id=test.id,
            created_by=teacher_user.id,
            is_revoked=False
        )
        test_db.add(share)
        await test_db.commit()

        # 3. Call the H5 report API
        response = await client.get("/api/v1/reports/h5-test-token-999/h5")
        
        # 4. Verify the results
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure (based on ParentReportData Pydantic model)
        assert data["student"]["name"] == student_profile.student_name
        assert data["overall"]["total_score"] == 87.5
        assert data["overall"]["star_level"] == 4
        
        # Verify Radar (5 dimensions)
        assert len(data["radar"]) == 5
        subjects = [d["subject"] for d in data["radar"]]
        assert "流利度" in subjects
        assert "发音" in subjects
        
        # Verify Part 1
        assert len(data["part1"]["words"]) == 1
        assert data["part1"]["words"][0]["text"] == "apple"
        
        # Verify Part 2
        assert data["part2"]["score"] == 90.0
        assert data["part2"]["best_sample"]["question_no"] == 1
        assert data["part2"]["best_sample"]["score"] == "S"

    @pytest.mark.asyncio
    async def test_get_parent_h5_report_not_found(self, client):
        """Test API returns 404 for invalid token."""
        response = await client.get("/api/v1/reports/non-existent-token/h5")
        assert response.status_code == 404
        # The error message is in Chinese: '链接无效或已过期'
        assert "链接无效" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_parent_h5_report_revoked(self, client, test_db, teacher_user, student_profile):
        """Test API returns 404 or 403 for revoked token."""
        test = TestModel(
            student_id=student_profile.user_id,
            level="L1", unit="U1", status="completed"
        )
        test_db.add(test)
        await test_db.commit()
        await test_db.refresh(test)

        share = ReportShareTokenModel(
            token="revoked-token-h5",
            test_id=test.id,
            created_by=teacher_user.id,
            is_revoked=True
        )
        test_db.add(share)
        await test_db.commit()

        response = await client.get("/api/v1/reports/revoked-token-h5/h5")
        # According to controller logic, it returns 404 if not found OR revoked
        assert response.status_code == 404
