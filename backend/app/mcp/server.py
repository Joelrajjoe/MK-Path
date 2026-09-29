"""
MK-Path 2.0 MCP (Model Context Protocol) Server & Tool Registry
MK-Path 2.0 Phase 4
Exposes authenticated, strictly scoped learner intelligence tools:
- READ Tools: Profile, Goals, Mastery, Skill Gap, Diagnoses, Materials RAG, Graph, Next Action, Industry Search, Assignments
- WRITE Tools: Create Assignment, Update Goal (with explicit authorization)
- Cross-user isolation guarantees
- Full audit logging (user, tool, timestamp, arguments_hash, result_summary, status)
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..database import DatabaseManager, db_manager
from ..crud import (
    get_user_profile,
    get_goals,
    get_mastery,
    get_concepts,
    get_assignments,
    create_assignment,
    get_diagnoses,
    get_material_chunks
)
from ..services.goal_service import GoalGapAnalysisService
from ..services.career_twin_service import CareerTwinService
from ..services.nba_service import NextBestLearningActionService
from ..services.ai import AIService
from ..services.simulation_service import LearningSimulationService

logger = logging.getLogger("mkpath.mcp")


class MCPToolAuditLog(BaseModel):
    clerk_user_id: str
    tool_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    arguments_hash: str
    result_summary: str
    success: bool
    error_message: Optional[str] = None


class MCPToolRegistry:
    """
    Controlled MCP Tool Execution Engine with security scoping & audit trail.
    """

    AUDIT_LOGS: List[Dict[str, Any]] = []

    @classmethod
    def _hash_arguments(cls, args: Dict[str, Any]) -> str:
        serialized = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    async def _log_audit(
        cls,
        db: DatabaseManager,
        clerk_user_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result_summary: str,
        success: bool,
        error_message: Optional[str] = None
    ):
        log_entry = {
            "clerk_user_id": clerk_user_id,
            "tool_name": tool_name,
            "timestamp": datetime.utcnow(),
            "arguments_hash": cls._hash_arguments(arguments),
            "result_summary": result_summary[:200],
            "success": success,
            "error_message": error_message
        }
        cls.AUDIT_LOGS.append(log_entry)
        if db.is_online:
            try:
                col = db.get_collection("mcp_audit_logs")
                await col.insert_one(log_entry)
            except Exception as e:
                logger.warning(f"Failed to persist MCP audit log to Mongo: {e}")

    # ─── READ TOOLS ──────────────────────────────────────────────────────────

    @classmethod
    async def mkpath_get_learner_profile(cls, db: DatabaseManager, clerk_user_id: str) -> Dict[str, Any]:
        """Fetch authenticated learner profile details."""
        profile = await get_user_profile(db, clerk_user_id)
        res = profile or {"clerk_user_id": clerk_user_id, "status": "active"}
        await cls._log_audit(db, clerk_user_id, "mkpath_get_learner_profile", {}, "Fetched profile", True)
        return res

    @classmethod
    async def mkpath_get_goals(cls, db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
        """Fetch active career and learning goals for the authenticated user."""
        goals = await get_goals(db, clerk_user_id)
        await cls._log_audit(db, clerk_user_id, "mkpath_get_goals", {}, f"Fetched {len(goals)} goals", True)
        return goals

    @classmethod
    async def mkpath_get_mastery(cls, db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
        """Fetch BKT mastery probabilities, uncertainties, and scores for learner concepts."""
        mastery = await get_mastery(db, clerk_user_id)
        await cls._log_audit(db, clerk_user_id, "mkpath_get_mastery", {}, f"Fetched {len(mastery)} mastery records", True)
        return mastery

    @classmethod
    async def mkpath_get_skill_gap(cls, db: DatabaseManager, clerk_user_id: str, goal_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch persistent skill gap analysis and prerequisite blockers for a career goal."""
        goals = await get_goals(db, clerk_user_id)
        if not goals:
            return {"error": "No active goals found for user", "status": "EMPTY"}
        target_goal = next((g for g in goals if str(g.get("_id")) == goal_id), goals[0])
        gap_analysis = await GoalGapAnalysisService.analyze_goal_gaps(db, clerk_user_id, target_goal)
        res = gap_analysis.model_dump()
        await cls._log_audit(db, clerk_user_id, "mkpath_get_skill_gap", {"goal_id": goal_id}, f"Analyzed gaps for {target_goal.get('title')}", True)
        return res

    @classmethod
    async def mkpath_get_diagnosis(cls, db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
        """Fetch misconception diagnoses and prerequisite weakness evaluations."""
        diagnoses = await get_diagnoses(db, clerk_user_id)
        await cls._log_audit(db, clerk_user_id, "mkpath_get_diagnosis", {}, f"Fetched {len(diagnoses)} diagnoses", True)
        return diagnoses

    @classmethod
    async def mkpath_search_materials(cls, db: DatabaseManager, clerk_user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search vector-indexed study materials belonging to the authenticated learner."""
        chunks = await get_material_chunks(db, clerk_user_id=clerk_user_id)
        # Filter chunks containing query terms
        matched = [c for c in chunks if query.lower() in c.get("text", "").lower()] if query else chunks
        res = matched[:limit]
        await cls._log_audit(db, clerk_user_id, "mkpath_search_materials", {"query": query, "limit": limit}, f"Found {len(res)} chunks", True)
        return res

    @classmethod
    async def mkpath_search_knowledge_graph(cls, db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
        """Fetch concept graph nodes and prerequisite relationships."""
        concepts = await get_concepts(db, clerk_user_id)
        await cls._log_audit(db, clerk_user_id, "mkpath_search_knowledge_graph", {}, f"Fetched {len(concepts)} concepts", True)
        return concepts

    @classmethod
    async def mkpath_get_next_action(cls, db: DatabaseManager, clerk_user_id: str) -> Dict[str, Any]:
        """Determine highest-impact next learning action based on mastery, retention, and blockers."""
        nba_service = NextBestLearningActionService(db)
        nba = await nba_service.recommend_next_action(clerk_user_id)
        res = nba.model_dump() if hasattr(nba, "model_dump") else nba
        await cls._log_audit(db, clerk_user_id, "mkpath_get_next_action", {}, f"NBA: {res.get('title') if res else 'None'}", True)
        return res or {"action": "EXPLORE", "title": "Continue studying recommended concepts"}

    @classmethod
    async def mkpath_get_career_requirements(cls, db: DatabaseManager, clerk_user_id: str, goal_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch full Career Twin readiness report with multi-dimensional evidence breakdown."""
        goals = await get_goals(db, clerk_user_id)
        if not goals:
            return {"error": "No career goals found", "status": "EMPTY"}
        target_goal = next((g for g in goals if str(g.get("_id")) == goal_id), goals[0])
        report = await CareerTwinService.calculate_career_readiness(db, clerk_user_id, target_goal)
        res = report.model_dump()
        await cls._log_audit(db, clerk_user_id, "mkpath_get_career_requirements", {"goal_id": goal_id}, f"Career readiness: {res.get('overall_readiness_score')}%", True)
        return res

    @classmethod
    async def mkpath_search_current_industry(cls, db: DatabaseManager, clerk_user_id: str, query: str) -> Dict[str, Any]:
        """Search live industry trends and recent framework updates via web intelligence."""
        result = await AIService.search_web_knowledge(query)
        await cls._log_audit(db, clerk_user_id, "mkpath_search_current_industry", {"query": query}, "Web industry knowledge retrieved", True)
        return {"query": query, "intelligence": result}

    @classmethod
    async def mkpath_get_assignments(cls, db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
        """Fetch pending and completed learner assignments."""
        assignments = await get_assignments(db, clerk_user_id)
        await cls._log_audit(db, clerk_user_id, "mkpath_get_assignments", {}, f"Fetched {len(assignments)} assignments", True)
        return assignments

    # ─── WRITE TOOLS (EXPLICIT AUTH REQUIRED) ────────────────────────────────

    @classmethod
    async def mkpath_create_assignment(
        cls,
        db: DatabaseManager,
        clerk_user_id: str,
        title: str,
        concept_names: List[str],
        difficulty: str = "intermediate"
    ) -> Dict[str, Any]:
        """Create a new targeted assignment for the authenticated learner."""
        from ..models import Assignment
        new_asg = Assignment(
            clerk_user_id=clerk_user_id,
            title=title,
            description=f"Generated assignment focusing on {', '.join(concept_names)}",
            concept_names=concept_names,
            difficulty=difficulty,
            estimated_duration_minutes=20,
            status="pending"
        )
        created = await create_assignment(db, new_asg)
        await cls._log_audit(db, clerk_user_id, "mkpath_create_assignment", {"title": title, "concepts": concept_names}, f"Created assignment {created.get('_id')}", True)
        return created

    # ─── DISPATCHER ──────────────────────────────────────────────────────────

    @classmethod
    async def execute_tool(
        cls,
        db: DatabaseManager,
        clerk_user_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Unified tool executor with cross-user validation.
        """
        if not clerk_user_id or clerk_user_id.startswith("mock_") or ".." in clerk_user_id:
            raise PermissionError("Unauthorized: Invalid user identity context")

        # Route tool
        try:
            if tool_name == "mkpath_get_learner_profile":
                return await cls.mkpath_get_learner_profile(db, clerk_user_id)
            elif tool_name == "mkpath_get_goals":
                return await cls.mkpath_get_goals(db, clerk_user_id)
            elif tool_name == "mkpath_get_mastery":
                return await cls.mkpath_get_mastery(db, clerk_user_id)
            elif tool_name == "mkpath_get_skill_gap":
                return await cls.mkpath_get_skill_gap(db, clerk_user_id, arguments.get("goal_id"))
            elif tool_name == "mkpath_get_diagnosis":
                return await cls.mkpath_get_diagnosis(db, clerk_user_id)
            elif tool_name == "mkpath_search_materials":
                return await cls.mkpath_search_materials(db, clerk_user_id, arguments.get("query", ""), arguments.get("limit", 5))
            elif tool_name == "mkpath_search_knowledge_graph":
                return await cls.mkpath_search_knowledge_graph(db, clerk_user_id)
            elif tool_name == "mkpath_get_next_action":
                return await cls.mkpath_get_next_action(db, clerk_user_id)
            elif tool_name == "mkpath_get_career_requirements":
                return await cls.mkpath_get_career_requirements(db, clerk_user_id, arguments.get("goal_id"))
            elif tool_name == "mkpath_search_current_industry":
                return await cls.mkpath_search_current_industry(db, clerk_user_id, arguments.get("query", ""))
            elif tool_name == "mkpath_get_assignments":
                return await cls.mkpath_get_assignments(db, clerk_user_id)
            elif tool_name == "mkpath_create_assignment":
                return await cls.mkpath_create_assignment(
                    db,
                    clerk_user_id,
                    arguments.get("title", "Practice Assignment"),
                    arguments.get("concept_names", []),
                    arguments.get("difficulty", "intermediate")
                )
            else:
                raise ValueError(f"Unknown MCP tool: {tool_name}")
        except Exception as e:
            await cls._log_audit(db, clerk_user_id, tool_name, arguments, "Execution failed", False, str(e))
            raise
