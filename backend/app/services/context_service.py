from typing import Dict, Any, List
from app.database import DatabaseManager
from app.models import UserLearningContext
import app.crud as crud
from datetime import datetime, timedelta

class UserContextService:
    """
    Centralized service to aggregate a unified context object for RAG LLM Prompts.
    Retrieves profile, preferences, mastery, and activity to personalize learning.
    """
    @staticmethod
    async def get_full_context(db: DatabaseManager, clerk_user_id: str) -> UserLearningContext:
        # 1. Profile
        profile = await crud.get_user_profile(db, clerk_user_id) or {}
        
        # 2. Preferences (assuming it might be stored in a 'user_preferences' collection, fallback to profile if empty)
        # Note: If crud.get_user_preferences is not implemented, we gracefully fallback.
        preferences = {}
        if db.is_online:
            col = db.get_collection("user_preferences")
            pref_doc = await col.find_one({"clerk_user_id": clerk_user_id})
            if pref_doc:
                preferences = crud.serialize_doc(pref_doc)

        # 3. Learning Goals & Target Role (extracted from preferences if available)
        goals = {
            "learning_goal": preferences.get("learning_goal", "Not specified"),
            "target_role": preferences.get("target_role", "Not specified"),
            "exam_target": preferences.get("exam_target", "Not specified"),
            "industry_interests": preferences.get("industry_interests", [])
        }

        # 4. Mastery State
        mastery_records = []
        if db.is_online:
            col = db.get_collection("mastery")
            cursor = col.find({"clerk_user_id": clerk_user_id})
            mastery_records = crud.serialize_docs(await cursor.to_list(length=200))
        
        mastery_summary = {
            "average_score": sum(m.get("mastery_score", 0) for m in mastery_records) / len(mastery_records) if mastery_records else 0,
            "proficient_concepts": [m["concept_name"] for m in mastery_records if m.get("category") in ["Proficient", "Mastered"]],
        }
        weak_concepts = [m for m in mastery_records if m.get("category") == "Weak"]

        # 5. Recent Activity
        activity = []
        if db.is_online:
            act_col = db.get_collection("user_activity")
            cursor = act_col.find({"clerk_user_id": clerk_user_id}).sort("timestamp", -1).limit(10)
            activity = crud.serialize_docs(await cursor.to_list(length=10))

        # 6. Recent Materials
        materials = await crud.get_materials(db, clerk_user_id)
        
        # safely sort materials, since they might be missing created_at in legacy db states
        def get_dt(x):
            return x.get("created_at") or datetime.min
            
        recent_materials = sorted(materials, key=get_dt, reverse=True)[:5]

        return UserLearningContext(
            profile=profile,
            preferences=preferences,
            goals=goals,
            mastery=mastery_summary,
            weak_concepts=weak_concepts,
            activity=activity,
            recent_materials=recent_materials
        )
