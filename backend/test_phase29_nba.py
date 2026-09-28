import asyncio
from unittest.mock import AsyncMock, patch

from app.models import ActionType, NextBestActionRecommendation
from app.services.nba_service import NextBestLearningActionService

async def test_nba_prerequisite_remediation_priority():
    service = NextBestLearningActionService()
    user_id = "test_user_nba_1"

    # Scenario: Learner has diagnosis showing struggles in "JOINs" due to "Relational Keys"
    mock_diagnosis = [{
        "diagnosis_type": "PREREQUISITE_WEAKNESS",
        "target_concept": "JOINs",
        "suspected_root_concept": "Relational Keys"
    }]

    mock_concepts = [
        {"id": "c1", "name": "Relational Keys", "prerequisites": []},
        {"id": "c2", "name": "JOINs", "prerequisites": ["Relational Keys"]}
    ]

    mock_mastery = [
        {"concept_name": "Relational Keys", "mastery_score": 41.0},
        {"concept_name": "JOINs", "mastery_score": 48.0}
    ]

    with patch("app.crud.get_goals", new=AsyncMock(return_value=[])), \
         patch("app.crud.get_concepts", new=AsyncMock(return_value=mock_concepts)), \
         patch("app.crud.get_mastery", new=AsyncMock(return_value=mock_mastery)), \
         patch("app.crud.get_diagnoses", new=AsyncMock(return_value=mock_diagnosis)), \
         patch("app.crud.get_assignments", new=AsyncMock(return_value=[])):

        nba: NextBestActionRecommendation = await service.compute_next_best_action(user_id)

        assert nba.action_type == ActionType.REVIEW
        assert nba.concept_id == "Relational Keys"
        assert "Relational Keys" in nba.reason
        assert nba.priority >= 90.0

async def test_nba_goal_gap_practice_recommendation():
    service = NextBestLearningActionService()
    user_id = "test_user_nba_2"

    # Goal requires SQL at 80% (currently 35%)
    mock_goal = {
        "id": "g1",
        "title": "Backend Dev",
        "required_skills": [{"concept_name": "SQL", "required_level": 80.0, "weight": 1.0}]
    }

    mock_concepts = [
        {"id": "c_sql", "name": "SQL", "prerequisites": []}
    ]

    mock_mastery = [
        {"concept_name": "SQL", "mastery_score": 35.0}
    ]

    with patch("app.crud.get_goals", new=AsyncMock(return_value=[mock_goal])), \
         patch("app.crud.get_concepts", new=AsyncMock(return_value=mock_concepts)), \
         patch("app.crud.get_mastery", new=AsyncMock(return_value=mock_mastery)), \
         patch("app.crud.get_diagnoses", new=AsyncMock(return_value=[])), \
         patch("app.crud.get_assignments", new=AsyncMock(return_value=[])):

        nba: NextBestActionRecommendation = await service.compute_next_best_action(user_id)

        assert nba.action_type == ActionType.PRACTICE
        assert nba.concept_name == "SQL"
        assert "Interactive practice is required" in nba.reason

if __name__ == "__main__":
    asyncio.run(test_nba_prerequisite_remediation_priority())
    asyncio.run(test_nba_goal_gap_practice_recommendation())
    print("ALL PHASE 29 NBA TESTS PASSED!")
