import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models import ActionType, NextBestActionRecommendation
from app.database import DatabaseManager, db_manager
import app.crud as crud

logger = logging.getLogger("NextBestLearningActionService")

class NextBestLearningActionService:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    async def compute_next_best_action(
        self,
        clerk_user_id: str,
        goal_id: Optional[str] = None
    ) -> NextBestActionRecommendation:
        """
        Deterministically computes the single highest-leverage NEXT learning action
        for the learner. No hallucinated LLM decision; purely evidence-driven and reproducible.
        
        Scoring factors:
        - Goal gap severity (weight: 35)
        - Prerequisite blocker status (weight: 30)
        - Recent diagnoses (misconceptions/retention decay) (weight: 20)
        - BKT uncertainty & low mastery (weight: 15)
        - Exam/Industry relevance (weight: 10)
        """
        now = datetime.utcnow()

        # 1. Fetch user goal
        goal = None
        if goal_id:
            goal = await crud.get_goal(self.db, goal_id, clerk_user_id)
        if not goal:
            goals = await crud.get_goals(self.db, clerk_user_id)
            goal = goals[0] if goals else None

        # 2. Fetch all concepts, masteries, attempts, and diagnoses
        concepts = await crud.get_concepts(self.db, clerk_user_id)
        masteries = await crud.get_mastery(self.db, clerk_user_id)
        diagnoses = await crud.get_diagnoses(self.db, clerk_user_id)
        assignments = await crud.get_assignments(self.db, clerk_user_id) if hasattr(crud, "get_assignments") else []
        
        # Build lookup maps
        mastery_map: Dict[str, Dict[str, Any]] = {}
        for m in masteries:
            c_name = m.get("concept_name") or m.get("concept_id")
            if c_name:
                mastery_map[c_name] = m

        concept_map: Dict[str, Dict[str, Any]] = {
            (c.get("name") or c.get("id")): c for c in concepts
        }

        # Check for urgent pending incomplete assignments
        pending_assignments = [
            a for a in assignments 
            if not a.get("is_completed") and a.get("due_date")
        ]
        if pending_assignments:
            pending_assignments.sort(key=lambda a: a.get("due_date", ""))
            urgent_assignment = pending_assignments[0]
            cid = urgent_assignment.get("concept_id") or "assignment_core"
            return NextBestActionRecommendation(
                action_type=ActionType.COMPLETE_ASSIGNMENT,
                concept_id=cid,
                concept_name=urgent_assignment.get("title", "Pending Assignment"),
                priority=95.0,
                reason=f"You have an upcoming assignment '{urgent_assignment.get('title')}' due soon.",
                evidence={"assignment_id": str(urgent_assignment.get("_id")), "due_date": urgent_assignment.get("due_date")},
                expected_effect="Complete scheduled coursework and validate milestone mastery.",
                confidence=0.95,
                assignment_id=str(urgent_assignment.get("_id")),
                generated_at=now
            )

        # Check for active diagnoses requiring remediation
        if diagnoses:
            latest_diag = diagnoses[0]
            diag_type = latest_diag.get("diagnosis_type")
            target_c = latest_diag.get("target_concept")
            root_c = latest_diag.get("suspected_root_concept")

            if diag_type == "PREREQUISITE_WEAKNESS" and root_c:
                root_mastery = mastery_map.get(root_c, {}).get("mastery_score", 0.0)
                return NextBestActionRecommendation(
                    action_type=ActionType.REVIEW,
                    concept_id=root_c,
                    concept_name=root_c,
                    priority=90.0,
                    reason=f"Your {target_c} struggles are rooted in prerequisite {root_c} ({root_mastery:.1f}% mastery).",
                    evidence={"diagnosis_type": diag_type, "target_concept": target_c, "root_concept": root_c, "root_mastery": root_mastery},
                    expected_effect=f"Remediate foundational gap to unlock advancement in {target_c}.",
                    confidence=0.90,
                    generated_at=now
                )
            elif diag_type == "RECURRING_MISCONCEPTION" and target_c:
                return NextBestActionRecommendation(
                    action_type=ActionType.PRACTICE,
                    concept_id=target_c,
                    concept_name=target_c,
                    priority=88.0,
                    reason=f"Repeated distractor patterns detected on {target_c}. Counter-example practice will correct the misconception.",
                    evidence={"diagnosis_type": diag_type, "target_concept": target_c},
                    expected_effect="Refute systematic misconception through focused question drill.",
                    confidence=0.88,
                    generated_at=now
                )
            elif diag_type == "RETENTION_DECAY" and target_c:
                return NextBestActionRecommendation(
                    action_type=ActionType.REVIEW,
                    concept_id=target_c,
                    concept_name=target_c,
                    priority=85.0,
                    reason=f"Memory decay observed for {target_c} due to lack of recent review.",
                    evidence={"diagnosis_type": diag_type, "target_concept": target_c},
                    expected_effect="Restore long-term retention curve via spaced repetition active recall.",
                    confidence=0.85,
                    generated_at=now
                )

        # Evaluate candidate concepts for Goal Gap / Readiness
        target_skills = goal.get("required_skills", []) if goal else []
        candidates: List[Dict[str, Any]] = []

        for c_key, c_data in concept_map.items():
            c_name = c_data.get("name") or c_key
            c_id = str(c_data.get("_id") or c_data.get("id"))
            prereqs = c_data.get("prerequisites", [])
            
            # Prereq check
            prereqs_met = all(mastery_map.get(p, {}).get("mastery_score", 0.0) >= 70.0 for p in prereqs)
            m_rec = mastery_map.get(c_name, {})
            current_score = m_rec.get("mastery_score", 0.0)
            bkt_p = m_rec.get("bkt_probability", 0.1)

            # Match in goal
            goal_skill = next((s for s in target_skills if s.get("concept_name") == c_name), None)
            goal_weight = float(goal_skill.get("weight", 1.0)) if goal_skill else 0.5
            required_lvl = float(goal_skill.get("required_level", 80.0)) if goal_skill else 80.0
            gap = max(required_lvl - current_score, 0.0)

            # Relevance
            exam_rel = float(c_data.get("exam_relevance", 80)) / 100.0
            ind_rel = float(c_data.get("industry_relevance", 80)) / 100.0

            # Deterministic Score Formula
            if prereqs_met and gap > 0:
                score = (gap * 0.4) + (goal_weight * 25.0) + (exam_rel * 15.0) + (ind_rel * 15.0)
                if current_score == 0.0:
                    action_type = ActionType.LEARN
                    reason = f"{c_name} is a foundational goal skill with 0% mastery and all prerequisites met."
                    effect = f"Establish initial conceptual baseline for {c_name}."
                elif current_score < 50.0:
                    action_type = ActionType.PRACTICE
                    reason = f"Mastery for {c_name} is currently at {current_score:.1f}%. Interactive practice is required to reach proficiency."
                    effect = f"Elevate {c_name} towards target threshold ({required_lvl}%)."
                elif current_score < required_lvl:
                    action_type = ActionType.ASSESS
                    reason = f"{c_name} is approaching competency ({current_score:.1f}%). Take an adaptive assessment to certify mastery."
                    effect = f"Verify high-confidence mastery on {c_name}."
                else:
                    action_type = ActionType.ADVANCE
                    reason = f"{c_name} meets requirements. Ready to advance to subsequent syllabus milestones."
                    effect = "Unlock next tier concepts in the knowledge graph."

                candidates.append({
                    "concept_id": c_id,
                    "concept_name": c_name,
                    "priority": round(score, 2),
                    "action_type": action_type,
                    "reason": reason,
                    "expected_effect": effect,
                    "evidence": {
                        "current_mastery": current_score,
                        "goal_gap": gap,
                        "prerequisites_met": True,
                        "exam_relevance": exam_rel
                    },
                    "confidence": 0.85
                })

        if candidates:
            candidates.sort(key=lambda x: x["priority"], reverse=True)
            best = candidates[0]
            return NextBestActionRecommendation(
                action_type=best["action_type"],
                concept_id=best["concept_id"],
                concept_name=best["concept_name"],
                priority=min(best["priority"], 99.0),
                reason=best["reason"],
                evidence=best["evidence"],
                expected_effect=best["expected_effect"],
                confidence=best["confidence"],
                generated_at=now
            )

        # Fallback if all mastered or empty
        fallback_c = list(concept_map.keys())[0] if concept_map else "General Knowledge"
        fallback_id = str(concept_map[fallback_c].get("_id") or fallback_c) if concept_map else "general"
        return NextBestActionRecommendation(
            action_type=ActionType.ADVANCE,
            concept_id=fallback_id,
            concept_name=fallback_c,
            priority=50.0,
            reason="All current learning goals and prerequisites are satisfied. Ready to explore advanced topics.",
            evidence={"all_goals_met": True},
            expected_effect="Expand knowledge frontier into elective and advanced domains.",
            confidence=0.80,
            generated_at=now
        )
