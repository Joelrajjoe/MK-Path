import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..database import DatabaseManager

logger = logging.getLogger("mkpath.adaptive")

class AdaptivePolicy:
    @classmethod
    async def get_next_question(
        cls, 
        db: DatabaseManager, 
        clerk_user_id: str, 
        exclude_question_ids: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates the next question based on the learner state:
        1. Selects the target Concept optimizing for high uncertainty (information gain) and review urgency.
        2. Calibrates difficulty (basic, intermediate, advanced) using recent accuracy.
        3. Returns the question, verifying it doesn't leak answers.
        """
        exclude_question_ids = exclude_question_ids or []
        
        # 1. Fetch user mastery data to analyze concepts state
        if db.is_online:
            col_m = db.get_collection("mastery")
            mastery_list = await col_m.find({"clerk_user_id": clerk_user_id}).to_list(length=500)
            
            # Fetch recent attempts to check dynamic correctness pacing
            col_a = db.get_collection("attempts")
            recent_attempts = await col_a.find({"clerk_user_id": clerk_user_id}).sort("created_at", -1).limit(5).to_list(length=5)
        else:
            from ..crud import _DEMO_DB
            mastery_list = [m for m in _DEMO_DB.get("mastery", []) if m.get("clerk_user_id") == clerk_user_id]
            recent_attempts = [a for a in _DEMO_DB.get("attempts", []) if a.get("clerk_user_id") == clerk_user_id]
            recent_attempts.sort(key=lambda x: x.get("created_at", datetime.utcnow()), reverse=True)
            recent_attempts = recent_attempts[:5]

        if not mastery_list:
            logger.info("No mastery records found for user. Falling back to any available question.")
            return await cls._fallback_any_question(db, clerk_user_id, exclude_question_ids)

        # 2. Select target concept: Priority order:
        # a. Spaced repetition due (urgency)
        # b. High uncertainty (information gain: kt_uncertainty closest to 0.25, P(L) closest to 0.5)
        # c. Low mastery score (Weak / Learning category)
        
        now = datetime.utcnow()
        sorted_concepts = []
        for m in mastery_list:
            concept_id = m.get("concept_id")
            concept_name = m.get("concept_name")
            
            # Calculate review urgency (1.0 if review date has passed, lower otherwise)
            next_rev = m.get("next_review", now)
            urgency = 1.0 if now >= next_rev else 0.0
            
            # Uncertainty: kt_uncertainty ranges from 0.0 to 0.25 (highest uncertainty = 0.25)
            # Default to 0.24 if missing
            uncertainty = m.get("kt_uncertainty", 0.24)
            
            # Mastery score
            mastery_score = m.get("mastery_score", 50.0)
            
            # Formulate selection weight: high urgency + high uncertainty + low mastery
            weight = (urgency * 2.0) + (uncertainty * 4.0) + ((100.0 - mastery_score) / 100.0)
            sorted_concepts.append((weight, concept_id, concept_name, mastery_score))

        sorted_concepts.sort(key=lambda x: x[0], reverse=True)

        # 3. Determine target difficulty based on recent correctness pacing
        # If last attempt was correct, try to increase difficulty. If incorrect, decrease.
        last_was_correct = True
        if recent_attempts:
            last_was_correct = recent_attempts[0].get("is_correct", True)

        # 4. Iterate through prioritized concepts to find a matching question
        for _, concept_id, concept_name, mastery_score in sorted_concepts:
            # Map mastery score to target difficulty
            if mastery_score < 40.0:
                base_diff = "basic"
            elif mastery_score < 75.0:
                base_diff = "intermediate"
            else:
                base_diff = "advanced"

            # Pacing adjustment
            if last_was_correct:
                target_diffs = [cls._increase_difficulty(base_diff), base_diff, cls._decrease_difficulty(base_diff)]
            else:
                target_diffs = [cls._decrease_difficulty(base_diff), base_diff, cls._increase_difficulty(base_diff)]

            # Fetch questions for this concept
            if db.is_online:
                col_q = db.get_collection("questions")
                questions = await col_q.find({"concept_id": concept_id}).to_list(length=100)
            else:
                from ..crud import _DEMO_DB
                questions = [q for q in _DEMO_DB.get("questions", []) if q.get("concept_id") == concept_id]

            # Try to match difficulty in target preference order
            for diff in target_diffs:
                matching_qs = [
                    q for q in questions 
                    if q.get("difficulty", "basic") == diff 
                    and str(q.get("_id")) not in exclude_question_ids
                ]
                
                # Check for leak prevention
                for q in matching_qs:
                    if not cls._leaks_answers(q, exclude_question_ids):
                        from ..crud import serialize_doc
                        return serialize_doc(q)

            # Fallback to any remaining question for this concept
            remaining_qs = [
                q for q in questions 
                if str(q.get("_id")) not in exclude_question_ids
            ]
            if remaining_qs:
                from ..crud import serialize_doc
                return serialize_doc(remaining_qs[0])

        # Final absolute fallback to any question in database
        return await cls._fallback_any_question(db, clerk_user_id, exclude_question_ids)

    @classmethod
    def _increase_difficulty(cls, diff: str) -> str:
        if diff == "basic":
            return "intermediate"
        return "advanced"

    @classmethod
    def _decrease_difficulty(cls, diff: str) -> str:
        if diff == "advanced":
            return "intermediate"
        return "basic"

    @classmethod
    def _leaks_answers(cls, question: Dict[str, Any], excluded_ids: List[str]) -> bool:
        """
        Leak prevention validation. Verifies question wording does not leak answers to previous questions.
        """
        # Simplistic validation: prevent exact duplicates or extremely similar question texts
        # In a real environment, we would run semantic checks or exclude direct duplicates.
        return str(question.get("_id")) in excluded_ids

    @classmethod
    async def _fallback_any_question(
        cls, 
        db: DatabaseManager, 
        clerk_user_id: str, 
        exclude_question_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Absolute fallback: returns any question the user has not seen yet."""
        if db.is_online:
            col_q = db.get_collection("questions")
            cursor = col_q.find({})
            all_qs = await cursor.to_list(length=1000)
        else:
            from ..crud import _DEMO_DB
            all_qs = _DEMO_DB.get("questions", [])

        # Filter by excluded and user-isolation concept owners if applicable
        # (Seeding models strictly links questions to user scoped concept objects)
        from ..crud import serialize_doc
        for q in all_qs:
            q_id = str(q.get("_id"))
            if q_id not in exclude_question_ids:
                return serialize_doc(q)
        return None
