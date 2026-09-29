"""
MK-Path 2.0 Agent Models
Unified context, citations, conversations, and intent schemas.
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class AgentIntent(str, Enum):
    DOCUMENT_QA = "DOCUMENT_QA"
    LEARNING_EXPLANATION = "LEARNING_EXPLANATION"
    CONCEPT_TUTOR = "CONCEPT_TUTOR"
    CAREER_GUIDANCE = "CAREER_GUIDANCE"
    SKILL_GAP = "SKILL_GAP"
    CURRENT_INDUSTRY = "CURRENT_INDUSTRY"
    PROJECT_GUIDANCE = "PROJECT_GUIDANCE"
    INTERVIEW_PREPARATION = "INTERVIEW_PREPARATION"
    STUDY_PLANNING = "STUDY_PLANNING"
    RESOURCE_SEARCH = "RESOURCE_SEARCH"
    GENERAL = "GENERAL"

class SourceCategory(str, Enum):
    LEARNER_MATERIAL = "learner_material"
    INTERNAL_LEARNER_STATE = "internal_learner_state"
    WEB_CURRENT_SOURCE = "web_current_source"
    AI_GENERATED = "ai_generated"
    YOUTUBE_SOURCE = "youtube_source"

class SourceCitation(BaseModel):
    source_type: SourceCategory
    title: str
    reference_id: Optional[str] = None
    snippet: Optional[str] = None
    page: Optional[int] = None
    timestamp_seconds: Optional[float] = None
    timestamp_formatted: Optional[str] = None
    url: Optional[str] = None
    confidence: float = 1.0

class LearnerContext(BaseModel):
    learner_id: str
    display_name: Optional[str] = None
    goals: List[Dict[str, Any]] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    mastery: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty: Dict[str, float] = Field(default_factory=dict)
    misconceptions: List[Dict[str, Any]] = Field(default_factory=list)
    prerequisites: List[Dict[str, Any]] = Field(default_factory=list)
    skill_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)
    study_path: List[Dict[str, Any]] = Field(default_factory=list)
    assessment_history: List[Dict[str, Any]] = Field(default_factory=list)
    career_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    materials_summary: List[Dict[str, Any]] = Field(default_factory=list)
    youtube_summary: List[Dict[str, Any]] = Field(default_factory=list)
    grounded_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    web_knowledge: List[Dict[str, Any]] = Field(default_factory=list)

class AgentChatMessage(BaseModel):
    role: str = Field(..., description="'user' | 'assistant' | 'system'")
    content: str
    intent: Optional[AgentIntent] = None
    citations: List[SourceCitation] = Field(default_factory=list)
    action_suggestion: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentConversation(BaseModel):
    clerk_user_id: str
    title: str = "New AI Learning Consultation"
    messages: List[AgentChatMessage] = Field(default_factory=list)
    active_intent: AgentIntent = AgentIntent.GENERAL
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AgentChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    override_intent: Optional[AgentIntent] = None
    include_web_search: bool = False
    context_focus_concept: Optional[str] = None
    context_material_id: Optional[str] = None

class AgentChatResponse(BaseModel):
    conversation_id: str
    message: AgentChatMessage
    intent_detected: AgentIntent
    sources_used: List[SourceCitation] = Field(default_factory=list)
    recommended_next_action: Optional[Dict[str, Any]] = None
