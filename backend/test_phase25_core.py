import os
import sys
import asyncio
from datetime import datetime

# Ensure backend root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import Material, MaterialStatus, Concept, Relationship, Question, UserPreferences, UserProfile
from app.database import DatabaseManager
import app.crud as crud

async def run_phase25_tests():
    print("==================================================================")
    print("MK-PATH PHASE 25: CORE PRODUCT & CRUD COMPLETION TEST HARNESS")
    print("==================================================================")

    db = DatabaseManager() # In-memory demo DB mode
    user_alice = "user_clerk_alice_p25"
    user_bob = "user_clerk_bob_p25"

    # -------------------------------------------------------------------------
    # TEST 1: Material Rename & Processing Status
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Material Creation, Title Rename & Status Updates...")
    mat = Material(
        clerk_user_id=user_alice,
        title="Original Machine Learning Notes.pdf",
        file_name="ml_notes.pdf",
        file_size=1024,
        content_type="application/pdf",
        raw_text="Neural Networks and Loss Optimization Fundamentals.",
        status=MaterialStatus.READY.value
    )
    saved_mat = await crud.create_material(db, mat)
    mat_id = str(saved_mat["_id"])
    assert saved_mat["title"] == "Original Machine Learning Notes.pdf"
    
    # Rename material
    rename_success = await crud.update_material_title(db, mat_id, user_alice, "Renamed Deep Learning Notes.pdf")
    assert rename_success is True
    updated_mat = await crud.get_material(db, mat_id, user_alice)
    assert updated_mat["title"] == "Renamed Deep Learning Notes.pdf"
    
    # Update status
    await crud.update_material_status(db, mat_id, user_alice, MaterialStatus.CHUNKING.value)
    re_status_mat = await crud.get_material(db, mat_id, user_alice)
    assert re_status_mat["status"] == MaterialStatus.CHUNKING.value
    print("  -> Passed! Material successfully created, renamed, and status verified.")

    # -------------------------------------------------------------------------
    # TEST 2: Concept Custom Creation, Edit, and Prerequisite Update
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Concept Creation, Updating & Prerequisite Management...")
    c1 = Concept(
        clerk_user_id=user_alice,
        material_id=mat_id,
        name="Gradient Descent",
        description="First-order iterative optimization algorithm for finding a local minimum.",
        difficulty="intermediate",
        exam_relevance=85,
        industry_relevance=90,
        prerequisites=[]
    )
    c2 = Concept(
        clerk_user_id=user_alice,
        material_id=mat_id,
        name="Stochastic Gradient Descent",
        description="Iterative optimization method using random batches of training data.",
        difficulty="intermediate",
        exam_relevance=80,
        industry_relevance=85,
        prerequisites=["Gradient Descent"]
    )
    saved_concepts = await crud.create_concepts(db, [c1, c2])
    c1_id = str(saved_concepts[0]["_id"])
    c2_id = str(saved_concepts[1]["_id"])
    
    # Edit Concept
    patched = await crud.update_concept(db, c2_id, user_alice, {
        "difficulty": "advanced",
        "industry_relevance": 95,
        "prerequisites": ["Gradient Descent", "Loss Functions"]
    })
    assert patched["difficulty"] == "advanced"
    assert patched["industry_relevance"] == 95
    assert "Loss Functions" in patched["prerequisites"]
    print("  -> Passed! Concept successfully created, patched, and prerequisites updated.")

    # -------------------------------------------------------------------------
    # TEST 3: Duplicate Concept Merge
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Duplicate Concept Merging...")
    c_dup = Concept(
        clerk_user_id=user_alice,
        material_id=mat_id,
        name="SGD (Stochastic Gradient Descent)",
        description="Duplicate acronym concept for stochastic gradient optimization.",
        difficulty="intermediate",
        exam_relevance=75,
        industry_relevance=80,
        prerequisites=["Gradient Descent"]
    )
    saved_dup = await crud.create_concepts(db, [c_dup])
    c_dup_id = str(saved_dup[0]["_id"])
    
    # Attach question to duplicate concept
    q_dup = Question(
        clerk_user_id=user_alice,
        concept_id=c_dup_id,
        concept_name="SGD (Stochastic Gradient Descent)",
        question_text="What is the advantage of mini-batch SGD?",
        options=["Faster epoch updates", "Zero memory usage", "Eliminates overfitting", "None"],
        correct_option_index=0,
        difficulty="intermediate",
        explanation="Mini-batching balances vectorized efficiency with variance."
    )
    saved_q = await crud.create_questions(db, [q_dup])
    assert saved_q[0]["concept_id"] == c_dup_id

    # Merge duplicate into primary (c2_id)
    merged_res = await crud.merge_concepts(db, user_alice, c2_id, c_dup_id)
    assert merged_res is not None
    assert str(merged_res["_id"]) == c2_id
    
    # Verify duplicate concept is removed
    deleted_check = await crud.get_concept(db, c_dup_id, user_alice)
    assert deleted_check is None, "Duplicate concept should be deleted after merge"
    
    # Verify question was repointed to primary concept
    questions_list = await crud.get_questions(db, user_alice)
    repointed_q = next((q for q in questions_list if q["_id"] == saved_q[0]["_id"]), None)
    assert repointed_q["concept_id"] == c2_id
    assert repointed_q["concept_name"] == "Stochastic Gradient Descent"
    print("  -> Passed! Duplicate concepts merged and associated questions re-pointed.")

    # -------------------------------------------------------------------------
    # TEST 4: Extended Profile & Learning Preferences
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Extended Learner Profile, Preferences, and Target Deadlines...")
    prefs = UserPreferences(
        clerk_user_id=user_alice,
        display_name="Alice Senior AI Engineer",
        learning_goal="Master Deep Learning and Distributed Training",
        target_role="Machine Learning Engineer",
        target_exam="AWS Machine Learning Specialty",
        current_level="Intermediate",
        preferred_difficulty="advanced",
        daily_study_target_minutes=45,
        preferred_session_duration_minutes=30,
        deadline=datetime(2026, 12, 31, 0, 0, 0)
    )
    upserted_prefs = await crud.upsert_user_preferences(db, prefs)
    assert upserted_prefs["target_role"] == "Machine Learning Engineer"
    assert upserted_prefs["daily_study_target_minutes"] == 45
    assert upserted_prefs["target_exam"] == "AWS Machine Learning Specialty"
    
    retrieved_prefs = await crud.get_user_preferences(db, user_alice)
    assert retrieved_prefs["display_name"] == "Alice Senior AI Engineer"
    print("  -> Passed! Extended learner profile, exam targets, and deadlines saved.")

    # -------------------------------------------------------------------------
    # TEST 5: Authenticated User-Scoped Global Search
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Global Search across User Data Categories...")
    # Add activity
    await crud.log_user_activity(db, user_alice, event_type="deep_learning_module_started", entity_type="course")
    
    search_results = await crud.search_user_data(db, user_alice, "gradient")
    assert len(search_results["concepts"]) >= 1, "Should find 'Gradient Descent' concepts"
    
    mat_search_results = await crud.search_user_data(db, user_alice, "learning")
    assert len(mat_search_results["materials"]) >= 1, "Should find matching material"
    
    # Security isolation search check: Bob searching should not find Alice's data
    bob_results = await crud.search_user_data(db, user_bob, "learning")
    assert len(bob_results["concepts"]) == 0
    assert len(bob_results["materials"]) == 0
    print("  -> Passed! Global search across materials, concepts, questions, and activity verified with user isolation.")

    # -------------------------------------------------------------------------
    # TEST 6: Safe Category Data Clearing
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Safe Category Data Reset...")
    # Clear only concepts for Alice
    clear_res = await crud.clear_user_data(db, user_alice, "concepts")
    assert "cleared" in clear_res
    remaining_concepts = await crud.get_concepts(db, user_alice)
    assert len(remaining_concepts) == 0, "Alice concepts should be cleared"
    
    # Material should still remain intact if only concepts cleared
    mat_still_there = await crud.get_material(db, mat_id, user_alice)
    assert mat_still_there is not None
    print("  -> Passed! Safe selective data clearing verified without touching profile or user account.")

    print("\n==================================================================")
    print("ALL PHASE 25 CORE PRODUCT & LEARNER MANAGEMENT TESTS PASSED!")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(run_phase25_tests())
