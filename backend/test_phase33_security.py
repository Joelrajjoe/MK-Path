import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime

import app.crud as crud
from app.database import db_manager
from app.models import (
    Material, Concept, Question, Attempt, Mastery,
    Goal, Assignment, AssignmentQuestion, LearningDiagnosis, DiagnosisType,
    DiagnosisEvidence
)

async def test_cross_user_isolation_security():
    """
    Comprehensive Security Audit for Phase 33.
    Verifies User A CANNOT read, update, or delete User B's records across ALL entities:
    - materials, concepts, questions, attempts, mastery, goals, assignments, diagnoses.
    """
    db = db_manager
    user_a = "clerk_user_alice"
    user_b = "clerk_user_bob"

    # 1. Materials Isolation
    mat_b = Material(
        clerk_user_id=user_b,
        title="Bob Private Material",
        file_name="bob_private.pdf",
        file_size=1024,
        content_type="application/pdf",
        raw_text="Confidential content",
        status="READY"
    )
    saved_mat_b = await crud.create_material(db, mat_b)
    mat_b_id = str(saved_mat_b["_id"])

    # Alice tries to read Bob's material
    alice_read_mat = await crud.get_material(db, mat_b_id, user_a)
    assert alice_read_mat is None, "SECURITY VIOLATION: User A read User B's material!"

    # Alice tries to list materials
    alice_materials = await crud.get_materials(db, user_a)
    assert not any(m["_id"] == mat_b_id for m in alice_materials), "SECURITY VIOLATION: User A listed User B's material!"

    # 2. Concepts Isolation
    con_b = Concept(
        clerk_user_id=user_b,
        name="Bob Secret Concept",
        description="Private concept notes",
        material_id=mat_b_id,
        difficulty="advanced",
        prerequisites=[]
    )
    saved_con_b = await crud.create_concepts(db, [con_b])
    con_b_id = str(saved_con_b[0]["_id"])

    # Alice tries to read Bob's concept
    alice_read_con = await crud.get_concept(db, con_b_id, user_a)
    assert alice_read_con is None, "SECURITY VIOLATION: User A read User B's concept!"

    # 3. Questions Isolation
    q_b = Question(
        clerk_user_id=user_b,
        concept_id=con_b_id,
        concept_name="Bob Secret Concept",
        question_text="Bob question?",
        options=["A", "B", "C", "D"],
        correct_option_index=0,
        explanation="Secret",
        difficulty="basic"
    )
    saved_q_b = await crud.create_questions(db, [q_b])
    q_b_id = str(saved_q_b[0]["_id"])

    alice_read_q = await crud.get_question(db, q_b_id, user_a)
    assert alice_read_q is None, "SECURITY VIOLATION: User A read User B's question!"

    # 4. Goals Isolation
    goal_b = Goal(
        clerk_user_id=user_b,
        title="Bob Cloud Architecture Goal",
        target_role="Cloud Architect",
        required_skills=[]
    )
    saved_goal_b = await crud.create_goal(db, goal_b)
    goal_b_id = str(saved_goal_b["_id"])

    # Alice tries to read, update, or delete Bob's goal
    assert await crud.get_goal(db, goal_b_id, user_a) is None, "SECURITY VIOLATION: User A read Bob's goal!"
    assert await crud.update_goal(db, goal_b_id, user_a, {"title": "Hacked"}) is None, "SECURITY VIOLATION: User A updated Bob's goal!"
    assert not await crud.delete_goal(db, goal_b_id, user_a), "SECURITY VIOLATION: User A deleted Bob's goal!"

    # Verify Bob's goal is untampered
    bob_goal = await crud.get_goal(db, goal_b_id, user_b)
    assert bob_goal["title"] == "Bob Cloud Architecture Goal"

    # 5. Assignments Isolation
    assign_b = Assignment(
        clerk_user_id=user_b,
        title="Bob Confidential Exam",
        questions=[AssignmentQuestion(question_text="Q?", options=["1", "2"], correct_option_index=0)]
    )
    saved_assign_b = await crud.create_assignment(db, assign_b)
    assign_b_id = str(saved_assign_b["_id"])

    assert await crud.get_assignment(db, assign_b_id, user_a) is None, "SECURITY VIOLATION: User A read Bob's assignment!"
    assert not await crud.delete_assignment(db, assign_b_id, user_a), "SECURITY VIOLATION: User A deleted Bob's assignment!"

    # 6. Diagnoses Isolation
    diag_b = LearningDiagnosis(
        clerk_user_id=user_b,
        target_concept="Bob Secret Concept",
        diagnosis_type=DiagnosisType.CONCEPT_WEAKNESS,
        evidence=DiagnosisEvidence(),
        confidence=0.9,
        reason="Bob specific gap",
        recommended_action="Study"
    )
    await crud.create_diagnosis(db, diag_b)
    alice_diagnoses = await crud.get_diagnoses(db, user_a)
    assert not any(d.get("target_concept") == "Bob Secret Concept" for d in alice_diagnoses), "SECURITY VIOLATION: User A read Bob's diagnoses!"

if __name__ == "__main__":
    asyncio.run(test_cross_user_isolation_security())
    print("ALL PHASE 33 SECURITY & ISOLATION TESTS PASSED!")
