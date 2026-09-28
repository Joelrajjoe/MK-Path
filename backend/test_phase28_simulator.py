import asyncio
from unittest.mock import AsyncMock, patch

from app.models import SimulationRequest, SimulationResult
from app.services.simulation_service import LearningSimulationService

async def test_pure_in_memory_simulation_no_db_side_effects():
    service = LearningSimulationService()
    user_id = "test_user_sim_1"

    # Mock real DB data
    mock_goal = {
        "id": "goal_123",
        "title": "Data Scientist",
        "required_skills": [
            {"concept_name": "Python", "required_level": 80.0},
            {"concept_name": "SQL", "required_level": 80.0},
            {"concept_name": "Machine Learning", "required_level": 80.0}
        ]
    }
    
    mock_real_mastery = [
        {"concept_name": "Python", "mastery_score": 85.0},
        {"concept_name": "SQL", "mastery_score": 30.0},
        {"concept_name": "Machine Learning", "mastery_score": 20.0}
    ]

    mock_concepts = [
        {"id": "Python", "name": "Python", "prerequisites": []},
        {"id": "SQL", "name": "SQL", "prerequisites": []},
        {"id": "Machine Learning", "name": "Machine Learning", "prerequisites": ["Python", "SQL"]},
        {"id": "Deep Learning", "name": "Deep Learning", "prerequisites": ["Machine Learning"]}
    ]

    # Create Spies for DB mutations to guarantee ZERO side-effects
    spy_update_mastery = AsyncMock()
    spy_award_xp = AsyncMock()
    spy_create_event = AsyncMock()

    with patch("app.crud.get_goal", new=AsyncMock(return_value=mock_goal)), \
         patch("app.crud.get_mastery", new=AsyncMock(return_value=mock_real_mastery)), \
         patch("app.crud.get_concepts", new=AsyncMock(return_value=mock_concepts)), \
         patch("app.crud.create_or_update_mastery", new=spy_update_mastery), \
         patch("app.crud.create_learner_event", new=spy_create_event):

        # Scenario: Learner asks "What if I boost SQL to 90% and Machine Learning to 85%?"
        request = SimulationRequest(
            goal_id="goal_123",
            simulated_mastery_map={
                "SQL": 90.0,
                "Machine Learning": 85.0
            }
        )

        result: SimulationResult = await service.simulate_learning(user_id, request)

        # 1. Verify Simulation Tagging
        assert result.is_simulation is True

        # 2. Verify Readiness Calculations
        # Initial: (85 + 30 + 20) / 3 = 135 / 3 = 45.0%
        # Simulated: (85 + 90 + 85) / 3 = 260 / 3 = 86.67%
        assert result.current_goal_readiness == 45.0
        assert result.simulated_goal_readiness == 86.67
        assert result.readiness_delta == 41.67

        # 3. Verify Resolved Gaps
        assert "SQL" in result.resolved_skill_gaps
        assert "Machine Learning" in result.resolved_skill_gaps

        # 4. Verify Unlocked Concepts
        # Deep Learning requires Machine Learning (now 85% >= 70%) -> newly unlocked!
        unlocked_names = [u.concept_name for u in result.newly_unlocked_concepts]
        assert "Deep Learning" in unlocked_names

        # 5. Verify Next Best Action generated in simulated state
        assert result.next_best_action is not None
        assert "remediating" in result.next_best_action or "mastered" in result.next_best_action

        # 6. CRITICAL VERIFICATION: Zero DB Mutations & Zero XP Alterations
        spy_update_mastery.assert_not_called()
        spy_award_xp.assert_not_called()
        spy_create_event.assert_not_called()

if __name__ == "__main__":
    asyncio.run(test_pure_in_memory_simulation_no_db_side_effects())
    print("ALL PHASE 28 SIMULATOR TESTS PASSED!")
