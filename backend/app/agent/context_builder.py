"""
MK-Path 2.0 Context Builder
Aggregates authenticated multi-source learner state, RAG chunks, and external intelligence.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .models import LearnerContext, AgentIntent
from .router import IntentRouter
from .. import crud
from ..services.ai import AIService

logger = logging.getLogger("mkpath.agent.context_builder")

class ContextBuilder:
    """
    Constructs unified LearnerContext strictly scoped to authenticated clerk_user_id.
    """

    @classmethod
    async def build_context(
        cls,
        db: Any,
        clerk_user_id: str,
        query: str,
        intent: AgentIntent,
        focus_concept: Optional[str] = None,
        material_id: Optional[str] = None,
        include_web: bool = False
    ) -> LearnerContext:
        """
        Assembles all relevant context items based on intent routing.
        """
        required_sources = IntentRouter.get_required_context_sources(intent)
        
        ctx = LearnerContext(learner_id=clerk_user_id)

        # 1. User Profile & Preferences
        try:
            profile = await crud.get_user_profile(db, clerk_user_id)
            if profile:
                ctx.display_name = profile.get("display_name")
            prefs = await crud.get_user_preferences(db, clerk_user_id)
            if prefs:
                if prefs.get("target_role"):
                    ctx.target_roles.append(prefs.get("target_role"))
                if prefs.get("display_name") and not ctx.display_name:
                    ctx.display_name = prefs.get("display_name")
        except Exception as e:
            logger.warning(f"Error fetching profile context: {e}")

        # 2. Goals & Benchmarks
        if required_sources.get("load_goals"):
            try:
                goals = await crud.get_goals(db, clerk_user_id)
                ctx.goals = goals[:4]
                for g in goals:
                    if g.get("target_role") and g["target_role"] not in ctx.target_roles:
                        ctx.target_roles.append(g["target_role"])
                    if g.get("required_skills"):
                        ctx.career_requirements.extend(g["required_skills"])
            except Exception as e:
                logger.warning(f"Error fetching goals context: {e}")

        # 3. Concepts & Mastery
        if required_sources.get("load_mastery") or required_sources.get("load_knowledge_graph"):
            try:
                concepts = await crud.get_concepts(db, clerk_user_id)
                masteries = await crud.get_mastery(db, clerk_user_id)
                mastery_map = {m["concept_name"]: m["mastery_score"] for m in masteries}
                
                ctx.skills = [
                    {
                        "name": c["name"],
                        "difficulty": c.get("difficulty", "intermediate"),
                        "mastery": mastery_map.get(c["name"], 0.0),
                        "prerequisites": c.get("prerequisites", [])
                    }
                    for c in concepts[:20]
                ]
                ctx.mastery = masteries[:15]
            except Exception as e:
                logger.warning(f"Error fetching mastery context: {e}")

        # 4. Misconceptions & Diagnoses
        if required_sources.get("load_misconceptions"):
            try:
                diagnoses = await crud.get_learning_diagnoses(db, clerk_user_id)
                ctx.misconceptions = diagnoses[:5]
            except Exception as e:
                logger.warning(f"Error fetching diagnoses context: {e}")

        # 5. Study Path & Schedule
        if required_sources.get("load_study_path"):
            try:
                path = await crud.get_study_path(db, clerk_user_id)
                if path and path.get("ordered_concepts"):
                    ctx.study_path = path["ordered_concepts"][:6]
            except Exception as e:
                logger.warning(f"Error fetching study path context: {e}")

        # 6. Assignments Summary
        if required_sources.get("load_assignments"):
            try:
                assignments = await crud.get_assignments(db, clerk_user_id)
                ctx.assessment_history = [
                    {"title": a.get("title"), "status": a.get("status"), "score": a.get("score")}
                    for a in assignments[:5]
                ]
            except Exception as e:
                logger.warning(f"Error fetching assignments context: {e}")

        # 7. Semantic RAG Search across Learner Materials & YouTube
        if required_sources.get("load_materials_rag") or material_id or focus_concept:
            try:
                # Query RAG chunks
                chunks = await crud.get_material_chunks(db, material_id=material_id, clerk_user_id=clerk_user_id)
                if chunks:
                    query_words = set(query.lower().split() + ([focus_concept.lower()] if focus_concept else []))
                    ranked_chunks = []
                    for chunk in chunks:
                        txt = chunk.get("text", "").lower()
                        match_count = sum(1 for w in query_words if len(w) > 3 and w in txt)
                        ranked_chunks.append((match_count, chunk))
                    
                    ranked_chunks.sort(key=lambda x: x[0], reverse=True)
                    ctx.grounded_chunks = [c[1] for c in ranked_chunks[:6] if c[0] > 0 or len(ranked_chunks) <= 3]
            except Exception as e:
                logger.warning(f"Error executing RAG search: {e}")

        # 8. Web Knowledge / Current Industry Trends
        if include_web or required_sources.get("load_web_knowledge"):
            ctx.web_knowledge = cls._synthesize_industry_context(query, ctx.target_roles)

        return ctx

    @classmethod
    def _synthesize_industry_context(cls, query: str, target_roles: List[str]) -> List[Dict[str, Any]]:
        """
        Provides curated current industry and market intelligence grounding.
        """
        trends = [
            {
                "topic": "Agentic AI & LLM Orchestration",
                "standards": "LangGraph, CrewAI, AutoGen, Model Context Protocol (MCP), Tool Calling & Structured Output",
                "relevance": "High across AI, Data, and Backend engineering"
            },
            {
                "topic": "Modern Backend & Distributed Systems",
                "standards": "FastAPI (Async Python), Go Microservices, Kafka Event Streaming, Vector Databases (Chroma/Pinecone/pgvector), Hybrid Search",
                "relevance": "Backend and Systems roles"
            },
            {
                "topic": "Frontend & Fullstack Engineering",
                "standards": "React 19, Next.js App Router, Vite, Tailwind CSS v4, TypeScript 5+, Server Components",
                "relevance": "Frontend and Fullstack roles"
            }
        ]
        return trends
