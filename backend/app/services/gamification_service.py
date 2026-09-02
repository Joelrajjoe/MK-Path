import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..database import DatabaseManager
from ..models import Gamification, LearnerEvent
from .. import crud

logger = logging.getLogger("mkpath.gamification")

# Centralized configurable XP rewards (minimizes scatter)
XP_VALUES = {
    "mastery_improvement": 20,
    "successful_retrieval": 5,
    "consistent_review": 15,
    "difficult_concept_completion": 30,
    "prerequisite_completion": 25,
    "study_path_completion": 50,
    "resource_usefulness": 10,
    "sustained_learning_daily_streak": 15,
    "bonus_achievement_unlocked": 50
}

LEVEL_BOUNDARIES = [
    (100, "Beginner"),
    (250, "Learner"),
    (500, "Explorer"),
    (1000, "Skilled"),
    (999999, "Master")
]

class GamificationService:
    @classmethod
    async def award_xp(
        cls, 
        db: DatabaseManager, 
        clerk_user_id: str, 
        action_type: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Awards configurable XP for a user action, logging a reproducible event.
        """
        if action_type not in XP_VALUES:
            logger.warning(f"Unrecognized action_type for XP award: {action_type}")
            xp_to_award = 0
        else:
            xp_to_award = XP_VALUES[action_type]

        metadata = metadata or {}
        metadata["xp_awarded"] = xp_to_award

        # 1. Log Learner Event in history for reproducibility audits
        event = LearnerEvent(
            clerk_user_id=clerk_user_id,
            event_type=action_type,
            metadata=metadata
        )
        await crud.create_learner_event(db, event)

        # 2. Fetch or initialize profile
        profile_doc = await crud.get_gamification(db, clerk_user_id)
        if profile_doc:
            current_xp = profile_doc.get("xp", 0)
            achievements = list(profile_doc.get("achievements", []))
        else:
            current_xp = 0
            achievements = []

        new_xp = current_xp + xp_to_award
        
        # Calculate level
        level = 1
        level_name = "Beginner"
        for idx, (threshold, name) in enumerate(LEVEL_BOUNDARIES):
            if new_xp > threshold:
                level = idx + 2
                level_name = LEVEL_BOUNDARIES[idx+1][1] if idx + 1 < len(LEVEL_BOUNDARIES) else "Master"
            else:
                level_name = name
                level = idx + 1
                break

        game_model = Gamification(
            clerk_user_id=clerk_user_id,
            xp=new_xp,
            level=level,
            level_name=level_name,
            achievements=achievements,
            updated_at=datetime.utcnow()
        )
        
        updated_game = await crud.create_or_update_gamification(db, game_model)
        
        # 3. Dynamic achievements scan to check unlock triggers
        updated_game = await cls.check_and_unlock_achievements(db, clerk_user_id)
        
        return updated_game

    @classmethod
    async def check_and_unlock_achievements(cls, db: DatabaseManager, clerk_user_id: str) -> Dict[str, Any]:
        """
        Reviews learner event logs and updates user profile, unlocking corresponding achievements.
        """
        profile_doc = await crud.get_gamification(db, clerk_user_id)
        if not profile_doc:
            return {"xp": 0, "level": 1, "level_name": "Beginner", "achievements": []}

        current_xp = profile_doc.get("xp", 0)
        current_achievements = set(profile_doc.get("achievements", []))
        new_achievements = []

        # 1. Fetch user event history and mastery records
        events = await crud.get_learner_events(db, clerk_user_id)
        masteries = await crud.get_mastery(db, clerk_user_id)

        # Achievement 1: Concept Master (At least one concept is 'Mastered')
        has_mastery = any(m.get("category") == "Mastered" for m in masteries)
        if has_mastery and "Concept Master" not in current_achievements:
            new_achievements.append("Concept Master")

        # Achievement 2: Consistent Reviewer (At least 3 reviews logged)
        reviews_count = sum(1 for e in events if e.get("event_type") == "consistent_review")
        if reviews_count >= 3 and "Consistent Reviewer" not in current_achievements:
            new_achievements.append("Consistent Reviewer")

        # Achievement 3: High Confidence Accuracy (Correct answer and confidence >= 4)
        has_confident_correct = False
        for e in events:
            if e.get("event_type") == "successful_retrieval":
                meta = e.get("metadata", {})
                if meta.get("confidence", 0) >= 4:
                    has_confident_correct = True
                    break
        if has_confident_correct and "High Confidence Accuracy" not in current_achievements:
            new_achievements.append("High Confidence Accuracy")

        # Achievement 4: Difficult Concept Completed (Correct attempt on advanced difficulty)
        has_difficult_correct = False
        for e in events:
            if e.get("event_type") == "successful_retrieval":
                meta = e.get("metadata", {})
                if meta.get("difficulty") == "advanced":
                    has_difficult_correct = True
                    break
        if has_difficult_correct and "Difficult Concept Completed" not in current_achievements:
            new_achievements.append("Difficult Concept Completed")

        # Achievement 5: Prerequisite Chain Completed (Complete topics which have prerequisites)
        has_completed_prereqs = False
        for m in masteries:
            c_id = m.get("concept_id")
            # Fetch concept details
            if db.is_online:
                c_doc = await db.get_collection("concepts").find_one({"_id": c_id})
            else:
                c_doc = next((c for c in crud._demo_get_all("concepts") if str(c.get("_id")) == c_id), None)
            
            if c_doc and c_doc.get("prerequisites"):
                # Prerequisite concept completed
                has_completed_prereqs = True
                break
        if has_completed_prereqs and "Prerequisite Chain Completed" not in current_achievements:
            new_achievements.append("Prerequisite Chain Completed")

        if not new_achievements:
            return profile_doc

        # Award bonus XP for each newly unlocked achievement
        xp_bonus = len(new_achievements) * XP_VALUES["bonus_achievement_unlocked"]
        final_xp = current_xp + xp_bonus
        final_achievements = list(current_achievements.union(new_achievements))

        # Recalculate level
        level = 1
        level_name = "Beginner"
        for idx, (threshold, name) in enumerate(LEVEL_BOUNDARIES):
            if final_xp > threshold:
                level = idx + 2
                level_name = LEVEL_BOUNDARIES[idx+1][1] if idx + 1 < len(LEVEL_BOUNDARIES) else "Master"
            else:
                level_name = name
                level = idx + 1
                break

        # Log achievement unlock events
        for ach in new_achievements:
            event = LearnerEvent(
                clerk_user_id=clerk_user_id,
                event_type="achievement_unlocked",
                metadata={"achievement_name": ach, "xp_awarded": XP_VALUES["bonus_achievement_unlocked"]}
            )
            await crud.create_learner_event(db, event)

        game_model = Gamification(
            clerk_user_id=clerk_user_id,
            xp=final_xp,
            level=level,
            level_name=level_name,
            achievements=final_achievements,
            updated_at=datetime.utcnow()
        )
        
        return await crud.create_or_update_gamification(db, game_model)

    @classmethod
    async def audit_user_xp(cls, db: DatabaseManager, clerk_user_id: str) -> Dict[str, Any]:
        """
        Audits user gamification profile against event logs to reproduce the XP score.
        """
        # Fetch profile
        profile_doc = await crud.get_gamification(db, clerk_user_id)
        profile_xp = profile_doc.get("xp", 0) if profile_doc else 0

        # Query events log
        events = await crud.get_learner_events(db, clerk_user_id)
        
        reproduced_xp = 0
        for e in events:
            meta = e.get("metadata", {})
            xp_val = meta.get("xp_awarded")
            if xp_val is not None:
                reproduced_xp += xp_val

        return {
            "clerk_user_id": clerk_user_id,
            "actual_profile_xp": profile_xp,
            "reproduced_xp": reproduced_xp,
            "consistent": profile_xp == reproduced_xp,
            "events_audited": len(events)
        }
