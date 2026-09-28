import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..models import Goal, RequiredSkill, SkillGap, GoalGapAnalysis
from ..database import DatabaseManager
from .neo4j_service import neo4j_service

logger = logging.getLogger("mkpath.goal_gap")

class GoalGapAnalysisService:
    """
    Goal-to-Skill Gap Intelligence Service.
    
    Persistent goal-to-skill state model:
    Goal -> Required Skills -> Learner State -> Skill Gaps -> Prerequisite Gaps -> Goal Readiness.
    
    Inputs:
    - Active learner goal & required skills
    - Learner mastery records (mastery score, BKT probability, uncertainty, last reviewed)
    - Graph prerequisites (via Neo4j / MongoDB relationships)
    - Assessment evidence (attempts count, confidence, correctness)
    - Concept metadata (exam relevance, industry relevance)
    
    Status outputs per skill:
    - MASTERED (current_mastery >= required_level)
    - READY (gap == 0 or prerequisites satisfied & assessed)
    - NEEDS_IMPROVEMENT (gap > 0 and all prerequisites met)
    - BLOCKED_BY_PREREQUISITE (one or more prerequisites have mastery < 70)
    - INSUFFICIENT_EVIDENCE (no assessment attempts or unassessed)
    """

    PREREQUISITE_THRESHOLD = 70.0  # Prerequisite mastery must be >= 70% to unblock dependent skill

    @classmethod
    async def analyze_goal_gaps(
        cls,
        db: DatabaseManager,
        clerk_user_id: str,
        goal: Dict[str, Any]
    ) -> GoalGapAnalysis:
        goal_id = str(goal.get("_id", ""))
        goal_title = goal.get("title", "Learner Goal")
        required_skills_raw = goal.get("required_skills", [])

        # Fetch learner mastery docs for user
        mastery_map: Dict[str, Dict[str, Any]] = {}
        if db.is_online:
            col_m = db.get_collection("mastery")
            cursor = col_m.find({"clerk_user_id": clerk_user_id})
            async for doc in cursor:
                mastery_map[doc.get("concept_name", "")] = doc
        else:
            from ..crud import _DEMO_DB
            for doc in _DEMO_DB.get("mastery", []):
                if doc.get("clerk_user_id") == clerk_user_id:
                    mastery_map[doc.get("concept_name", "")] = doc

        # Fetch concept metadata for user
        concept_meta_map: Dict[str, Dict[str, Any]] = {}
        if db.is_online:
            col_c = db.get_collection("concepts")
            cursor = col_c.find({"clerk_user_id": clerk_user_id})
            async for doc in cursor:
                concept_meta_map[doc.get("name", "")] = doc
        else:
            from ..crud import _DEMO_DB
            for doc in _DEMO_DB.get("concepts", []):
                if doc.get("clerk_user_id") == clerk_user_id:
                    concept_meta_map[doc.get("name", "")] = doc

        # Fetch learner attempts count per concept (match by name or concept_id)
        attempts_count_map: Dict[str, int] = {}
        if db.is_online:
            col_a = db.get_collection("attempts")
            cursor = col_a.find({"clerk_user_id": clerk_user_id})
            async for doc in cursor:
                cname = doc.get("concept_name", "")
                cid = str(doc.get("concept_id", ""))
                if cname:
                    attempts_count_map[cname] = attempts_count_map.get(cname, 0) + 1
                if cid:
                    attempts_count_map[cid] = attempts_count_map.get(cid, 0) + 1
        else:
            from ..crud import _DEMO_DB
            for doc in _DEMO_DB.get("attempts", []):
                if doc.get("clerk_user_id") == clerk_user_id:
                    cname = doc.get("concept_name", "")
                    cid = str(doc.get("concept_id", ""))
                    if cname:
                        attempts_count_map[cname] = attempts_count_map.get(cname, 0) + 1
                    if cid:
                        attempts_count_map[cid] = attempts_count_map.get(cid, 0) + 1

        skill_gaps: List[SkillGap] = []
        total_weighted_readiness = 0.0
        total_weights = 0.0

        for req in required_skills_raw:
            skill_name = req.get("name", "") if isinstance(req, dict) else req.name
            required_level = float(req.get("required_level", 75.0) if isinstance(req, dict) else req.required_level)
            source = str(req.get("source", "verified_system_mapping") if isinstance(req, dict) else req.source)
            weight = float(req.get("weight", 1.0) if isinstance(req, dict) else req.weight)

            # 1. Determine current mastery
            mastery_doc = mastery_map.get(skill_name)
            current_mastery = 0.0
            kt_p = None
            kt_uncertainty = None
            if mastery_doc:
                current_mastery = float(mastery_doc.get("mastery_score", 0.0))
                kt_p = mastery_doc.get("kt_mastery_probability")
                kt_uncertainty = mastery_doc.get("kt_uncertainty")

            # 2. Determine evidence strength based on attempt history and BKT uncertainty
            attempt_count = attempts_count_map.get(skill_name, 0)
            if attempt_count == 0 and not mastery_doc:
                evidence_strength = "none"
            elif attempt_count < 2:
                evidence_strength = "low"
            elif attempt_count < 5 or (kt_uncertainty and kt_uncertainty > 0.18):
                evidence_strength = "moderate"
            else:
                evidence_strength = "high"

            # 3. Calculate Gap
            gap = max(0.0, round(required_level - current_mastery, 2))

            # 4. Determine Prerequisites & Prerequisite Readiness
            prereq_names = await neo4j_service.get_prerequisites(clerk_user_id, skill_name)
            # If no graph prereqs found in neo4j service, also check MongoDB relationships
            if not prereq_names:
                if db.is_online:
                    col_rel = db.get_collection("relationships")
                    cursor = col_rel.find({
                        "clerk_user_id": clerk_user_id,
                        "target_concept_name": skill_name,
                        "relationship_type": {"$in": ["PREREQUISITE_OF", "PREREQUISITE", "prerequisite_of", "prerequisite"]}
                    })
                    async for r in cursor:
                        prereq_names.append(r.get("source_concept_name"))
                else:
                    from ..crud import _DEMO_DB
                    for r in _DEMO_DB.get("relationships", []):
                        if r.get("clerk_user_id") == clerk_user_id and r.get("target_concept_name") == skill_name:
                            rtype = str(r.get("relationship_type", "")).upper()
                            if "PREREQUISITE" in rtype:
                                prereq_names.append(r.get("source_concept_name"))

            unmet_prerequisites = []
            prereq_readiness_total = 0.0

            if prereq_names:
                for p_name in prereq_names:
                    p_doc = mastery_map.get(p_name)
                    p_score = float(p_doc.get("mastery_score", 0.0)) if p_doc else 0.0
                    prereq_readiness_total += p_score
                    if p_score < cls.PREREQUISITE_THRESHOLD:
                        unmet_prerequisites.append(f"{p_name} (Current: {round(p_score, 1)}% / Required: {cls.PREREQUISITE_THRESHOLD}%)")
                prerequisite_readiness = round(prereq_readiness_total / len(prereq_names), 2)
            else:
                prerequisite_readiness = 100.0  # No prerequisites required

            # 5. Determine Skill Status
            # Statuses: MASTERED, READY, NEEDS_IMPROVEMENT, BLOCKED_BY_PREREQUISITE, INSUFFICIENT_EVIDENCE
            if current_mastery >= required_level:
                status = "MASTERED"
                explanation = f"Learner has attained {round(current_mastery, 1)}% mastery, meeting target requirement of {round(required_level, 1)}%."
            elif unmet_prerequisites:
                status = "BLOCKED_BY_PREREQUISITE"
                explanation = f"Blocked by {len(unmet_prerequisites)} prerequisite skill(s) below {cls.PREREQUISITE_THRESHOLD}% threshold: {', '.join(unmet_prerequisites)}."
            elif evidence_strength == "none":
                status = "INSUFFICIENT_EVIDENCE"
                explanation = f"Target requires {round(required_level, 1)}% mastery, but learner has no assessment history or evidence for this skill."
            elif gap > 0:
                status = "NEEDS_IMPROVEMENT"
                explanation = f"All prerequisites are satisfied, but mastery ({round(current_mastery, 1)}%) is below the {round(required_level, 1)}% target level (Gap: {gap}%)."
            else:
                status = "READY"
                explanation = f"Prerequisites are met and current proficiency matches required baseline."

            # 6. Calculate Priority
            # Priority formula enriches gap by skill weight, exam relevance, and industry relevance
            c_meta = concept_meta_map.get(skill_name, {})
            exam_rel = float(c_meta.get("exam_relevance", 50.0))
            industry_rel = float(c_meta.get("industry_relevance", 50.0))
            
            # Blocking prerequisites or high gaps get elevated priority
            status_multiplier = 1.0
            if status == "NEEDS_IMPROVEMENT":
                status_multiplier = 1.3
            elif status == "BLOCKED_BY_PREREQUISITE":
                status_multiplier = 1.1
            elif status == "INSUFFICIENT_EVIDENCE":
                status_multiplier = 1.2
            elif status == "MASTERED":
                status_multiplier = 0.2

            priority = round(
                (gap * 0.5 + (100.0 - current_mastery) * 0.3 + (exam_rel + industry_rel) * 0.1) * weight * status_multiplier,
                2
            )

            skill_gaps.append(SkillGap(
                skill_name=skill_name,
                required_level=required_level,
                current_mastery=round(current_mastery, 2),
                gap=gap,
                prerequisite_readiness=prerequisite_readiness,
                evidence_strength=evidence_strength,
                priority=priority,
                status=status,
                source=source,
                unmet_prerequisites=unmet_prerequisites,
                explanation=explanation
            ))

            # Weight towards overall readiness
            skill_completion_ratio = min(1.0, current_mastery / required_level) if required_level > 0 else 1.0
            total_weighted_readiness += (skill_completion_ratio * 100.0) * weight
            total_weights += weight

        # Sort skill gaps by priority descending
        skill_gaps.sort(key=lambda x: x.priority, reverse=True)

        # Compute overall goal readiness score
        overall_readiness_score = round(total_weighted_readiness / total_weights, 2) if total_weights > 0 else 0.0

        if overall_readiness_score >= 90.0:
            goal_status = "READY"
        elif overall_readiness_score >= 50.0:
            goal_status = "IN_PROGRESS"
        elif overall_readiness_score > 0.0:
            goal_status = "AT_RISK"
        else:
            goal_status = "NOT_STARTED"

        # Determine recommended focus skill (highest priority among actionable NEEDS_IMPROVEMENT or INSUFFICIENT_EVIDENCE)
        focus_candidates = [s for s in skill_gaps if s.status in ("NEEDS_IMPROVEMENT", "INSUFFICIENT_EVIDENCE")]
        if not focus_candidates:
            focus_candidates = [s for s in skill_gaps if s.status == "BLOCKED_BY_PREREQUISITE"]
        
        recommended_focus_skill = focus_candidates[0].skill_name if focus_candidates else (skill_gaps[0].skill_name if skill_gaps else None)

        return GoalGapAnalysis(
            goal_id=goal_id,
            goal_title=goal_title,
            overall_readiness_score=overall_readiness_score,
            status=goal_status,
            skills=skill_gaps,
            recommended_focus_skill=recommended_focus_skill,
            analyzed_at=datetime.utcnow()
        )
