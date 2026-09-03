from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Pydantic Models for Schema Validation ---

class UserProfile(BaseModel):
    clerk_user_id: str = Field(..., description="Unique authenticated Clerk User ID")
    email: str = Field(..., description="Primary email address")
    display_name: str = Field(..., description="User full name or display name")
    avatar_url: Optional[str] = Field(None, description="URL of user profile avatar")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Material(BaseModel):
    clerk_user_id: str = Field(...)
    title: str = Field(..., description="Name or title of study material")
    file_name: str = Field(...)
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="Content mime-type (e.g. application/pdf)")
    raw_text: str = Field(..., description="Plaintext content extracted from file")
    status: str = Field("processing", description="'processing', 'processed', or 'failed'")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Extended properties for Multimodal Content Ingestion (Phase 12)
    source_type: str = Field("pdf", description="pdf, txt, image, audio, video")
    mime_type: str = Field("application/pdf", description="MIME type of uploaded file")
    duration: Optional[float] = Field(None, description="Duration in seconds for audio/video")
    page_count: Optional[int] = Field(None, description="Number of pages for PDFs")
    transcription_status: str = Field("n/a", description="n/a, processing, completed, failed")
    ocr_status: str = Field("n/a", description="n/a, processing, completed, failed")
    extraction_method: str = Field("direct_text", description="direct_text, ocr, transcription")
    segments: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted segments or timestamps layout blocks")



class Concept(BaseModel):
    clerk_user_id: str = Field(...)
    material_id: str = Field(..., description="Reference to materials collection _id")
    name: str = Field(..., description="Name of the extracted concept")
    description: str = Field(...)
    exam_relevance: int = Field(..., ge=0, le=100)
    industry_relevance: int = Field(..., ge=0, le=100)
    difficulty: str = Field(..., description="basic, intermediate, advanced")
    prerequisites: List[str] = Field(default_factory=list, description="List of prerequisite concept names")
    source_refs: List[Dict[str, Any]] = Field(default_factory=list, description="References to document chunks")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Relationship(BaseModel):
    clerk_user_id: str = Field(...)
    material_id: str = Field(..., description="Reference to materials collection _id")
    source_concept_name: str = Field(...)
    target_concept_name: str = Field(...)
    relationship_type: str = Field(..., description="e.g. prerequisite_of, builds_on")
    relationship_origin: str = Field("explicit", description="explicit or inferred")
    confidence: Optional[float] = Field(None, description="Inferred confidence score")
    source_refs: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Question(BaseModel):
    clerk_user_id: str = Field(...)
    concept_id: str = Field(..., description="Reference to concepts collection _id")
    concept_name: str = Field(...)
    question_text: str = Field(...)
    options: List[str] = Field(..., min_items=4, max_items=4, description="4 multiple choice options")
    correct_option_index: int = Field(..., ge=0, le=3)
    difficulty: str = Field(...)
    explanation: str = Field(...)
    source_refs: List[Dict[str, Any]] = Field(default_factory=list)

class Attempt(BaseModel):
    clerk_user_id: str = Field(...)
    concept_id: str = Field(..., description="Reference to concepts collection _id")
    question_id: str = Field(..., description="Reference to questions collection _id")
    selected_option_index: int = Field(...)
    is_correct: bool = Field(...)
    confidence: int = Field(..., ge=1, le=5, description="Learner self-reported confidence 1-5")
    response_time_seconds: float = Field(..., description="Time taken to answer in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Mastery(BaseModel):
    clerk_user_id: str = Field(...)
    concept_id: str = Field(...)
    concept_name: str = Field(...)
    mastery_score: float = Field(..., ge=0.0, le=100.0)
    category: str = Field("Weak", description="Weak, Learning, Proficient, Mastered")
    last_reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    next_review: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    accuracy_rolling: float = Field(0.0)
    confidence_rolling: float = Field(0.0)
    speed_rolling: float = Field(0.0)
    
    # Shadow Tracing variables (Phase 15)
    baseline_mastery: Optional[float] = None
    knowledge_tracing_mastery: Optional[float] = None
    kt_uncertainty: Optional[float] = None
    kt_mastery_probability: Optional[float] = None
    active_mastery_model: str = Field("baseline", description="baseline or knowledge_tracing")


class LearnerEvent(BaseModel):
    clerk_user_id: str = Field(...)
    event_type: str = Field(..., description="e.g. material_uploaded, question_answered")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    material_id: Optional[str] = None
    concept_id: Optional[str] = None
    question_id: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)



class StudyPathItem(BaseModel):
    concept_id: str = Field(...)
    concept_name: str = Field(...)
    priority_score: float = Field(...)
    reason: str = Field(...)

