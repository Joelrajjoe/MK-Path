import copy
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models import (
    SimulationRequest,
    SimulationResult,
    UnlockedConcept,
    SkillGap,
    Goal
)
from app.database import DatabaseManager, db_manager
import app.crud as crud
from app.services.goal_service import GoalGapAnalysisService

logger = logging.getLogger("LearningSimulationService")

class LearningSimulationService:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager
        self.gap_service = GoalGapAnalysisService()

    async def simulate_learning(
        self,
        user_id: str,
        request: SimulationRequest
    ) -> SimulationResult:
        """
        Pure in-memory counterfactual simulation of a learner's state.
        NEVER mutates database mastery, never creates learner events, never awards XP,
        and never alters production study paths.
        """
        # 1. Fetch real goal information
        goal = None
        if request.goal_id:
            goal = await crud.get_goal(self.db, request.goal_id, user_id)
        
        if not goal:
            # Fallback to active goal if none specified
            active_goals = await crud.get_goals(self.db, user_id)
            goal = active_goals[0] if active_goals else {
                "id": "simulated_goal",
                "title": "Simulated Master Goal",
                "required_skills": [
                    {"concept_name": c, "required_level": 80.0, "weight": 1.0}
                    for c in request.simulated_mastery_map.keys()
                ]
            }

        goal_title = goal.get("title", "Target Goal")
        required_skills = goal.get("required_skills", [])
        target_concept_names = [s.get("concept_name") for s in required_skills if s.get("concept_name")]
        
        if not target_concept_names and request.simulated_mastery_map:
            target_concept_names = list(request.simulated_mastery_map.keys())

        # 2. Fetch real current mastery records from DB
        real_masteries = await crud.get_mastery(self.db, user_id)
        current_mastery_map: Dict[str, float] = {}
        for m in real_masteries:
            c_name = m.get("concept_name") or m.get("concept_id")
            if c_name:
                current_mastery_map[c_name] = float(m.get("mastery_score", 0.0))

        # Calculate current readiness on target concepts
        if target_concept_names:
            current_scores = [current_mastery_map.get(c, 0.0) for c in target_concept_names]
            current_readiness = sum(current_scores) / max(len(target_concept_names), 1)
        else:
            current_readiness = 0.0

        # 3. Create simulated cloned mastery state in-memory
        simulated_mastery_map = copy.deepcopy(current_mastery_map)
        for concept, score in request.simulated_mastery_map.items():
            simulated_mastery_map[concept] = float(score)

        # Calculate simulated readiness
        if target_concept_names:
            simulated_scores = [simulated_mastery_map.get(c, 0.0) for c in target_concept_names]
            simulated_readiness = sum(simulated_scores) / max(len(target_concept_names), 1)
        else:
            simulated_readiness = 0.0

        readiness_delta = simulated_readiness - current_readiness

        # 4. Determine resolved vs remaining skill gaps
        all_concepts = await crud.get_concepts(self.db, user_id)
        concept_prereqs: Dict[str, List[str]] = {
            c.get("name") or c.get("id"): c.get("prerequisites", [])
            for c in all_concepts
        }

        resolved_skill_gaps: List[str] = []
        remaining_skill_gaps: List[SkillGap] = []

        for req in required_skills:
            c_name = req.get("name") or req.get("concept_name")
            if not c_name:
                continue
            target_val = float(req.get("required_level", 80.0))
            curr_val = current_mastery_map.get(c_name, 0.0)
            sim_val = simulated_mastery_map.get(c_name, 0.0)

            if sim_val >= target_val and curr_val < target_val:
                resolved_skill_gaps.append(c_name)
            elif sim_val < target_val:
                prereqs = concept_prereqs.get(c_name, [])
                prereqs_met = all(simulated_mastery_map.get(p, 0.0) >= 70.0 for p in prereqs)
                blocked_by = [p for p in prereqs if simulated_mastery_map.get(p, 0.0) < 70.0]
                
                remaining_skill_gaps.append(
                    SkillGap(
                        skill_name=c_name,
                        required_level=target_val,
                        current_mastery=sim_val,
                        gap=max(target_val - sim_val, 0.0),
                        prerequisite_readiness=100.0 if prereqs_met else 40.0,
                        evidence_strength="SIMULATED",
                        priority=target_val - sim_val,
                        status="BLOCKED_BY_PREREQUISITE" if not prereqs_met else "NEEDS_IMPROVEMENT",
                        source="simulated_counterfactual",
                        unmet_prerequisites=blocked_by,
                        explanation=f"Simulated skill gap of {target_val - sim_val:.1f}% on {c_name}."
                    )
                )

        # 5. Determine newly unlocked concepts & blocked concepts in graph
        newly_unlocked_concepts: List[UnlockedConcept] = []
        blocked_concepts: List[str] = []

        for c in all_concepts:
            c_name = c.get("name") or c.get("id")
            prereqs = c.get("prerequisites", [])
            if not prereqs:
                continue

            real_unlocked = all(current_mastery_map.get(p, 0.0) >= 70.0 for p in prereqs)
            sim_unlocked = all(simulated_mastery_map.get(p, 0.0) >= 70.0 for p in prereqs)

            if sim_unlocked and not real_unlocked:
                newly_unlocked_concepts.append(
                    UnlockedConcept(
                        concept_name=c_name,
                        reason=f"Prerequisites {', '.join(prereqs)} satisfied in simulation"
                    )
                )
            elif not sim_unlocked:
                blocked_concepts.append(c_name)

        # 6. Synthesize Changed Study Path (In-Memory Simulation)
        changed_study_path: List[Dict[str, Any]] = []
        for item in target_concept_names:
            sim_val = simulated_mastery_map.get(item, 0.0)
            if sim_val >= 80.0:
                changed_study_path.append({
                    "concept": item,
                    "simulated_status": "COMPLETED",
                    "simulated_mastery": sim_val
                })
            else:
                changed_study_path.append({
                    "concept": item,
                    "simulated_status": "IN_PROGRESS",
                    "simulated_mastery": sim_val
                })

        for u in newly_unlocked_concepts:
            changed_study_path.append({
                "concept": u.concept_name,
                "simulated_status": "AVAILABLE_NEXT",
                "reason": u.reason
            })

        # 7. Compute Next Best Action
        if remaining_skill_gaps:
            unblocked = [g for g in remaining_skill_gaps if g.status != "BLOCKED_BY_PREREQUISITE"]
            next_target = unblocked[0].skill_name if unblocked else remaining_skill_gaps[0].skill_name
            next_action_str = f"Focus on remediating '{next_target}' next as the highest unblocked leverage concept toward {goal_title}."
        else:
            next_action_str = f"All milestone competencies for {goal_title} are simulated as mastered. Proceed to comprehensive capstone assessment."

        return SimulationResult(
            is_simulation=True,
            goal_id=str(goal.get("_id") or goal.get("id")),
            goal_title=goal_title,
            current_goal_readiness=round(current_readiness, 2),
            simulated_goal_readiness=round(simulated_readiness, 2),
            readiness_delta=round(readiness_delta, 2),
            resolved_skill_gaps=resolved_skill_gaps,
            remaining_skill_gaps=remaining_skill_gaps,
            newly_unlocked_concepts=newly_unlocked_concepts,
            blocked_concepts=blocked_concepts[:10],
            changed_study_path=changed_study_path,
            next_best_action=next_action_str
        )
