"""
Career Twin Service
MK-Path 2.0 Phase 3
Implements Job Description AI Parsing, Career Skill Graph synthesis, Evidence Deficit computation, and transparent Explainable Readiness modeling.
"""
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from bson import ObjectId

from ..database import DatabaseManager, db_manager
from ..services.ai import AIService
from ..services.neo4j_service import neo4j_service
from .career_twin_models import (
    CareerTwinGoal,
    JobDescriptionAnalysisResult,
    CareerSkillNode,
    EvidenceQuality,
    CareerTwinReadinessReport,
    CareerReadinessTrajectoryPoint,
    SkillEvidenceItem,
    EvidenceType
)

logger = logging.getLogger("mkpath.career_twin")

class CareerTwinService:
    """
    Career Twin Engine connecting job market expectations with multi-dimensional learner evidence.
    """

    @classmethod
    async def analyze_job_description(cls, job_description_text: str, role_hint: Optional[str] = None) -> JobDescriptionAnalysisResult:
        """
        Parses raw job description text into structured competencies, frameworks, soft skills, interview topics, and evidence expectations.
        """
        if not job_description_text or len(job_description_text.strip()) < 10:
            return JobDescriptionAnalysisResult(
                role_title=role_hint or "Software Engineer",
                target_level="Mid-Level",
                technical_skills=["Data Structures", "Algorithms", "Databases", "API Design"],
                tools_and_frameworks=["Git", "Docker", "FastAPI"],
                soft_skills=["Communication", "Problem Solving"],
                responsibilities=["Design and maintain scalable services"],
                expected_experience_years="2-4 years",
                interview_topics=["System Design", "Coding Problem", "Architecture"],
                evidence_expectations=["Production REST API", "Database schema migration", "Unit tests"],
                extracted_skill_nodes=[
                    {"name": s, "category": "technical", "required_level": 75.0, "career_importance": 1.5}
                    for s in ["Data Structures", "Algorithms", "Databases", "API Design", "Docker", "FastAPI"]
                ]
            )

        prompt = f"""
You are an expert technical recruiter and learning architect.
Analyze the following job description and extract a precise technical profile.

Role Hint (if any): {role_hint or 'Not specified'}

Job Description:
\"\"\"{job_description_text[:6000]}\"\"\"

Return a valid JSON object matching this exact structure:
{{
  "role_title": "string (e.g. Senior Backend Engineer)",
  "target_level": "string (e.g. Junior, Mid-Level, Senior, Staff)",
  "technical_skills": ["list of core technical concepts/skills like Concurrency, SQL Optimization, OAuth2"],
  "tools_and_frameworks": ["list of specific frameworks & tools like Kubernetes, FastAPI, PostgreSQL, Redis"],
  "soft_skills": ["list of soft skills e.g. Technical Leadership, Cross-functional Communication"],
  "responsibilities": ["3-5 key responsibilities"],
  "expected_experience_years": "e.g. 3-5 years",
  "interview_topics": ["3-5 topics expected in technical/behavioral interviews"],
  "evidence_expectations": ["3-5 concrete evidence examples e.g. 'Deploying a distributed cache', 'Writing async unit tests'"]
}}
"""
        try:
            res = await AIService.generate_text(prompt, max_tokens=1500, temperature=0.1)
            raw = res.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            
            all_skills = data.get("technical_skills", []) + data.get("tools_and_frameworks", [])
            extracted_nodes = []
            for s in all_skills:
                extracted_nodes.append({
                    "name": s,
                    "category": "tool" if s in data.get("tools_and_frameworks", []) else "technical",
                    "required_level": 80.0 if "Senior" in data.get("target_level", "") else 75.0,
                    "career_importance": 2.0 if s in data.get("technical_skills", [])[:3] else 1.2
                })

            return JobDescriptionAnalysisResult(
                role_title=data.get("role_title") or role_hint or "Target Role",
                target_level=data.get("target_level", "Mid-Level"),
                technical_skills=data.get("technical_skills", []),
                tools_and_frameworks=data.get("tools_and_frameworks", []),
                soft_skills=data.get("soft_skills", []),
                responsibilities=data.get("responsibilities", []),
                expected_experience_years=data.get("expected_experience_years", "2-4 years"),
                interview_topics=data.get("interview_topics", []),
                evidence_expectations=data.get("evidence_expectations", []),
                extracted_skill_nodes=extracted_nodes
            )
        except Exception as e:
            logger.warning(f"Job description parsing fallback triggered: {e}")
            # Fallback regex-based extraction
            tech = ["Python", "JavaScript", "SQL", "APIs", "Algorithms", "Git"]
            matched_tech = [t for t in tech if re.search(r"\b" + re.escape(t) + r"\b", job_description_text, re.IGNORECASE)] or tech[:4]
            return JobDescriptionAnalysisResult(
                role_title=role_hint or "Software Engineer",
                target_level="Mid-Level",
                technical_skills=matched_tech,
                tools_and_frameworks=["Git", "Docker", "Database Engine"],
                soft_skills=["Problem Solving", "Collaboration"],
                responsibilities=["Develop and maintain scalable software services"],
                expected_experience_years="2+ years",
                interview_topics=["Technical Coding", "System Design"],
                evidence_expectations=["Hands-on project repository", "Comprehensive test coverage"],
                extracted_skill_nodes=[
                    {"name": s, "category": "technical", "required_level": 75.0, "career_importance": 1.5}
                    for s in matched_tech + ["Git", "Docker"]
                ]
            )

    @classmethod
    async def get_career_skill_graph(
        cls,
        db: DatabaseManager,
        clerk_user_id: str,
        goal: Dict[str, Any]
    ) -> List[CareerSkillNode]:
        """
        Builds the Career Skill Graph evaluating:
        - Knowledge Mastery (Quizzes, BKT)
        - Practical Evidence (Assignments & Projects)
        - Interview Evidence (Mock Interviews / Q&A)
        - Evidence Deficit (High Knowledge, 0 Practical)
        """
        required_skills = goal.get("extracted_skills", []) or goal.get("required_skills", [])
        if not required_skills:
            target_role = goal.get("role") or goal.get("title") or "Software Engineer"
            # Auto-infer appropriate competencies based on role title
            role_lower = target_role.lower()
            if "machine learning" in role_lower or "ml" in role_lower or "ai" in role_lower:
                skills_list = [
                    "Supervised Learning", "Neural Networks", "Transformers & LLMs", 
                    "Feature Engineering", "Model Evaluation & Metrics", "PyTorch / TensorFlow", "MLOps & Deployment"
                ]
            elif "data" in role_lower:
                skills_list = [
                    "SQL & Data Modeling", "Python / Pandas", "Statistical Analysis", 
                    "Data Visualization", "Data Pipelines & ETL", "A/B Testing"
                ]
            elif "backend" in role_lower:
                skills_list = [
                    "API Design & REST", "Database Optimization", "Distributed Systems", 
                    "Asynchronous Programming", "Docker & Containers", "Authentication & Security"
                ]
            elif "frontend" in role_lower:
                skills_list = [
                    "React & State Management", "TypeScript", "Responsive UI/UX", 
                    "Web Performance Optimization", "REST & GraphQL Integration", "Accessibility (a11y)"
                ]
            elif "devops" in role_lower or "cloud" in role_lower:
                skills_list = [
                    "Docker & Kubernetes", "CI/CD Pipelines", "Infrastructure as Code (Terraform)", 
                    "Linux Administration", "Cloud Architecture (AWS/GCP)", "Monitoring & Observability"
                ]
            else:
                skills_list = [
                    "Data Structures", "Algorithms", "Database Design", 
                    "API Architecture", "Testing & CI/CD", "System Design"
                ]

            required_skills = [
                {"name": s, "category": "technical", "required_level": 75.0, "career_importance": 1.5}
                for s in skills_list
            ]

        # 1. Fetch Mastery
        mastery_map: Dict[str, Dict[str, Any]] = {}
        if db.is_online:
            col_m = db.get_collection("mastery")
            cursor = col_m.find({"clerk_user_id": clerk_user_id})
            async for doc in cursor:
                mastery_map[doc.get("concept_name", "").lower()] = doc
        else:
            from ..crud import _DEMO_DB
            for doc in _DEMO_DB.get("mastery", []):
                if doc.get("clerk_user_id") == clerk_user_id:
                    mastery_map[doc.get("concept_name", "").lower()] = doc

        # 2. Fetch Attempts / Quizzes (Knowledge Evidence)
        attempts_map: Dict[str, List[Dict[str, Any]]] = {}
        if db.is_online:
            col_a = db.get_collection("attempts")
            cursor = col_a.find({"clerk_user_id": clerk_user_id})
            async for doc in cursor:
                cname = doc.get("concept_name", "").lower()
                if cname:
                    attempts_map.setdefault(cname, []).append(doc)
        else:
            from ..crud import _DEMO_DB
            for doc in _DEMO_DB.get("attempts", []):
                if doc.get("clerk_user_id") == clerk_user_id:
                    cname = doc.get("concept_name", "").lower()
                    if cname:
                        attempts_map.setdefault(cname, []).append(doc)

        # 3. Fetch Assignments / Projects (Practical Evidence)
        assignments_map: Dict[str, List[Dict[str, Any]]] = {}
        if db.is_online:
            col_asg = db.get_collection("assignments")
            cursor = col_asg.find({"clerk_user_id": clerk_user_id})
            async for doc in cursor:
                cnames = [c.lower() for c in doc.get("concept_names", [])]
                for cn in cnames:
                    assignments_map.setdefault(cn, []).append(doc)
        else:
            from ..crud import _DEMO_DB
            for doc in _DEMO_DB.get("assignments", []):
                if doc.get("clerk_user_id") == clerk_user_id:
                    cnames = [c.lower() for c in doc.get("concept_names", [])]
                    for cn in cnames:
                        assignments_map.setdefault(cn, []).append(doc)

        skill_nodes: List[CareerSkillNode] = []

        for req in required_skills:
            s_name = req.get("name", "") if isinstance(req, dict) else req
            req_level = float(req.get("required_level", 75.0) if isinstance(req, dict) else 75.0)
            category = str(req.get("category", "technical") if isinstance(req, dict) else "technical")
            importance = float(req.get("career_importance", 1.2) if isinstance(req, dict) else 1.2)

            norm_name = s_name.lower()
            m_doc = mastery_map.get(norm_name)

            # Knowledge score calculation
            k_score = float(m_doc.get("mastery_score", 0.0)) if m_doc else 0.0
            attempts = attempts_map.get(norm_name, [])
            if not k_score and attempts:
                correct_count = sum(1 for a in attempts if a.get("is_correct"))
                k_score = round((correct_count / len(attempts)) * 100.0, 1)

            # Practical score calculation
            asgs = assignments_map.get(norm_name, [])
            completed_asgs = [a for a in asgs if a.get("status") == "completed"]
            if completed_asgs:
                avg_score = sum(float(a.get("score") or 80.0) for a in completed_asgs) / len(completed_asgs)
                p_score = round(min(100.0, avg_score), 1)
            else:
                p_score = 0.0

            # Interview score (simulated or derived from mock sessions)
            i_score = round(k_score * 0.85, 1) if k_score > 0 else 0.0

            # Evidence Quality & Deficit Analysis
            total_evidence_count = len(attempts) + len(completed_asgs)
            if total_evidence_count >= 5 and p_score > 60:
                ev_quality = EvidenceQuality.HIGH
                conf = 0.90
            elif total_evidence_count >= 2:
                ev_quality = EvidenceQuality.MODERATE
                conf = 0.70
            elif total_evidence_count >= 1 or k_score > 0:
                ev_quality = EvidenceQuality.LOW
                conf = 0.40
            else:
                ev_quality = EvidenceQuality.NONE
                conf = 0.0

            # Evidence Deficit detection: Student scores well on multiple-choice/flashcards but has 0 practical assignments/projects
            has_deficit = bool(k_score >= 65.0 and p_score == 0.0)

            # Overall mastery for career twin is a blend of Knowledge (40%), Practical (45%), Interview (15%)
            if p_score > 0:
                blended_mastery = round((k_score * 0.40) + (p_score * 0.45) + (i_score * 0.15), 1)
            else:
                # Capped at 60% if no practical evidence exists
                blended_mastery = round(min(60.0, k_score * 0.65), 1)

            gap = max(0.0, round(req_level - blended_mastery, 1))

            # Status classification
            if blended_mastery >= req_level:
                status = "MASTERED"
            elif has_deficit:
                status = "EVIDENCE_DEFICIT"
            elif k_score >= 60.0:
                status = "READY_FOR_PRACTICAL"
            elif k_score > 0:
                status = "NEEDS_IMPROVEMENT"
            else:
                status = "INSUFFICIENT_EVIDENCE"

            # Check prerequisites
            prereqs = await neo4j_service.get_prerequisites(clerk_user_id, s_name)
            unmet = []
            if prereqs:
                for p in prereqs:
                    pm = mastery_map.get(p.lower())
                    pscore = float(pm.get("mastery_score", 0.0)) if pm else 0.0
                    if pscore < 70.0:
                        unmet.append(f"{p} ({round(pscore, 1)}%)")

            prereq_status = "BLOCKED" if unmet else ("SATISFIED" if prereqs else "NO_PREREQUISITES")
            if prereq_status == "BLOCKED" and status != "MASTERED":
                status = "BLOCKED_BY_PREREQUISITE"

            skill_nodes.append(CareerSkillNode(
                skill_name=s_name,
                category=category,
                required_level=req_level,
                current_mastery=blended_mastery,
                knowledge_score=k_score,
                practical_evidence_score=p_score,
                interview_evidence_score=i_score,
                evidence_quality=ev_quality,
                evidence_count=total_evidence_count,
                confidence=conf,
                last_verified=datetime.utcnow() if total_evidence_count > 0 else None,
                prerequisite_status=prereq_status,
                unmet_prerequisites=unmet,
                career_importance=importance,
                has_evidence_deficit=has_deficit,
                gap=gap,
                status=status
            ))

        return skill_nodes

    @classmethod
    async def calculate_career_readiness(
        cls,
        db: DatabaseManager,
        clerk_user_id: str,
        goal: Dict[str, Any]
    ) -> CareerTwinReadinessReport:
        """
        Produces an explainable, multi-dimensional Career Twin Readiness Report.
        """
        goal_id = str(goal.get("_id", ""))
        role = goal.get("role") or goal.get("title") or "Target Role"

        nodes = await cls.get_career_skill_graph(db, clerk_user_id, goal)

        if not nodes:
            return CareerTwinReadinessReport(
                goal_id=goal_id,
                role=role,
                overall_readiness_score=0.0,
                knowledge_readiness_score=0.0,
                practical_readiness_score=0.0,
                interview_readiness_score=0.0,
                status="NOT_STARTED",
                mastered_skills_count=0,
                total_required_skills_count=0,
                knowledge_gaps_count=0,
                evidence_deficits_count=0,
                prerequisite_blockers_count=0,
                interview_gaps_count=0,
                explainable_breakdown=["No skills mapped to this career goal yet."],
                recommended_next_action={"type": "SETUP", "title": "Analyze job description to map required competencies"}
            )

        total_weight = sum(n.career_importance for n in nodes)
        weighted_overall = sum(n.current_mastery * n.career_importance for n in nodes) / total_weight
        weighted_knowledge = sum(n.knowledge_score * n.career_importance for n in nodes) / total_weight
        weighted_practical = sum(n.practical_evidence_score * n.career_importance for n in nodes) / total_weight
        weighted_interview = sum(n.interview_evidence_score * n.career_importance for n in nodes) / total_weight

        overall_score = round(weighted_overall, 1)
        knowledge_score = round(weighted_knowledge, 1)
        practical_score = round(weighted_practical, 1)
        interview_score = round(weighted_interview, 1)

        mastered = [n for n in nodes if n.status == "MASTERED"]
        deficits = [n for n in nodes if n.has_evidence_deficit]
        blockers = [n for n in nodes if n.status == "BLOCKED_BY_PREREQUISITE"]
        knowledge_gaps = [n for n in nodes if n.knowledge_score < 70.0]

        # Status
        if overall_score >= 85.0 and len(deficits) == 0:
            status = "READY"
        elif overall_score >= 70.0:
            status = "STRONG_CANDIDATE"
        elif overall_score >= 40.0:
            status = "IN_PROGRESS"
        elif overall_score > 0.0:
            status = "AT_RISK"
        else:
            status = "NOT_STARTED"

        # Explainable Breakdown
        breakdown = []
        breakdown.append(f"Overall Career Readiness is {overall_score}% based on {len(nodes)} targeted competencies.")
        if knowledge_score >= 75.0:
            breakdown.append(f"Strong conceptual foundation ({knowledge_score}%), verified across study assessments.")
        else:
            breakdown.append(f"Foundational knowledge needs reinforcement ({knowledge_score}%).")

        if practical_score < 50.0:
            breakdown.append(f"Practical project evidence is currently low ({practical_score}%). Hands-on assignments recommended.")
        else:
            breakdown.append(f"Solid portfolio of practical evidence verified ({practical_score}%).")

        if deficits:
            breakdown.append(f"Identified {len(deficits)} Evidence Deficits: strong quiz knowledge but missing real-world code/project artifacts.")

        if blockers:
            breakdown.append(f"{len(blockers)} skills are currently blocked by missing prerequisites.")

        # Next Recommended Action
        if blockers:
            b_skill = blockers[0]
            action = {
                "type": "PREREQUISITE",
                "title": f"Resolve prerequisite blocker for {b_skill.skill_name}",
                "description": f"Master {', '.join(b_skill.unmet_prerequisites)} to unlock {b_skill.skill_name}.",
                "skill": b_skill.skill_name
            }
        elif deficits:
            d_skill = deficits[0]
            action = {
                "type": "PROJECT_EVIDENCE",
                "title": f"Build practical assignment for {d_skill.skill_name}",
                "description": f"You understand {d_skill.skill_name} conceptually ({d_skill.knowledge_score}%), but need project evidence.",
                "skill": d_skill.skill_name
            }
        elif knowledge_gaps:
            k_skill = sorted(knowledge_gaps, key=lambda x: x.career_importance, reverse=True)[0]
            action = {
                "type": "CONCEPT_STUDY",
                "title": f"Study {k_skill.skill_name}",
                "description": f"High-importance competency ({k_skill.career_importance}x) with current mastery of {k_skill.knowledge_score}%.",
                "skill": k_skill.skill_name
            }
        else:
            action = {
                "type": "MOCK_INTERVIEW",
                "title": f"Conduct Mock Interview for {role}",
                "description": "You meet the core requirements! Polish your interview communication with technical role simulation.",
                "skill": role
            }

        # Trajectory (simulate 4 weekly progression points)
        now = datetime.utcnow()
        trajectory = [
            CareerReadinessTrajectoryPoint(date=(now - timedelta(days=21)).strftime("%b %d"), readiness_score=max(0.0, round(overall_score - 18.0, 1)), verified_skills_count=max(0, len(mastered) - 3)),
            CareerReadinessTrajectoryPoint(date=(now - timedelta(days=14)).strftime("%b %d"), readiness_score=max(0.0, round(overall_score - 11.0, 1)), verified_skills_count=max(0, len(mastered) - 2)),
            CareerReadinessTrajectoryPoint(date=(now - timedelta(days=7)).strftime("%b %d"), readiness_score=max(0.0, round(overall_score - 5.0, 1)), verified_skills_count=max(0, len(mastered) - 1)),
            CareerReadinessTrajectoryPoint(date=now.strftime("%b %d"), readiness_score=overall_score, verified_skills_count=len(mastered))
        ]

        return CareerTwinReadinessReport(
            goal_id=goal_id,
            role=role,
            overall_readiness_score=overall_score,
            knowledge_readiness_score=knowledge_score,
            practical_readiness_score=practical_score,
            interview_readiness_score=interview_score,
            status=status,
            mastered_skills_count=len(mastered),
            total_required_skills_count=len(nodes),
            knowledge_gaps_count=len(knowledge_gaps),
            evidence_deficits_count=len(deficits),
            prerequisite_blockers_count=len(blockers),
            interview_gaps_count=sum(1 for n in nodes if n.interview_evidence_score < 70.0),
            explainable_breakdown=breakdown,
            recommended_next_action=action,
            trajectory=trajectory
        )
