import asyncio
import sys
import os
from datetime import datetime

# Adjust Python path to backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import DatabaseManager
from app.models import Goal, RequiredSkill, Mastery, Relationship, Concept, Attempt
from app import crud
from app.services.goal_service import GoalGapAnalysisService
from app.services.neo4j_service import neo4j_service

async def run_tests():
    print("=================================================================")
    print("PHASE 26: MK-PATH GOAL-TO-SKILL GAP INTELLIGENCE TEST HARNESS")
    print("=================================================================")

    db = DatabaseManager()
    user_a = "user_phase26_alice"
    user_b = "user_phase26_bob"

    # Reset demo database state for test users
    crud._DEMO_DB["goals"] = []
    crud._DEMO_DB["mastery"] = []
    crud._DEMO_DB["relationships"] = []
    crud._DEMO_DB["concepts"] = []
    crud._DEMO_DB["attempts"] = []
    neo4j_service.in_memory_nodes = {}
    neo4j_service.in_memory_edges = {}

    print("\n--- TEST 1: Goal Creation & Persistence ---")
    goal_data = Goal(
        clerk_user_id=user_a,
        title="Data Analyst",
        description="Master business intelligence, statistical modeling, and data pipelines.",
        target_role="Data Analyst",
        target_exam="PL-300",
        required_skills=[
            RequiredSkill(name="Power BI", required_level=80.0, source="verified_system_mapping", weight=2.0),
            RequiredSkill(name="Statistics", required_level=75.0, source="verified_system_mapping", weight=1.5),
            RequiredSkill(name="Python Data Analysis", required_level=85.0, source="learner_defined", weight=1.0),
            RequiredSkill(name="SQL Querying", required_level=90.0, source="ai_suggested", weight=2.5)
        ]
    )
    created_goal = await crud.create_goal(db, goal_data)
    assert created_goal is not None, "Goal creation failed"
    goal_id = str(created_goal["_id"])
    print(f"Goal created successfully with ID: {goal_id}")
    assert len(created_goal["required_skills"]) == 4

    print("\n--- TEST 2: User Isolation (Cross-User Data Protection) ---")
    bob_goals = await crud.get_goals(db, user_b)
    assert len(bob_goals) == 0, "Bob should not see Alice's goals"
    bob_attempt_get = await crud.get_goal(db, goal_id, user_b)
    assert bob_attempt_get is None, "Bob cannot access Alice's goal by ID"
    print("User isolation verified: cross-user access strictly blocked.")

    print("\n--- TEST 3: Goal Gap Analysis - Baseline / Insufficient Evidence ---")
    # At this point, Alice has no attempts or mastery records
    analysis_empty = await GoalGapAnalysisService.analyze_goal_gaps(db, user_a, created_goal)
    assert analysis_empty.overall_readiness_score == 0.0, "Readiness score should be 0 with no learner state"
    assert analysis_empty.status == "NOT_STARTED"
    for s in analysis_empty.skills:
        assert s.status == "INSUFFICIENT_EVIDENCE", f"Expected INSUFFICIENT_EVIDENCE for {s.skill_name}, got {s.status}"
        assert s.evidence_strength == "none"
        assert s.gap == s.required_level
    print(f"Empty state correctly evaluated as {analysis_empty.status} with 4 INSUFFICIENT_EVIDENCE skills.")

    print("\n--- TEST 4: Prerequisite Blocking and Needs Improvement Computation ---")
    # Setup scenario:
    # 1. 'Probability Fundamentals' is prerequisite for 'Statistics'
    # 2. Alice has low mastery in 'Probability Fundamentals' (35%) -> Should BLOCK 'Statistics'
    # 3. Alice has some mastery in 'Power BI' (42%) with attempts and no unmet prerequisites -> NEEDS_IMPROVEMENT
    # 4. Alice has mastered 'SQL Querying' (95%) -> MASTERED

    # Seed relationships
    rel = Relationship(
        clerk_user_id=user_a,
        source_concept_name="Probability Fundamentals",
        target_concept_name="Statistics",
        relationship_type="PREREQUISITE_OF"
    )
    await crud.create_relationships(db, [rel])
    await neo4j_service.sync_relationship(user_a, rel.model_dump())

    # Seed mastery docs
    m_prob = Mastery(
        clerk_user_id=user_a,
        concept_id="c_prob_01",
        concept_name="Probability Fundamentals",
        mastery_score=35.0,
        category="Weak"
    )
    m_pbi = Mastery(
        clerk_user_id=user_a,
        concept_id="c_pbi_01",
        concept_name="Power BI",
        mastery_score=42.0,
        category="Learning"
    )
    m_stat = Mastery(
        clerk_user_id=user_a,
        concept_id="c_stat_01",
        concept_name="Statistics",
        mastery_score=31.0,
        category="Weak"
    )
    m_sql = Mastery(
        clerk_user_id=user_a,
        concept_id="c_sql_01",
        concept_name="SQL Querying",
        mastery_score=95.0,
        category="Mastered"
    )
    for m in [m_prob, m_pbi, m_stat, m_sql]:
        await crud.create_or_update_mastery(db, m)

    # Seed attempts for Power BI to create evidence
    for i in range(3):
        att = Attempt(
            clerk_user_id=user_a,
            concept_id="c_pbi_01",
            question_id=f"q_{i}",
            concept_name="Power BI",
            selected_option_index=1,
            is_correct=True,
            confidence=4,
            response_time_seconds=7.0
        )
        await crud.create_attempt(db, att)

    # Run analysis
    analysis = await GoalGapAnalysisService.analyze_goal_gaps(db, user_a, created_goal)

    skills_dict = {s.skill_name: s for s in analysis.skills}

    # Verify Power BI
    pbi_gap = skills_dict["Power BI"]
    print(f"\nPower BI: Required {pbi_gap.required_level}, Current {pbi_gap.current_mastery}, Gap {pbi_gap.gap}, Status: {pbi_gap.status}")
    assert pbi_gap.gap == 38.0, f"Expected gap 38.0, got {pbi_gap.gap}"
    assert pbi_gap.status == "NEEDS_IMPROVEMENT", f"Expected NEEDS_IMPROVEMENT, got {pbi_gap.status}"
    assert pbi_gap.evidence_strength in ("moderate", "high")

    # Verify Statistics
    stat_gap = skills_dict["Statistics"]
    print(f"Statistics: Required {stat_gap.required_level}, Current {stat_gap.current_mastery}, Gap {stat_gap.gap}, Status: {stat_gap.status}")
    assert stat_gap.status == "BLOCKED_BY_PREREQUISITE", f"Expected BLOCKED_BY_PREREQUISITE, got {stat_gap.status}"
    assert len(stat_gap.unmet_prerequisites) > 0
    assert "Probability Fundamentals" in stat_gap.unmet_prerequisites[0]

    # Verify SQL Querying
    sql_gap = skills_dict["SQL Querying"]
    print(f"SQL Querying: Required {sql_gap.required_level}, Current {sql_gap.current_mastery}, Gap {sql_gap.gap}, Status: {sql_gap.status}")
    assert sql_gap.status == "MASTERED"
    assert sql_gap.gap == 0.0

    # Verify Python Data Analysis
    py_gap = skills_dict["Python Data Analysis"]
    print(f"Python Data Analysis: Required {py_gap.required_level}, Current {py_gap.current_mastery}, Gap {py_gap.gap}, Status: {py_gap.status}")
    assert py_gap.status == "INSUFFICIENT_EVIDENCE"

    print(f"\nOverall Readiness Score: {analysis.overall_readiness_score}% (Status: {analysis.status})")
    print(f"Recommended Focus Skill: {analysis.recommended_focus_skill}")
    assert analysis.overall_readiness_score > 0.0
    assert analysis.recommended_focus_skill in ("Power BI", "Python Data Analysis")

    print("\n--- TEST 5: Goal Update & Delete CRUD Operations ---")
    updated_goal = await crud.update_goal(db, goal_id, user_a, {"title": "Senior Data Analyst", "target_exam": "PL-300 & DP-500"})
    assert updated_goal["title"] == "Senior Data Analyst"
    assert updated_goal["target_exam"] == "PL-300 & DP-500"

    delete_success = await crud.delete_goal(db, goal_id, user_a)
    assert delete_success is True, "Failed to delete goal"
    assert await crud.get_goal(db, goal_id, user_a) is None, "Deleted goal still retrievable"
    print("Goal update and delete CRUD verified successfully.")

    print("\n=================================================================")
    print("ALL PHASE 26 GOAL-TO-SKILL GAP INTELLIGENCE TESTS PASSED (5/5)!")
    print("=================================================================\n")

if __name__ == "__main__":
    asyncio.run(run_tests())
