import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from ..models import Mastery, Attempt, LearnerEvent
from ..database import DatabaseManager
from .neo4j_service import neo4j_service

logger = logging.getLogger("mkpath.kt")

class KTService:
    # Standard BKT default parameters
    P_L0 = 0.40  # Prior knowledge probability
    P_T = 0.20   # Learning transition rate (probability of learning a concept after an attempt)
    P_S = 0.10   # Slip rate (knowing but getting it wrong)
    P_G = 0.25   # Guess rate (not knowing but getting it right)

    @classmethod
    def calculate_bkt_step(cls, p_prev: float, is_correct: bool, confidence: int, response_time: float) -> Tuple[float, float]:
        """
        Executes one sequential BKT update step.
        Enriches classic BKT using confidence (reduces slip) and response speed (reduces guess).
        """
        # Dynamic slip reduction for high confidence responses
        p_slip = cls.P_S
        if confidence >= 4:
            p_slip = 0.05
        
        # Dynamic guess reduction for fast response times
        p_guess = cls.P_G
        if response_time < 6.0:
            p_guess = 0.12

        # 1. Update posterior probability of knowledge given correctness observation
        if is_correct:
            p_known_given_obs = (p_prev * (1.0 - p_slip)) / (p_prev * (1.0 - p_slip) + (1.0 - p_prev) * p_guess)
        else:
            p_known_given_obs = (p_prev * p_slip) / (p_prev * p_slip + (1.0 - p_prev) * (1.0 - p_guess))

        # 2. Account for transition (learning step)
        p_new = p_known_given_obs + (1.0 - p_known_given_obs) * cls.P_T
        
        # Clip to safe bounds
        p_new = max(0.01, min(0.99, p_new))
        
        # 3. Calculate uncertainty: variance P(L_t) * (1 - P(L_t))
        uncertainty = p_new * (1.0 - p_new)

        return p_new, uncertainty

    @classmethod
    async def update_mastery(
        cls, 
        db: DatabaseManager, 
        clerk_user_id: str, 
        concept_id: str, 
        concept_name: str, 
        is_correct: bool, 
        confidence: int, 
        response_time: float
    ) -> Dict[str, Any]:
        """
        Updates both baseline and BKT scores in shadow mode on MongoDB and returns the updated document.
        """
        # Retrieve existing mastery or initialize
        if db.is_online:
            col = db.get_collection("mastery")
            existing = await col.find_one({"clerk_user_id": clerk_user_id, "concept_id": concept_id})
        else:
            from ..crud import _DEMO_DB, _demo_get_by_id
            if "mastery" not in _DEMO_DB:
                _DEMO_DB["mastery"] = []
            # Find in demo DB
            existing = None
            for m in _DEMO_DB["mastery"]:
                if m.get("clerk_user_id") == clerk_user_id and m.get("concept_id") == concept_id:
                    existing = m
                    break

        # Defaults
        prev_score = 30.0
        prev_p = cls.P_L0
        active_model = "baseline"
        
        if existing:
            prev_score = existing.get("mastery_score", 30.0)
            prev_p = existing.get("kt_mastery_probability", cls.P_L0)
            active_model = existing.get("active_mastery_model", "baseline")

        # 1. Compute baseline score (weighted 4-term formula from Phase 7)
        acc_val = 100.0 if is_correct else 0.0
        conf_val = (confidence / 5.0) * 100.0
        speed_val = max(0.0, min(100.0, (1.0 - (response_time / 30.0)) * 100.0))
        
        baseline_score = (0.50 * acc_val) + (0.20 * conf_val) + (0.15 * speed_val) + (0.15 * prev_score)
        baseline_score = max(0.0, min(100.0, baseline_score))

        # 2. Compute BKT model step
        kt_p, kt_uncertainty = cls.calculate_bkt_step(prev_p, is_correct, confidence, response_time)
        bkt_score = kt_p * 100.0

        # Choose score based on active model config
        final_score = bkt_score if active_model == "knowledge_tracing" else baseline_score
        
        # Categorize
        if final_score < 40.0:
            category = "Weak"
        elif final_score < 70.0:
            category = "Learning"
        elif final_score < 85.0:
            category = "Proficient"
        else:
            category = "Mastered"

        # Calculate next review interval (spaced repetition interval based on score)
        # Score 0-39: review in 1 day; 40-69: 3 days; 70-84: 7 days; 85-100: 14 days
        now = datetime.utcnow()
        if category == "Weak":
            next_review_days = 1
        elif category == "Learning":
            next_review_days = 3
        elif category == "Proficient":
            next_review_days = 7
        else:
            next_review_days = 14
        
        next_review_time = now + timedelta(days=next_review_days)

        update_dict = {
            "clerk_user_id": clerk_user_id,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "mastery_score": final_score,
            "category": category,
            "last_reviewed_at": now,
            "next_review": next_review_time,
            "updated_at": now,
            
            # Shadow values stored concurrently
            "baseline_mastery": baseline_score,
            "knowledge_tracing_mastery": bkt_score,
            "kt_uncertainty": kt_uncertainty,
            "kt_mastery_probability": kt_p,
            "active_mastery_model": active_model
        }

        # Log Phase 13 event: concept_mastery_updated
        try:
            event = LearnerEvent(
                clerk_user_id=clerk_user_id,
                event_type="concept_mastery_updated",
                concept_id=concept_id,
                metadata={
                    "concept_name": concept_name,
                    "mastery_score": final_score,
                    "active_model": active_model,
                    "bkt_p": kt_p
                }
            )
            if db.is_online:
                await db.get_collection("learner_events").insert_one(event.model_dump())
            else:
                from ..crud import _DEMO_DB
                _DEMO_DB["learner_events"].append(event.model_dump())
        except Exception as e:
            logger.error(f"Failed to log concept_mastery_updated event: {e}")

        # Persist to database
        if db.is_online:
            col = db.get_collection("mastery")
            await col.update_one(
                {"clerk_user_id": clerk_user_id, "concept_id": concept_id},
                {"$set": update_dict},
                upsert=True
            )
            res = await col.find_one({"clerk_user_id": clerk_user_id, "concept_id": concept_id})
            from ..crud import serialize_doc
            return serialize_doc(res)
        else:
            from ..crud import serialize_doc, _demo_get_by_id
            if existing:
                existing.update(update_dict)
                return serialize_doc(existing)
            else:
                from bson import ObjectId
                update_dict["_id"] = ObjectId()
                from ..crud import _DEMO_DB
                _DEMO_DB["mastery"].append(update_dict)
                return serialize_doc(update_dict)

    @classmethod
    async def evaluate_models(cls, db: DatabaseManager, clerk_user_id: str) -> Dict[str, Any]:
        """
        Retrospectively evaluates prediction accuracy, calibration, and Brier score
        for both baseline and BKT models against future attempt outcomes.
        """
        # Fetch all user quiz attempts
        if db.is_online:
            col = db.get_collection("attempts")
            attempts = await col.find({"clerk_user_id": clerk_user_id}).sort("created_at", 1).to_list(length=1000)
        else:
            from ..crud import _DEMO_DB
            attempts = [a for a in _DEMO_DB.get("attempts", []) if a.get("clerk_user_id") == clerk_user_id]
            attempts.sort(key=lambda x: x.get("created_at", datetime.utcnow()))

        if len(attempts) < 2:
            return {
                "evaluation_status": "insufficient_data",
                "message": "At least 2 historical attempts are required for retrospective prediction analysis.",
                "baseline_brier_score": 0.0,
                "bkt_brier_score": 0.0,
                "better_model": "baseline"
            }

        # Track concept states over time
        # Baseline model tracks score (0-100) -> mapped to correctness probability = score / 100
        # BKT tracks probability P(L_t-1) -> predicted correct = P(L_t-1) * (1 - S) + (1 - P(L_t-1)) * G
        concept_baseline_state = {}
        concept_bkt_state = {}
        
        baseline_squared_errors = []
        bkt_squared_errors = []
        
        baseline_correct_predictions = 0
        bkt_correct_predictions = 0
        
        for att in attempts:
            concept_id = att.get("concept_id")
            is_correct = att.get("is_correct", False)
            actual_binary = 1.0 if is_correct else 0.0
            
            # 1. Predictions for current attempt based on previous concept states
            prev_baseline_score = concept_baseline_state.get(concept_id, 30.0)
            p_baseline = max(0.01, min(0.99, prev_baseline_score / 100.0))
            
            prev_bkt_p = concept_bkt_state.get(concept_id, cls.P_L0)
            # Probability of answering correct in BKT:
            p_bkt = (prev_bkt_p * (1.0 - cls.P_S)) + ((1.0 - prev_bkt_p) * cls.P_G)
            p_bkt = max(0.01, min(0.99, p_bkt))

            # 2. Compute Squared Errors (Brier Scores components)
            baseline_se = (p_baseline - actual_binary) ** 2
            bkt_se = (p_bkt - actual_binary) ** 2
            
            baseline_squared_errors.append(baseline_se)
            bkt_squared_errors.append(bkt_se)

            # 3. Binary Accuracy (Prediction matches correctness if threshold is 0.5)
            pred_baseline_bin = p_baseline >= 0.50
            pred_bkt_bin = p_bkt >= 0.50
            
            if pred_baseline_bin == is_correct:
                baseline_correct_predictions += 1
            if pred_bkt_bin == is_correct:
                bkt_correct_predictions += 1

            # 4. Advance states (BKT step & Baseline updates)
            confidence = att.get("confidence", 3)
            response_time = att.get("response_time_seconds", 10.0)
            
            # Baseline rolling update step
            acc_val = 100.0 if is_correct else 0.0
            conf_val = (confidence / 5.0) * 100.0
            speed_val = max(0.0, min(100.0, (1.0 - (response_time / 30.0)) * 100.0))
            new_baseline_score = (0.50 * acc_val) + (0.20 * conf_val) + (0.15 * speed_val) + (0.15 * prev_baseline_score)
            concept_baseline_state[concept_id] = new_baseline_score
            
            # BKT step update
            new_bkt_p, _ = cls.calculate_bkt_step(prev_bkt_p, is_correct, confidence, response_time)
            concept_bkt_state[concept_id] = new_bkt_p

        # Averages
        n = len(attempts)
        baseline_brier = sum(baseline_squared_errors) / n
        bkt_brier = sum(bkt_squared_errors) / n
        
        baseline_accuracy = (baseline_correct_predictions / n) * 100.0
        bkt_accuracy = (bkt_correct_predictions / n) * 100.0
        
        # BKT is promoted if Brier score is lower (better prediction calibration)
        better_model = "knowledge_tracing" if bkt_brier < baseline_brier else "baseline"
        
        return {
            "evaluation_status": "evaluated",
            "attempts_analyzed": n,
            "baseline_brier_score": round(baseline_brier, 4),
            "bkt_brier_score": round(bkt_brier, 4),
            "baseline_accuracy": round(baseline_accuracy, 2),
            "bkt_accuracy": round(bkt_accuracy, 2),
            "better_model": better_model,
            "suggest_promotion": better_model == "knowledge_tracing"
        }

    @classmethod
    async def promote_model(cls, db: DatabaseManager, clerk_user_id: str, promote_to: str) -> Dict[str, Any]:
        """
        Promotes selected model to production by updating active_mastery_model values.
        """
        if promote_to not in ("baseline", "knowledge_tracing"):
            raise ValueError("Target model must be either 'baseline' or 'knowledge_tracing'")

        if db.is_online:
            col = db.get_collection("mastery")
            # Update all documents for this user
            await col.update_many(
                {"clerk_user_id": clerk_user_id},
                {"$set": {"active_mastery_model": promote_to}}
            )
            # Re-read and update scores according to promoted model
            cursor = col.find({"clerk_user_id": clerk_user_id})
            records = await cursor.to_list(length=1000)
            for r in records:
                score = r.get("knowledge_tracing_mastery" if promote_to == "knowledge_tracing" else "baseline_mastery", 30.0)
                # Re-categorize
                category = "Weak" if score < 40 else "Learning" if score < 70 else "Proficient" if score < 85 else "Mastered"
                await col.update_one(
                    {"_id": r["_id"]},
                    {"$set": {"mastery_score": score, "category": category}}
                )
        else:
            from ..crud import _DEMO_DB
            for m in _DEMO_DB.get("mastery", []):
                if m.get("clerk_user_id") == clerk_user_id:
                    m["active_mastery_model"] = promote_to
                    score = m.get("knowledge_tracing_mastery" if promote_to == "knowledge_tracing" else "baseline_mastery", 30.0)
                    m["mastery_score"] = score
                    m["category"] = "Weak" if score < 40 else "Learning" if score < 70 else "Proficient" if score < 85 else "Mastered"

        return {
            "status": "success",
            "active_mastery_model": promote_to,
            "message": f"Successfully promoted {promote_to} to active production tracing."
        }
