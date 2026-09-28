import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.models import MasteryEvidenceChain
from app.services.mastery_evidence_service import MasteryEvidenceChainService

async def test_mastery_evidence_full_chain():
    service = MasteryEvidenceChainService()
    user_id = "test_user_ev_1"
    concept_id = "c_trees"

    mock_concept = {"id": "c_trees", "name": "Binary Trees"}
    mock_mastery = {
        "concept_id": "c_trees",
        "concept_name": "Binary Trees",
        "mastery_score": 63.0,
        "bkt_probability": 0.65,
        "bkt_uncertainty": 0.12
    }

    # 7 recent attempts: 5 correct, 2 incorrect, avg conf: 3.6, median rt: 22s
    mock_attempts = [
        {"_id": "a1", "concept_id": "c_trees", "is_correct": True, "confidence": 4, "response_time_seconds": 20.0, "created_at": datetime.utcnow() - timedelta(days=2)},
        {"_id": "a2", "concept_id": "c_trees", "is_correct": True, "confidence": 3, "response_time_seconds": 22.0, "created_at": datetime.utcnow() - timedelta(days=2)},
        {"_id": "a3", "concept_id": "c_trees", "is_correct": False, "confidence": 3, "response_time_seconds": 25.0, "created_at": datetime.utcnow() - timedelta(days=1)},
        {"_id": "a4", "concept_id": "c_trees", "is_correct": True, "confidence": 4, "response_time_seconds": 21.0, "created_at": datetime.utcnow() - timedelta(days=1)},
        {"_id": "a5", "concept_id": "c_trees", "is_correct": True, "confidence": 4, "response_time_seconds": 18.0, "created_at": datetime.utcnow() - timedelta(hours=12)},
        {"_id": "a6", "concept_id": "c_trees", "is_correct": False, "confidence": 3, "response_time_seconds": 30.0, "created_at": datetime.utcnow() - timedelta(hours=6)},
        {"_id": "a7", "concept_id": "c_trees", "is_correct": True, "confidence": 4, "response_time_seconds": 22.0, "created_at": datetime.utcnow() - timedelta(hours=1)}
    ]

    with patch("app.crud.get_concept", new=AsyncMock(return_value=mock_concept)), \
         patch("app.crud.get_mastery_by_concept", new=AsyncMock(return_value=mock_mastery)), \
         patch("app.crud.get_attempts", new=AsyncMock(return_value=mock_attempts)):

        chain: MasteryEvidenceChain = await service.get_mastery_evidence(user_id, concept_id)

        assert chain.concept_name == "Binary Trees"
        assert chain.current_mastery == 63.0
        assert chain.correct_attempts_count == 5
        assert chain.total_attempts_count == 7
        assert chain.is_insufficient_evidence is False
        assert "5/7 recent answers were correct" in chain.explanation
        assert "Median response time: 22.0 seconds" in chain.explanation
        assert "Current validated mastery: 63.0%" in chain.explanation

async def test_mastery_evidence_insufficient_data():
    service = MasteryEvidenceChainService()
    user_id = "test_user_ev_2"
    concept_id = "c_quantum"

    with patch("app.crud.get_concept", new=AsyncMock(return_value=None)), \
         patch("app.crud.get_mastery_by_concept", new=AsyncMock(return_value=None)), \
         patch("app.crud.get_mastery", new=AsyncMock(return_value=[])), \
         patch("app.crud.get_attempts", new=AsyncMock(return_value=[])):

        chain: MasteryEvidenceChain = await service.get_mastery_evidence(user_id, concept_id)

        assert chain.is_insufficient_evidence is True
        assert "INSUFFICIENT EVIDENCE" in chain.explanation
        assert chain.current_mastery == 0.0

if __name__ == "__main__":
    asyncio.run(test_mastery_evidence_full_chain())
    asyncio.run(test_mastery_evidence_insufficient_data())
    print("ALL PHASE 30 MASTERY EVIDENCE TESTS PASSED!")
