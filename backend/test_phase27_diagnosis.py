import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from app.models import DiagnosisType, LearningDiagnosis
from app.services.diagnosis_service import LearningDiagnosisService

async def test_insufficient_evidence_single_attempt():
    service = LearningDiagnosisService()
    user_id = "test_user_p27_1"
    
    with patch("app.crud.get_concept", new=AsyncMock(return_value={"id": "c1", "prerequisites": []})), \
         patch("app.crud.get_attempts", new=AsyncMock(return_value=[])), \
         patch("app.crud.get_mastery_by_concept", new=AsyncMock(return_value=None)), \
         patch("app.crud.create_diagnosis", new=AsyncMock(return_value={"id": "diag1"})):
        
        diag = await service.diagnose_learner(
            user_id=user_id,
            concept_id="c1",
            question="What is a variable?",
            answer="A number",
            correct_answer="A named storage location",
            confidence=3
        )
        assert diag.diagnosis_type == DiagnosisType.INSUFFICIENT_EVIDENCE
        assert "Only 1 single attempt" in diag.reason

async def test_confidence_mismatch_overconfidence():
    service = LearningDiagnosisService()
    user_id = "test_user_p27_2"
    
    with patch("app.crud.get_concept", new=AsyncMock(return_value={"id": "c2", "prerequisites": []})), \
         patch("app.crud.get_attempts", new=AsyncMock(return_value=[{"concept_id": "c2", "is_correct": False}, {"concept_id": "c2", "is_correct": False}])), \
         patch("app.crud.get_mastery_by_concept", new=AsyncMock(return_value={"mastery_score": 40.0})), \
         patch("app.crud.create_diagnosis", new=AsyncMock(return_value={"id": "diag2"})):
        
        diag = await service.diagnose_learner(
            user_id=user_id,
            concept_id="c2",
            question="Does Python use pointers?",
            answer="Yes explicitly",
            correct_answer="No, reference model",
            confidence=5 # Very high confidence but incorrect!
        )
        assert diag.diagnosis_type == DiagnosisType.CONFIDENCE_MISMATCH
        assert "High confidence" in diag.reason

async def test_retention_decay():
    service = LearningDiagnosisService()
    user_id = "test_user_p27_3"
    
    # Last reviewed 20 days ago
    old_date = (datetime.utcnow() - timedelta(days=20)).isoformat()
    
    with patch("app.crud.get_concept", new=AsyncMock(return_value={"id": "c3", "prerequisites": []})), \
         patch("app.crud.get_attempts", new=AsyncMock(return_value=[{"concept_id": "c3"}, {"concept_id": "c3"}])), \
         patch("app.crud.get_mastery_by_concept", new=AsyncMock(return_value={"mastery_score": 85.0, "last_reviewed": old_date})), \
         patch("app.crud.create_diagnosis", new=AsyncMock(return_value={"id": "diag3"})):
        
        diag = await service.diagnose_learner(
            user_id=user_id,
            concept_id="c3",
            question="What is Dijkstra's algorithm?",
            answer="Sorting",
            correct_answer="Shortest path",
            confidence=2
        )
        assert diag.diagnosis_type == DiagnosisType.RETENTION_DECAY
        assert "Ebbinghaus" in diag.reason

async def test_prerequisite_weakness():
    service = LearningDiagnosisService()
    user_id = "test_user_p27_4"
    
    async def mock_mastery(db, cid, uid):
        if cid == "Recursion":
            return {"mastery_score": 40.0}
        elif cid == "Functions":
            return {"mastery_score": 35.0} # Weak prerequisite!
        return None

    with patch("app.crud.get_concept", new=AsyncMock(return_value={"id": "Recursion", "prerequisites": ["Functions"]})), \
         patch("app.crud.get_attempts", new=AsyncMock(return_value=[{"concept_id": "Recursion", "is_correct": False}, {"concept_id": "Recursion", "is_correct": False}])), \
         patch("app.crud.get_mastery_by_concept", side_effect=mock_mastery), \
         patch("app.crud.create_diagnosis", new=AsyncMock(return_value={"id": "diag4"})):
        
        diag = await service.diagnose_learner(
            user_id=user_id,
            concept_id="Recursion",
            prerequisites=["Functions"],
            question="Base case check",
            answer="None",
            correct_answer="if n == 0",
            confidence=3
        )
        assert diag.diagnosis_type == DiagnosisType.PREREQUISITE_WEAKNESS
        assert diag.suspected_root_concept == "Functions"

async def test_recurring_misconception():
    service = LearningDiagnosisService()
    user_id = "test_user_p27_5"
    
    # 2 past attempts picking wrong option "B"
    past_attempts = [
        {"concept_id": "c5", "is_correct": False, "selected_answer": "Option B"},
        {"concept_id": "c5", "is_correct": False, "selected_answer": "Option B"}
    ]
    
    with patch("app.crud.get_concept", new=AsyncMock(return_value={"id": "c5", "prerequisites": []})), \
         patch("app.crud.get_attempts", new=AsyncMock(return_value=past_attempts)), \
         patch("app.crud.get_mastery_by_concept", new=AsyncMock(return_value={"mastery_score": 45.0})), \
         patch("app.crud.create_diagnosis", new=AsyncMock(return_value={"id": "diag5"})):
        
        diag = await service.diagnose_learner(
            user_id=user_id,
            concept_id="c5",
            question="Question 3",
            answer="Option B",
            correct_answer="Option A",
            confidence=3
        )
        assert diag.diagnosis_type == DiagnosisType.RECURRING_MISCONCEPTION
        assert "Option B" in diag.reason

if __name__ == "__main__":
    asyncio.run(test_insufficient_evidence_single_attempt())
    asyncio.run(test_confidence_mismatch_overconfidence())
    asyncio.run(test_retention_decay())
    asyncio.run(test_prerequisite_weakness())
    asyncio.run(test_recurring_misconception())
    print("ALL PHASE 27 TESTS PASSED!")
