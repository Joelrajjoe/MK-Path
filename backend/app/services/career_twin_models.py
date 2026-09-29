"""
Career Twin Models & Schemas
MK-Path 2.0 Phase 3
Persistent Digital Career Twin with multi-dimensional evidence modeling:
- Knowledge Mastery (Quizzes, BKT, Knowledge Graph)
- Practical / Project Evidence (Assignments, Repositories, Uploaded artifacts)
- Assessment Evidence (Adaptive diagnostics, Exam readiness)
- Interview Evidence (Mock technical/system design interviews)
- Evidence Deficit & Explainable Readiness Score
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class EvidenceType(str, Enum):
    KNOWLEDGE_ASSESSMENT = "KNOWLEDGE_ASSESSMENT"
    PRACTICAL_PROJECT = "PRACTICAL_PROJECT"
    ASSIGNMENT = "ASSIGNMENT"
    MOCK_INTERVIEW = "MOCK_INTERVIEW"
    LEARNER_ARTIFACT = "LEARNER_ARTIFACT"


class EvidenceQuality(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    NONE = "NONE"


class SkillEvidenceItem(BaseModel):
    evidence_id: str = Field(..., description="ID of the assessment attempt, assignment, project, or interview")
    evidence_type: EvidenceType
    title: str = Field(..., description="Name of the assessment, assignment, or project")
    score_or_performance: float = Field(..., description="Numeric score 0-100 or rating")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[str] = None
    artifact_url_or_ref: Optional[str] = None


class CareerSkillNode(BaseModel):
    skill_name: str
    category: str = Field("technical", description="technical, tool, framework, soft_skill, architecture")
    required_level: float = Field(75.0, ge=0.0, le=100.0)
    current_mastery: float = Field(0.0, ge=0.0, le=100.0)
    knowledge_score: float = Field(0.0, ge=0.0, le=100.0)
    practical_evidence_score: float = Field(0.0, ge=0.0, le=100.0)
    interview_evidence_score: float = Field(0.0, ge=0.0, le=100.0)
    evidence_quality: EvidenceQuality = Field(EvidenceQuality.NONE)
    evidence_count: int = 0
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    last_verified: Optional[datetime] = None
    prerequisite_status: str = Field("SATISFIED", description="SATISFIED, BLOCKED, NO_PREREQUISITES")
    unmet_prerequisites: List[str] = Field(default_factory=list)
    career_importance: float = Field(1.0, ge=0.1, le=5.0)
    has_evidence_deficit: bool = Field(False, description="True if knowledge mastery >= 70 but practical/project evidence == 0")
    gap: float = 0.0
    status: str = Field("INSUFFICIENT_EVIDENCE")  # MASTERED, READY, NEEDS_IMPROVEMENT, BLOCKED_BY_PREREQUISITE, INSUFFICIENT_EVIDENCE, EVIDENCE_DEFICIT


class CareerTwinGoal(BaseModel):
    clerk_user_id: str
    role: str = Field(..., description="Target role e.g. Senior Backend Engineer")
    company_or_industry: Optional[str] = Field(None, description="e.g. Distributed Systems / Fintech / Google")
    experience_level: str = Field("Mid-Level", description="Entry-Level, Mid-Level, Senior, Staff, Principal")
    location_preference: str = Field("Remote", description="Remote, Hybrid, On-site")
    target_date: Optional[datetime] = None
    job_description_raw: Optional[str] = None
    job_url: Optional[str] = None
    extracted_skills: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobDescriptionAnalysisResult(BaseModel):
    role_title: str
    target_level: str
    technical_skills: List[str] = Field(default_factory=list)
    tools_and_frameworks: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    expected_experience_years: Optional[str] = None
    interview_topics: List[str] = Field(default_factory=list)
    evidence_expectations: List[str] = Field(default_factory=list)
    extracted_skill_nodes: List[Dict[str, Any]] = Field(default_factory=list)


class CareerReadinessTrajectoryPoint(BaseModel):
    date: str
    readiness_score: float
    verified_skills_count: int


class CareerTwinReadinessReport(BaseModel):
    goal_id: str
    role: str
    overall_readiness_score: float  # 0 to 100 explainable weighted aggregate
    knowledge_readiness_score: float
    practical_readiness_score: float
    interview_readiness_score: float
    status: str  # READY, STRONG_CANDIDATE, IN_PROGRESS, AT_RISK, NOT_STARTED
    mastered_skills_count: int
    total_required_skills_count: int
    knowledge_gaps_count: int
    evidence_deficits_count: int
    prerequisite_blockers_count: int
    interview_gaps_count: int
    explainable_breakdown: List[str] = Field(default_factory=list)
    recommended_next_action: Dict[str, Any] = Field(default_factory=dict)
    trajectory: List[CareerReadinessTrajectoryPoint] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