class StudyPath(BaseModel):
    clerk_user_id: str = Field(...)
    ordered_concepts: List[StudyPathItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Resource(BaseModel):
    concept_name: str = Field(...)
    title: str = Field(...)
    type: str = Field(..., description="article, video, documentation")
    url: str = Field(...)
    trust_score: int = Field(..., ge=0, le=100)
    difficulty: str = Field("basic", description="basic, intermediate, advanced")
    freshness_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ResourceFeedback(BaseModel):
    clerk_user_id: str = Field(...)
    resource_id: str = Field(...)
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5 stars rating")
    helpful: Optional[bool] = Field(None, description="helpful (True) or not helpful (False)")
    completed: bool = Field(False, description="True if learner completed the resource")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Gamification(BaseModel):
    clerk_user_id: str = Field(...)
    xp: int = Field(0, ge=0)
    level: int = Field(1, ge=1)
    level_name: str = Field("Beginner")
    achievements: List[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AttemptSubmit(BaseModel):
    question_id: str
    selected_option_index: int
    confidence: int = Field(..., ge=1, le=5)
    response_time_seconds: float = Field(..., ge=0.0)


class UserPreferences(BaseModel):
    """Extended learner profile preferences stored in MongoDB (separate from Clerk identity)."""
    clerk_user_id: str = Field(...)
    preferred_name: Optional[str] = None
    learning_goal: Optional[str] = None
    target_role: Optional[str] = None
    preferred_difficulty: str = Field("intermediate", description="basic, intermediate, advanced")
    daily_study_target_minutes: int = Field(30, ge=5, le=480)
    preferred_session_duration_minutes: int = Field(25, ge=5, le=120)
    exam_target: Optional[str] = None
    industry_interests: List[str] = Field(default_factory=list)
    preferred_resource_types: List[str] = Field(default_factory=list, description="video, article, documentation")
    notifications_enabled: bool = Field(True)
    reduced_motion: bool = Field(False)
    font_size: str = Field("medium", description="small, medium, large, xlarge")
    tts_enabled: bool = Field(False)
    tts_rate: float = Field(1.0, ge=0.5, le=2.0)
    high_contrast: bool = Field(False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialChunk(BaseModel):
    """Semantic chunk of a study material with vector embedding."""
    chunk_id: str = Field(...)
    material_id: str = Field(...)
    clerk_user_id: str = Field(...)
    sequence: int = Field(...)
    text: str = Field(...)
    embedding: List[float] = Field(default_factory=list)
    embedding_model: Optional[str] = Field(None)
    embedding_status: str = Field("completed", description="completed, failed")
    page: Optional[int] = Field(None)
    section: Optional[str] = Field(None)
    start_time: Optional[float] = Field(None)
    end_time: Optional[float] = Field(None)
    token_count: Optional[int] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserActivity(BaseModel):
    """Activity tracking for analytics and personalization."""
    event_id: str = Field(...)
    clerk_user_id: str = Field(...)
    event_type: str = Field(..., description="e.g. material_uploaded, concept_generated, assessment_started, etc.")
    session_id: Optional[str] = Field(None)
    entity_type: Optional[str] = Field(None)
    entity_id: Optional[str] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AssignmentQuestion(BaseModel):
    """A single question within an assignment."""
    question_id: Optional[str] = None
    question_text: str
    question_type: str = Field("mcq", description="mcq, true_false, short_answer")
    options: List[str] = Field(default_factory=list, description="Options for MCQ/True-False")
    correct_option_index: Optional[int] = None
    concept_name: Optional[str] = None
    difficulty: str = Field("basic")
    explanation: Optional[str] = None
    source_refs: List[Dict[str, Any]] = Field(default_factory=list)


class Assignment(BaseModel):
    """A learning assignment with lifecycle management."""
    clerk_user_id: str = Field(...)
    title: str = Field(...)
    description: str = Field(default="")
    source_material_ids: List[str] = Field(default_factory=list)
    concept_ids: List[str] = Field(default_factory=list)
    concept_names: List[str] = Field(default_factory=list)
    questions: List[AssignmentQuestion] = Field(default_factory=list)
    difficulty: str = Field("intermediate")
    estimated_duration_minutes: int = Field(20)
    due_date: Optional[datetime] = None
    status: str = Field("pending", description="pending, in_progress, completed, overdue")
    score: Optional[float] = None
    accuracy: Optional[float] = None
    time_spent_seconds: Optional[float] = None
    draft_answers: Dict[str, Any] = Field(default_factory=dict, description="Saved in-progress answers keyed by question index")
    assignment_type: str = Field("ai_generated", description="ai_generated, concept_based, material_based, manual, practice")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    feedback: Optional[str] = None


class UserLearningContext(BaseModel):
    profile: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    goals: Dict[str, Any] = Field(default_factory=dict)
    mastery: Dict[str, Any] = Field(default_factory=dict)
    activity: List[Dict[str, Any]] = Field(default_factory=list)
    weak_concepts: List[Dict[str, Any]] = Field(default_factory=list)
    recent_materials: List[Dict[str, Any]] = Field(default_factory=list)


class RAGContext(BaseModel):
    user_context: UserLearningContext
    query: str
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    task_type: str = Field(...)
    current_concept: Optional[Dict[str, Any]] = None
    current_material: Optional[Dict[str, Any]] = None
    learning_state: Optional[Dict[str, Any]] = None


# --- Spaced Repetition Flashcard System Models ---

class Flashcard(BaseModel):
    """An active recall flashcard generated from concept or material."""
    clerk_user_id: str = Field(...)
    concept_id: str = Field(..., description="Target concept ID")
    concept_name: str = Field(...)
    material_id: Optional[str] = Field(None, description="Optional source material ID")
    front: str = Field(..., description="Flashcard question/prompt/term")
    back: str = Field(..., description="Flashcard answer/explanation/key points")
    card_type: str = Field("standard", description="standard, cloze, code, scenario")
    difficulty: str = Field("basic", description="basic, intermediate, advanced")
    
    # SM-2 / Anki Algorithm Parameters
    repetitions: int = Field(0, description="Consecutive successful recall repetitions")
    interval_days: float = Field(1.0, description="Interval in days until next review")
    ease_factor: float = Field(2.5, description="SM-2 Ease Factor (minimum 1.3)")
    last_reviewed_at: Optional[datetime] = None
    next_review_at: datetime = Field(default_factory=datetime.utcnow)
    state: str = Field("new", description="new, learning, review, mastered")
    
    # Observability & Metadata
    total_reviews: int = Field(0)
    lapses: int = Field(0, description="Count of failing recall on review card")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FlashcardReviewRequest(BaseModel):
    """Payload when a user reviews a flashcard."""
    card_id: str
    rating: int = Field(..., ge=1, le=4, description="1: Again (Fail), 2: Hard, 3: Good, 4: Easy")
    response_time_seconds: Optional[float] = Field(5.0)


class GenerateFlashcardsRequest(BaseModel):
    """Payload to generate AI flashcards for concepts or materials."""
    concept_ids: Optional[List[str]] = Field(default_factory=list)
    material_id: Optional[str] = None
    cards_per_concept: int = Field(2, ge=1, le=10)
    include_scenarios: bool = Field(True)


class MindMapNode(BaseModel):
    id: str
    label: str
    details: Optional[str] = None
    children: Optional[List['MindMapNode']] = Field(default_factory=list)


class StudyNote(BaseModel):
    """Structured hierarchical study notes and mind-map trees for concepts/materials."""
    clerk_user_id: str
    concept_id: Optional[str] = None
    concept_name: str
    material_id: Optional[str] = None
    title: str
    summary: str
    key_takeaways: List[str] = Field(default_factory=list)
    formulae_or_rules: List[str] = Field(default_factory=list)
    common_pitfalls: List[str] = Field(default_factory=list)
    mind_map_tree: Optional[Dict[str, Any]] = Field(default_factory=dict)
    markdown_content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GenerateStudyNotesRequest(BaseModel):
    concept_ids: Optional[List[str]] = Field(default_factory=list)
    material_id: Optional[str] = None
    depth: str = Field("comprehensive", description="concise or comprehensive")


class TutorChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    role: str = Field(..., description="user, assistant, or system")
    content: str
    concept_references: List[str] = Field(default_factory=list)
    source_chunk_ids: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TutorSession(BaseModel):
    """Conversational Socratic tutoring session grounded in user concepts & chunks."""
    clerk_user_id: str
    concept_id: Optional[str] = None
    concept_name: Optional[str] = None
    session_title: str = Field("Socratic Tutoring Session")
    messages: List[TutorChatMessage] = Field(default_factory=list)
    learning_goals: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TutorChatRequest(BaseModel):
    session_id: Optional[str] = None
    concept_id: Optional[str] = None
    concept_name: Optional[str] = None
    message: str
    tutor_mode: str = Field("socratic", description="socratic (guided inquiry), direct_explainer, or exam_coach")


class PodcastDialogueTurn(BaseModel):
    speaker: str = Field(..., description="'Alex' (deep-dive expert host) or 'Sam' (curious co-host)")
    text: str = Field(..., description="Spoken dialogue line")
    emotion: Optional[str] = Field("enthusiastic", description="enthusiastic, questioning, explanatory, humorous")
    pitch: Optional[float] = Field(1.0, description="Voice pitch multiplier for TTS")
    rate: Optional[float] = Field(1.0, description="Voice speech rate for TTS")


class PodcastOverview(BaseModel):
    """Deep-dive dynamic multi-speaker audio podcast generated from user materials."""
    clerk_user_id: str
    material_id: Optional[str] = None
    material_title: Optional[str] = None
    concept_ids: List[str] = Field(default_factory=list)
    title: str
    summary: str
    episode_duration_est_minutes: float = Field(3.5)
    hosts: List[str] = Field(default_factory=lambda: ["Alex (Lead Researcher)", "Sam (Curious Explorer)"])
    script: List[PodcastDialogueTurn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratePodcastRequest(BaseModel):
    material_id: Optional[str] = None
    concept_ids: Optional[List[str]] = Field(default_factory=list)
    style: str = Field("dynamic", description="dynamic (engaging & lively), academic (deep analytical), or exam_prep (high-yield rapid recall)")



