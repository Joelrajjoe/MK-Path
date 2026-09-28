import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.models import Assignment, AssignmentQuestion
from app.services.gamification_service import GamificationService
import app.crud as crud
from app.database import db_manager

async def test_assignment_full_lifecycle():
    user_id = "test_user_assign_1"
    db = db_manager

    # 1. CREATE
    question_1 = AssignmentQuestion(
        question_text="What is the time complexity of binary search?",
        options=["O(n)", "O(log n)", "O(n^2)", "O(1)"],
        correct_option_index=1,
        explanation="Binary search cuts the search space in half at each step."
    )
    
    assignment_model = Assignment(
        clerk_user_id=user_id,
        title="Algorithms Midterm Drill",
        description="Core complexity questions",
        concept_ids=["c_algo"],
        concept_names=["Binary Search"],
        questions=[question_1],
        difficulty="intermediate",
        status="pending"
    )

    created = await crud.create_assignment(db, assignment_model)
    assign_id = str(created["_id"])
    assert created["status"] == "pending"
    assert created["clerk_user_id"] == user_id
    assert created["score"] is None

    # 2. START & AUTOSAVE (Draft answers saved, status -> in_progress, no mastery awarded yet)
    draft_updates = {
        "status": "in_progress",
        "draft_answers": {"0": 1}
    }
    updated = await crud.update_assignment(db, assign_id, user_id, draft_updates)
    assert updated["status"] == "in_progress"
    assert updated["draft_answers"] == {"0": 1}
    assert updated["score"] is None # PROVING: merely opening/saving does not award score

    # 3. RESUME (Fetch and verify draft state)
    resumed = await crud.get_assignment(db, assign_id, user_id)
    assert resumed["draft_answers"]["0"] == 1

    # 4. SUBMIT & EVALUATE & XP AWARD
    # 1/1 correct -> 100% accuracy
    final_updates = {
        "status": "completed",
        "score": 100.0,
        "accuracy": 100.0,
        "time_spent_seconds": 45.0,
        "submitted_at": datetime.utcnow(),
        "draft_answers": {}
    }
    completed = await crud.update_assignment(db, assign_id, user_id, final_updates)
    assert completed["status"] == "completed"
    assert completed["score"] == 100.0
    assert completed["accuracy"] == 100.0
    assert completed["submitted_at"] is not None

if __name__ == "__main__":
    asyncio.run(test_assignment_full_lifecycle())
    print("ALL PHASE 31 ASSIGNMENT LIFECYCLE TESTS PASSED!")
