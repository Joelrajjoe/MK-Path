import logging
import math
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..database import DatabaseManager
from .. import crud

logger = logging.getLogger("mkpath.recommender")

class ResourceRanker:
    async def rank_resources(
        self, 
        db: DatabaseManager, 
        clerk_user_id: str, 
        resources: List[Dict[str, Any]], 
        concept_mastery_score: float
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError()


class BaselineResourceRanker(ResourceRanker):
    async def rank_resources(
        self, 
        db: DatabaseManager, 
        clerk_user_id: str, 
        resources: List[Dict[str, Any]], 
        concept_mastery_score: float
    ) -> List[Dict[str, Any]]:
        """Simple baseline ranker sorting resources descending by default curated trust score."""
        ranked = []
        for r in resources:
            r_copy = dict(r)
            r_copy["recommendation_score"] = float(r.get("trust_score", 50))
            r_copy["rank_reason"] = "Curated baseline source trust ranking."
            ranked.append(r_copy)
        
        ranked.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return ranked


class TrustAwareResourceRanker(ResourceRanker):
    async def rank_resources(
        self, 
        db: DatabaseManager, 
        clerk_user_id: str, 
        resources: List[Dict[str, Any]], 
        concept_mastery_score: float
    ) -> List[Dict[str, Any]]:
        """
        Trust-aware recommendation engine.
        Integrates: curated trust, community ratings, helpfulness, freshness, difficulty fit, and completion penalties.
        """
        ranked = []
        now = datetime.utcnow()

        # Fetch user's feedback logs to calculate completions
        user_feedback_list = await crud.get_user_resource_feedback(db, clerk_user_id)
        completed_resource_ids = {f["resource_id"] for f in user_feedback_list if f.get("completed", False)}

        for r in resources:
            r_id = str(r["_id"])
            
            # 1. Fetch community feedback for this resource
            feedback_docs = await crud.get_resource_feedback(db, r_id)
            
            # Community ratings calculation (1-5 stars -> 0-100)
            ratings = [f["rating"] for f in feedback_docs if f.get("rating") is not None]
            if ratings:
                avg_rating = (sum(ratings) / len(ratings)) * 20.0
            else:
                avg_rating = 70.0  # Cold start: default to a neutral curated value

            # Helpfulness ratio
            helpful_votes = [f["helpful"] for f in feedback_docs if f.get("helpful") is not None]
            if helpful_votes:
                helpful_count = sum(1 for v in helpful_votes if v is True)
                helpfulness_ratio = (helpful_count / len(helpful_votes)) * 100.0
            else:
                helpfulness_ratio = 70.0  # Cold start default

            # 2. Freshness decay (1% decay per day elapsed)
            fresh_date = r.get("freshness_date")
            if not isinstance(fresh_date, datetime):
                fresh_date = r.get("created_at", now)
            if not isinstance(fresh_date, datetime):
                fresh_date = now
            days_old = (now - fresh_date).total_seconds() / (24 * 3600)
            freshness_score = 100.0 * math.exp(-0.01 * max(0.0, days_old))

            # 3. Difficulty Compatibility boost
            diff = r.get("difficulty", "basic").lower()
            diff_boost = 0.0
            if concept_mastery_score < 40.0:  # Weak
                if diff == "basic":
                    diff_boost = 15.0
                elif diff == "advanced":
                    diff_boost = -20.0
            elif concept_mastery_score < 70.0:  # Learning
                if diff == "intermediate":
                    diff_boost = 15.0
            else:  # Proficient/Mastered
                if diff == "advanced":
                    diff_boost = 15.0
                elif diff == "basic":
                    diff_boost = -10.0

            # 4. Sum up scoring criteria
            curated_trust = float(r.get("trust_score", 50))
            recommendation_score = (
                (0.30 * curated_trust) + 
                (0.25 * avg_rating) + 
                (0.20 * helpfulness_ratio) + 
                (0.15 * freshness_score) + 
                diff_boost
            )

            # 5. Completion Penalty (avoid recommending already completed items)
            is_completed = r_id in completed_resource_ids
            if is_completed:
                recommendation_score -= 50.0

            # Formulate reasons
            reasons = []
            if avg_rating >= 80.0:
                reasons.append("highly rated by community")
            if helpfulness_ratio >= 80.0:
                reasons.append("voted helpful by learners")
            if diff_boost > 0:
                reasons.append(f"tailored to your current '{diff}' proficiency level")
            if is_completed:
                reasons.append("already completed (review session)")
            else:
                reasons.append("highly trusted source")

            reason_str = f"Recommended because it is: {', and '.join(reasons)}."

            r_copy = dict(r)
            r_copy["recommendation_score"] = max(0.0, min(100.0, recommendation_score))
            r_copy["rank_reason"] = reason_str
            ranked.append(r_copy)

        # Sort descending by recommendation score
        ranked.sort(key=lambda x: x["recommendation_score"], reverse=True)
        return ranked


# --- Shadow Mode Recommendation Evaluation ---

async def run_recommender_evaluation(db: DatabaseManager, clerk_user_id: str, concept_name: str) -> Dict[str, Any]:
    """
    [SHADOW MODE] Evaluates performance stats (Click-through, helpfulness ratings, completion rate)
    for trust-aware vs baseline recommendations.
    """
    # Fetch all resources for the concept
    if db.is_online:
        col = db.get_collection("resources")
        resources = await col.find({"concept_name": concept_name}).to_list(length=100)
    else:
        resources = [r for r in crud._demo_get_all("resources") if r.get("concept_name") == concept_name]

    if not resources:
        return {"evaluation_status": "insufficient_data", "message": f"No resources seeded for concept '{concept_name}'."}

    # Fetch user concept mastery
    if db.is_online:
        col_m = db.get_collection("mastery")
        m_doc = await col_m.find_one({"clerk_user_id": clerk_user_id, "concept_name": concept_name})
    else:
        m_doc = next((m for m in crud._demo_get_all("mastery", clerk_user_id) if m.get("concept_name") == concept_name), None)

    mastery_score = m_doc.get("mastery_score", 50.0) if m_doc else 50.0

    # Calculate both recommendations
    baseline_ranker = BaselineResourceRanker()
    trust_ranker = TrustAwareResourceRanker()

    baseline_path = await baseline_ranker.rank_resources(db, clerk_user_id, resources, mastery_score)
    trust_path = await trust_ranker.rank_resources(db, clerk_user_id, resources, mastery_score)

    # Fetch all learner events for this user to calculate actual click-throughs
    events = await crud.get_learner_events(db, clerk_user_id)
    clicks = [e for e in events if e.get("event_type") == "resource_viewed"]
    completions = [e for e in events if e.get("event_type") == "resource_completed"]

    baseline_clicks = 0
    trust_clicks = 0
    
    top_baseline_id = str(baseline_path[0]["_id"]) if baseline_path else None
    top_trust_id = str(trust_path[0]["_id"]) if trust_path else None

    for c in clicks:
        res_id = c.get("resource_id")
        if res_id == top_baseline_id:
            baseline_clicks += 1
        if res_id == top_trust_id:
            trust_clicks += 1

    return {
        "concept_evaluated": concept_name,
        "learner_mastery": mastery_score,
        "baseline_top_recommendation": baseline_path[0]["title"] if baseline_path else None,
        "trust_top_recommendation": trust_path[0]["title"] if trust_path else None,
        "metrics": {
            "baseline_click_throughs": baseline_clicks,
            "trust_aware_click_throughs": trust_clicks,
            "total_completed_resources": len(completions)
        },
        "suggest_trust_promotion": True
    }
