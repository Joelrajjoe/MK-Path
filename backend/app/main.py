import logging
import math
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz
from .config import settings
from .database import db_manager, get_db
from .auth import get_current_user
from . import crud
from .models import (
    UserProfile, Material, MaterialStatus, Concept, Relationship, Question, Attempt, 
    Mastery, AttemptSubmit, Gamification, LearnerEvent, UserPreferences, 
    Assignment, AssignmentQuestion, ResourceFeedback, Flashcard, 
    FlashcardReviewRequest, GenerateFlashcardsRequest, StudyNote, GenerateStudyNotesRequest,
    TutorChatMessage, TutorSession, TutorChatRequest,
    PodcastOverview, PodcastDialogueTurn, GeneratePodcastRequest,
    Goal, RequiredSkill, SkillGap, GoalGapAnalysis,
    DiagnosisRequest, LearningDiagnosis, SimulationRequest, SimulationResult,
    NextBestActionRecommendation, MasteryEvidenceChain
)
from .services.ai import AIService
from .services.goal_service import GoalGapAnalysisService
from .services.diagnosis_service import LearningDiagnosisService
from .services.simulation_service import LearningSimulationService
from .services.nba_service import NextBestLearningActionService
from .services.mastery_evidence_service import MasteryEvidenceChainService
from .services.extractors import (
    PDFExtractor,
    TextExtractor,
    OCRExtractor,
    AudioExtractor,
    VideoExtractor
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mkpath.main")

app = FastAPI(
    title="MK-Path API",
    description="Multimodal Knowledge-Graph Framework for Adaptive Learning",
    version="1.0.0"
)
from .services.neo4j_service import neo4j_service
from .services.kt_service import KTService
from .services.adaptive_policy import AdaptivePolicy
from .services.planner import (
    BaselinePlanner,
    GraphAwarePlanner,
    RLStudyPathPlanner,
    run_simulation_comparison
)
from .services.recommender import BaselineResourceRanker, TrustAwareResourceRanker, run_recommender_evaluation
from .services.gamification_service import GamificationService

# Configure CORS for React/Vite frontend and mobile clients (running on localhost ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175"
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    logger.info("Initializing database client...")
    # Trigger lazy connection on startup to check connectivity
    await db_manager.connect()
    if db_manager.is_online:
        logger.info("Database initialized online.")
    else:
        logger.warning("Database initialized offline (Demo Mode active).")

@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Closing database client...")
    await db_manager.close()

# --- Public Endpoints ---

@app.get("/")
async def root():
    """
    Root landing response for Render/Vercel health checks and API index.
    """
    return {
        "name": "MK-Path API",
        "version": "1.0.0",
        "status": "healthy",
        "docs_url": "/docs",
        "health_check": "/api/health"
    }

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """
    Public health check endpoint displaying system and database status.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database_online": db_manager.is_online,
        "demo_mode": settings.DEMO_MODE or not db_manager.is_online
    }

# --- Protected Endpoints ---

@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Returns the authenticated Clerk user identity.
    """
    return {
        "clerk_user_id": current_user["clerk_user_id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "is_demo": current_user.get("is_demo", False)
    }

@app.get("/api/user/profile")
async def get_user_profile(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Protected route retrieving full user profile enriched with extended learning preferences and gamification level.
    """
    clerk_id = current_user["clerk_user_id"]
    email = current_user["email"]
    name = current_user["name"]
    avatar_url = current_user.get("avatar_url", "")

    profile_model = UserProfile(
        clerk_user_id=clerk_id,
        email=email,
        display_name=name,
        avatar_url=avatar_url,
        updated_at=datetime.utcnow()
    )

    try:
        profile_record = await crud.create_or_update_user_profile(db, profile_model)
        prefs = await crud.get_user_preferences(db, clerk_id) or {}
        gamification = await crud.get_gamification(db, clerk_id) or {}
        
        merged_profile = {
            **profile_record,
            "display_name": prefs.get("display_name") or prefs.get("preferred_name") or profile_record.get("display_name") or name,
            "preferred_name": prefs.get("preferred_name"),
            "target_role": prefs.get("target_role"),
            "target_exam": prefs.get("target_exam") or prefs.get("exam_target"),
            "current_level": prefs.get("current_level") or gamification.get("level_name", "Beginner"),
            "level": gamification.get("level", 1),
            "xp": gamification.get("xp", 0),
            "preferred_difficulty": prefs.get("preferred_difficulty", "intermediate"),
            "daily_study_target_minutes": prefs.get("daily_study_target_minutes", 30),
            "preferred_session_duration_minutes": prefs.get("preferred_session_duration_minutes", 25),
            "deadline": prefs.get("deadline"),
            "preferences": prefs
        }
        return merged_profile
    except Exception as e:
        logger.error(f"Error upserting user profile: {e}")
        return {
            "clerk_user_id": clerk_id,
            "email": email,
            "display_name": name,
            "avatar_url": avatar_url,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_demo_profile": True
        }

# --- Protected Endpoint Stubs (Return 501 / Mock until implemented in later phases) ---

@app.post("/api/materials/upload")
async def upload_material(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    filename = file.filename
    content_type = file.content_type or ""

    # 1. Determine extractor based on file extension / MIME type
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    pdf_exts = {"pdf"}
    txt_exts = {"txt"}
    img_exts = {"png", "jpg", "jpeg", "bmp", "webp"}
    audio_exts = {"mp3", "wav", "m4a", "ogg", "flac"}
    video_exts = {"mp4", "avi", "webm", "mkv", "mov"}

    if ext in pdf_exts or content_type == "application/pdf":
        source_type = "pdf"
        extractor = PDFExtractor()
    elif ext in txt_exts or content_type.startswith("text/"):
        source_type = "txt"
        extractor = TextExtractor()
    elif ext in img_exts or content_type.startswith("image/"):
        source_type = "image"
        extractor = OCRExtractor()
    elif ext in audio_exts or content_type.startswith("audio/"):
        source_type = "audio"
        extractor = AudioExtractor()
    elif ext in video_exts or content_type.startswith("video/"):
        source_type = "video"
        extractor = VideoExtractor()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: PDF, TXT, Images, Audio, Video."
        )

    # 2. Read bytes and validate size (limit 25MB)
    try:
        file_bytes = await file.read()
        file_size = len(file_bytes)
    except Exception as e:
        logger.error(f"Error reading file bytes: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file."
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty (0 bytes)."
        )

    if file_size > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 25MB."
        )

    # 3. Perform Ingestion / Extraction
    import hashlib
    material_status = MaterialStatus.EXTRACTING.value
    error_message = None

    try:
        extract_result = await extractor.extract(file_bytes, content_type or f"application/{ext}")
        
        extracted_text = extract_result.get("text", "").strip()
        segments = extract_result.get("segments", [])
        metadata = extract_result.get("metadata", {})
        extraction_status = extract_result.get("extraction_status", "failed")
        ocr_status = extract_result.get("ocr_status", "n/a")
        transcription_status = extract_result.get("transcription_status", "n/a")
        extraction_method = extract_result.get("extraction_method", "direct_text")
        
        if extraction_status == "processed" and extracted_text:
            material_status = MaterialStatus.EXTRACTED.value
        else:
            material_status = MaterialStatus.FAILED.value
            error_message = extract_result.get("error_code", "Extraction produced empty text or quality check failed.")
    except Exception as e:
        logger.error(f"Unified extraction failed for {filename}: {e}")
        extracted_text = ""
        segments = []
        metadata = {}
        extraction_status = "failed"
        ocr_status = "failed"
        transcription_status = "failed"
        extraction_method = "direct_text"
        material_status = MaterialStatus.FAILED.value
        error_message = str(e)

    # 4. Save to Database with initial state
    material_model = Material(
        clerk_user_id=clerk_id,
        title=filename,
        file_name=filename,
        file_size=file_size,
        content_type=content_type or f"application/{ext}",
        raw_text=extracted_text,
        status=material_status,
        created_at=datetime.utcnow(),
        source_type=source_type,
        mime_type=content_type or f"application/{ext}",
        duration=metadata.get("duration"),
        page_count=metadata.get("page_count"),
        transcription_status=transcription_status,
        ocr_status=ocr_status,
        extraction_method=extraction_method,
        segments=segments,
        error_message=error_message
    )

    try:
        material_record = await crud.create_material(db, material_model)
        material_id_str = str(material_record["_id"])
        
        # 5. RAG Pipeline: Canonical Chunking & Embedding
        if extracted_text and material_status == MaterialStatus.EXTRACTED.value:
            try:
                await crud.update_material_status(db, material_id_str, clerk_id, MaterialStatus.CHUNKING.value)
                
                # Build canonical chunks (by segments/pages or 400-word blocks)
                raw_chunks_to_embed = []
                if segments and len(segments) > 1:
                    for s_idx, seg in enumerate(segments):
                        seg_text = seg.get("text", "").strip()
                        if not seg_text:
                            continue
                        page_num = seg.get("page")
                        start_time = seg.get("start")
                        end_time = seg.get("end")
                        c_hash = hashlib.sha256(seg_text.encode("utf-8")).hexdigest()
                        c_id = f"{material_id_str}_chunk_{s_idx}_{c_hash[:8]}"
                        raw_chunks_to_embed.append({
                            "chunk_id": c_id,
                            "material_id": material_id_str,
                            "clerk_user_id": clerk_id,
                            "sequence": s_idx,
                            "text": seg_text,
                            "page": page_num,
                            "section": f"Segment {s_idx + 1}",
                            "source_type": source_type,
                            "content_hash": c_hash,
                            "start_time": start_time,
                            "end_time": end_time,
                            "token_count": len(seg_text.split()),
                            "metadata": {}
                        })
                
                if not raw_chunks_to_embed:
                    # Slicing fallback for unsegmented text (approx 400 words)
                    words = extracted_text.split()
                    chunk_size = 400
                    word_blocks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
                    for idx, block in enumerate(word_blocks):
                        c_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()
                        c_id = f"{material_id_str}_chunk_{idx}_{c_hash[:8]}"
                        raw_chunks_to_embed.append({
                            "chunk_id": c_id,
                            "material_id": material_id_str,
                            "clerk_user_id": clerk_id,
                            "sequence": idx,
                            "text": block,
                            "page": 1,
                            "section": f"Section {idx + 1}",
                            "source_type": source_type,
                            "content_hash": c_hash,
                            "start_time": None,
                            "end_time": None,
                            "token_count": len(block.split()),
                            "metadata": {}
                        })

                if raw_chunks_to_embed:
                    await crud.update_material_status(db, material_id_str, clerk_id, MaterialStatus.EMBEDDING.value)
                    
                    texts = [c["text"] for c in raw_chunks_to_embed]
                    embeddings = await AIService.generate_embeddings(texts)
                    
                    final_chunk_records = []
                    for chunk_dict, emb in zip(raw_chunks_to_embed, embeddings):
                        chunk_dict["embedding"] = emb
                        chunk_dict["embedding_model"] = "models/gemini-embedding-001"
                        chunk_dict["embedding_status"] = "completed" if any(emb) else "fallback"
                        final_chunk_records.append(chunk_dict)
                        
                    await crud.save_material_chunks(db, material_id_str, final_chunk_records)
                    await crud.update_material_status(db, material_id_str, clerk_id, MaterialStatus.READY.value)
                    material_record["status"] = MaterialStatus.READY.value
                else:
                    await crud.update_material_status(db, material_id_str, clerk_id, MaterialStatus.PARTIAL.value)
                    material_record["status"] = MaterialStatus.PARTIAL.value
            except Exception as e:
                logger.error(f"Failed during chunking/embedding pipeline for material {material_id_str}: {e}")
                await crud.update_material_status(db, material_id_str, clerk_id, MaterialStatus.PARTIAL.value, error_message=str(e))
                material_record["status"] = MaterialStatus.PARTIAL.value
                
        # 6. Log User Activity
        await crud.log_user_activity(
            db, 
            clerk_id, 
            event_type="material_uploaded", 
            entity_type="material",
            entity_id=material_id_str,
            metadata={"filename": filename, "status": material_record.get("status")}
        )

        return material_record
    except Exception as e:
        logger.error(f"Error saving material in database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store material metadata in the database."
        )

@app.get("/api/materials")
async def get_materials_list(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        return await crud.get_materials(db, clerk_id)
    except Exception as e:
        logger.error(f"Error retrieving materials list: {e}")
@app.get("/api/materials/{material_id}")
async def get_material_detail(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        material = await crud.get_material(db, material_id, clerk_id)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study material not found."
            )
        return material
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving material {material_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve study material details."
        )

@app.patch("/api/materials/{material_id}")
async def update_material(
    material_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Rename or update study material metadata."""
    clerk_id = current_user["clerk_user_id"]
    title = body.get("title")
    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Material title cannot be empty.")
    success = await crud.update_material_title(db, material_id, clerk_id, title.strip())
    if not success:
        raise HTTPException(status_code=404, detail="Material not found or access denied.")
    return await crud.get_material(db, material_id, clerk_id)

@app.post("/api/materials/{material_id}/reprocess")
async def reprocess_material(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Re-runs chunking and vector embeddings generation for an existing material."""
    clerk_id = current_user["clerk_user_id"]
    material = await crud.get_material(db, material_id, clerk_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found.")
        
    raw_text = material.get("raw_text", "").strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Cannot reprocess material with empty text.")

    import hashlib
    try:
        await crud.update_material_status(db, material_id, clerk_id, MaterialStatus.CHUNKING.value)
        words = raw_text.split()
        chunk_size = 400
        word_blocks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
        
        raw_chunks = []
        for idx, block in enumerate(word_blocks):
            c_hash = hashlib.sha256(block.encode("utf-8")).hexdigest()
            c_id = f"{material_id}_chunk_{idx}_{c_hash[:8]}"
            raw_chunks.append({
                "chunk_id": c_id,
                "material_id": str(material_id),
                "clerk_user_id": clerk_id,
                "sequence": idx,
                "text": block,
                "page": 1,
                "section": f"Section {idx + 1}",
                "source_type": material.get("source_type", "pdf"),
                "content_hash": c_hash,
                "token_count": len(block.split()),
                "metadata": {}
            })
            
        await crud.update_material_status(db, material_id, clerk_id, MaterialStatus.EMBEDDING.value)
        embeddings = await AIService.generate_embeddings([c["text"] for c in raw_chunks])
        
        final_chunks = []
        for c, emb in zip(raw_chunks, embeddings):
            c["embedding"] = emb
            c["embedding_model"] = "models/gemini-embedding-001"
            c["embedding_status"] = "completed" if any(emb) else "fallback"
            final_chunks.append(c)
            
        # Clear previous chunks and insert new ones
        if db.is_online:
            await db.get_collection("material_chunks").delete_many({"material_id": str(material_id), "clerk_user_id": clerk_id})
        await crud.save_material_chunks(db, material_id, final_chunks)
        await crud.update_material_status(db, material_id, clerk_id, MaterialStatus.READY.value)
        
        return {
            "success": True,
            "material_id": material_id,
            "status": MaterialStatus.READY.value,
            "chunks_count": len(final_chunks)
        }
    except Exception as e:
        logger.error(f"Reprocessing failed for material {material_id}: {e}")
        await crud.update_material_status(db, material_id, clerk_id, MaterialStatus.PARTIAL.value, error_message=str(e))
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {e}")

@app.post("/api/materials/{material_id}/extract-concepts")
async def extract_concepts(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]

    # 1. Fetch and verify ownership of study material
    material = await crud.get_material(db, material_id, clerk_id)
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study material not found."
        )

    if material.get("status") in ("failed", MaterialStatus.FAILED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot extract concepts from a failed material upload."
        )

    # 2. Check if concepts are already extracted for this material
    if db.is_online:
        concepts_col = db.get_collection("concepts")
        existing_concepts = await concepts_col.find({"material_id": material_id, "clerk_user_id": clerk_id}).to_list(length=200)
        if existing_concepts:
            relationships_col = db.get_collection("relationships")
            existing_rels = await relationships_col.find({"material_id": material_id, "clerk_user_id": clerk_id}).to_list(length=200)
            logger.info(f"Returning pre-extracted concepts for material {material_id} to avoid redundant AI calls.")
            return {
                "concepts": crud.serialize_docs(existing_concepts),
                "relationships": crud.serialize_docs(existing_rels),
                "already_extracted": True
            }

    # 3. Call AI Service to extract concepts
    logger.info(f"Extracting concepts from material {material_id}...")
    try:
        raw_text = material["raw_text"]
        ai_data = await AIService.extract_concepts_and_relationships(raw_text)
        
        if ai_data.get("error") == "INSUFFICIENT_SOURCE_CONTENT":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INSUFFICIENT_SOURCE_CONTENT: The uploaded material does not contain enough educational content to extract concepts."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extract concepts via AI service: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Concept extraction failed due to AI service disruption."
        )

    # 4. Validate output with Pydantic and enrich metadata
    concepts_list = []
    relationships_list = []

    try:
        # Validate and prepare Concepts
        for c in ai_data.get("concepts", []):
            concept_model = Concept(
                clerk_user_id=clerk_id,
                material_id=material_id,
                name=c["name"],
                description=c["description"],
                exam_relevance=c["exam_relevance"],
                industry_relevance=c["industry_relevance"],
                difficulty=c["difficulty"],
                prerequisites=c.get("prerequisites", []),
                created_at=datetime.utcnow()
            )
            concepts_list.append(concept_model)

        # Validate and prepare Relationships
        for r in ai_data.get("relationships", []):
            rel_model = Relationship(
                clerk_user_id=clerk_id,
                material_id=material_id,
                source_concept_name=r["source"],
                target_concept_name=r["target"],
                relationship_type=r["relationship_type"],
                created_at=datetime.utcnow()
            )
            relationships_list.append(rel_model)

    except Exception as e:
        logger.error(f"Pydantic validation failed for AI concepts schema: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="AI service returned data that failed validation schemas."
        )

    # 5. Persist to MongoDB
    try:
        saved_concepts = await crud.create_concepts(db, concepts_list)
        saved_relationships = await crud.create_relationships(db, relationships_list)
        
        # Phase 13 Event Logging: concept_extracted
        for c in saved_concepts:
            try:
                event = LearnerEvent(
                    clerk_user_id=clerk_id,
                    event_type="concept_extracted",
                    concept_id=c["_id"],
                    metadata={"concept_name": c["name"]}
                )
                await crud.create_learner_event(db, event)
            except Exception as e:
                logger.error(f"Failed to log concept_extracted event: {e}")
                
            # Phase 14 Neo4j Synchronization
            try:
                await neo4j_service.sync_concept(clerk_id, c)
            except Exception as e:
                logger.error(f"Failed to sync concept {c['name']} to Neo4j: {e}")

        # Sync relationships to Neo4j
        for r in saved_relationships:
            try:
                await neo4j_service.sync_relationship(clerk_id, r)
            except Exception as e:
                logger.error(f"Failed to sync relationship {r.get('source_concept_name')} -> {r.get('target_concept_name')} to Neo4j: {e}")
        
        return {
            "concepts": saved_concepts,
            "relationships": saved_relationships,
            "already_extracted": False
        }
    except Exception as e:
        logger.error(f"Error persisting concepts in database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save extracted concepts in the database."
        )

@app.get("/api/concepts")
async def get_concepts_list(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        return await crud.get_concepts(db, clerk_id)
    except Exception as e:
        logger.error(f"Error retrieving concepts list: {e}")
        return []

@app.get("/api/concepts/{concept_id}")
async def get_concept_detail(
    concept_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        concept = await crud.get_concept(db, concept_id, clerk_id)
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Concept not found."
            )
        return concept
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving concept {concept_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve concept details."
        )

class ConceptCreateRequest(BaseModel):
    name: str
    description: str
    difficulty: str = "intermediate"
    exam_relevance: int = 80
    industry_relevance: int = 80
    prerequisites: List[str] = []
    material_id: Optional[str] = None

class ConceptUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    exam_relevance: Optional[int] = None
    industry_relevance: Optional[int] = None
    prerequisites: Optional[List[str]] = None

class ConceptMergeRequest(BaseModel):
    primary_concept_id: str
    duplicate_concept_id: str

@app.post("/api/concepts")
async def create_custom_concept(
    body: ConceptCreateRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new user-defined or manual educational concept."""
    clerk_id = current_user["clerk_user_id"]
    concept_model = Concept(
        clerk_user_id=clerk_id,
        material_id=body.material_id,
        name=body.name.strip(),
        description=body.description.strip(),
        difficulty=body.difficulty,
        exam_relevance=body.exam_relevance,
        industry_relevance=body.industry_relevance,
        prerequisites=body.prerequisites,
        created_at=datetime.utcnow()
    )
    saved = await crud.create_concepts(db, [concept_model])
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to create concept.")
    created_c = saved[0]
    
    # Sync with Neo4j
    try:
        await neo4j_service.sync_concept(clerk_id, created_c)
    except Exception as e:
        logger.warning(f"Neo4j sync failed for custom concept: {e}")
        
    return created_c

@app.patch("/api/concepts/{concept_id}")
async def patch_concept(
    concept_id: str,
    body: ConceptUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Edit concept details, difficulty, relevance weights, and prerequisites."""
    clerk_id = current_user["clerk_user_id"]
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update.")
        
    updated = await crud.update_concept(db, concept_id, clerk_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Concept not found or access denied.")
        
    # Sync update with Neo4j
    try:
        await neo4j_service.sync_concept(clerk_id, updated)
    except Exception as e:
        logger.warning(f"Neo4j sync failed on concept update: {e}")
        
    return updated

@app.post("/api/concepts/merge")
async def merge_duplicate_concepts(
    body: ConceptMergeRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Merge duplicate concepts into a single primary concept.
    Re-points associated questions, attempts, relationships, and mastery.
    """
    clerk_id = current_user["clerk_user_id"]
    merged = await crud.merge_concepts(db, clerk_id, body.primary_concept_id, body.duplicate_concept_id)
    if not merged:
        raise HTTPException(status_code=404, detail="Primary or duplicate concept not found.")
    return {
        "success": True,
        "primary_concept": merged,
        "message": f"Successfully merged concept into '{merged['name']}'."
    }

class GenerateAssessmentRequest(BaseModel):
    concept_id: Optional[str] = None
    num_questions: int = 5

class AssessmentSubmitRequest(BaseModel):
    attempts: List[AttemptSubmit]

@app.get("/api/graph")
async def get_graph(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        concepts = await crud.get_concepts(db, clerk_id)
        relationships = await crud.get_relationships(db, clerk_id)
        masteries = await crud.get_mastery(db, clerk_id)
    except Exception as e:
        logger.error(f"Error reading graph raw data: {e}")
        return {"nodes": [], "edges": []}

    # Map concept_id to mastery values (applying time decay)
    mastery_map = {}
    for m in masteries:
        decayed_score = get_decayed_score(m["mastery_score"], m["last_reviewed_at"])
        if decayed_score < 40.0:
            category = "Weak"
        elif decayed_score < 70.0:
            category = "Learning"
        elif decayed_score < 85.0:
            category = "Proficient"
        else:
            category = "Mastered"

        mastery_map[m["concept_id"]] = {
            "score": decayed_score,
            "category": category
        }

    nodes = []
    edges = []

    # Build adjacency and compute topological levels
    concept_by_name = {c["name"]: c for c in concepts}
    concept_level = {}

    def compute_level(name, visited=None):
        if visited is None:
            visited = set()
        if name in visited or name not in concept_by_name:
            return 0
        visited.add(name)
        prereqs = concept_by_name[name].get("prerequisites", [])
        if not prereqs:
            return 0
        return 1 + max([compute_level(p, visited.copy()) for p in prereqs], default=0)

    for c in concepts:
        concept_level[c["name"]] = compute_level(c["name"])

    # Group concepts by hierarchical level/layer
    levels_dict = {}
    for c in concepts:
        lvl = concept_level.get(c["name"], 0)
        levels_dict.setdefault(lvl, []).append(c)

    sorted_levels = sorted(levels_dict.keys())
    for col_idx, lvl in enumerate(sorted_levels):
        layer_concepts = levels_dict[lvl]
        total_in_layer = len(layer_concepts)
        for row_idx, c in enumerate(layer_concepts):
            concept_id_str = str(c["_id"])
            m_info = mastery_map.get(concept_id_str)
            
            if m_info:
                mastery_score = m_info["score"]
                mastery_state = m_info["category"]
            else:
                mastery_score = None
                mastery_state = "Not assessed"

            # Hierarchical topological positioning (left-to-right progression)
            x = col_idx * 300 + 40
            # Center nodes vertically within their column
            y = (row_idx - (total_in_layer - 1) / 2) * 160 + 260

            nodes.append({
                "id": concept_id_str,
                "type": "default",
                "position": {"x": int(x), "y": int(y)},
                "data": {
                    "label": c["name"],
                    "name": c["name"],
                    "difficulty": c.get("difficulty", "intermediate"),
                    "exam_relevance": c.get("exam_relevance", 80),
                    "industry_relevance": c.get("industry_relevance", 80),
                    "mastery_score": mastery_score,
                    "mastery_state": mastery_state,
                    "description": c.get("description", ""),
                    "prerequisites": c.get("prerequisites", []),
                    "level": lvl
                },
                "style": {
                    "background": "#0f172a",
                    "color": "#fff",
                    "border": "1.5px solid " + (
                        "#10b981" if mastery_state == "Mastered"
                        else "#6366f1" if mastery_state == "Proficient"
                        else "#f59e0b" if mastery_state == "Learning"
                        else "#ef4444" if mastery_state == "Weak"
                        else "#475569"
                    ),
                    "borderRadius": "12px",
                    "padding": "12px",
                    "fontSize": "11px",
                    "fontWeight": "700",
                    "boxShadow": "0 0 12px " + (
                        "rgba(16, 185, 129, 0.25)" if mastery_state == "Mastered"
                        else "rgba(99, 101, 241, 0.25)" if mastery_state == "Proficient"
                        else "rgba(245, 158, 11, 0.25)" if mastery_state == "Learning"
                        else "rgba(239, 68, 68, 0.25)" if mastery_state == "Weak"
                        else "rgba(71, 85, 105, 0.1)"
                    )
                }
            })

    # Map relationships to React Flow Edges
    name_to_id = {c["name"]: str(c["_id"]) for c in concepts}
    edge_pairs_seen = set()

    for r in relationships:
        source_id = name_to_id.get(r["source_concept_name"])
        target_id = name_to_id.get(r["target_concept_name"])
        
        if source_id and target_id and (source_id, target_id) not in edge_pairs_seen:
            edge_pairs_seen.add((source_id, target_id))
            edges.append({
                "id": f"e_{source_id}_{target_id}",
                "source": source_id,
                "target": target_id,
                "label": r.get("relationship_type", "prerequisite_of").replace("_", " "),
                "type": "smoothstep",
                "animated": True,
                "style": {"stroke": "#6366f1", "strokeWidth": 1.5},
                "labelStyle": {"fill": "#94a3b8", "fontSize": 8, "fontWeight": 600}
            })

    # Also synthesize edges from concept.prerequisites if not in relationships
    for c in concepts:
        target_id = str(c["_id"])
        for p_name in c.get("prerequisites", []):
            source_id = name_to_id.get(p_name)
            if source_id and target_id and (source_id, target_id) not in edge_pairs_seen:
                edge_pairs_seen.add((source_id, target_id))
                edges.append({
                    "id": f"e_{source_id}_{target_id}",
                    "source": source_id,
                    "target": target_id,
                    "label": "prerequisite of",
                    "type": "smoothstep",
                    "animated": True,
                    "style": {"stroke": "#6366f1", "strokeWidth": 1.5},
                    "labelStyle": {"fill": "#94a3b8", "fontSize": 8, "fontWeight": 600}
                })

    return {"nodes": nodes, "edges": edges}

@app.get("/api/assessment")
async def get_assessment(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        questions = await crud.get_questions(db, clerk_id)
        sanitized = []
        for sq in questions:
            sanitized.append({
                "_id": sq["_id"],
                "concept_id": sq["concept_id"],
                "concept_name": sq["concept_name"],
                "question_text": sq["question_text"],
                "options": sq["options"],
                "difficulty": sq["difficulty"]
            })
        return sanitized
    except Exception as e:
        logger.error(f"Error retrieving questions list: {e}")
        return []

@app.post("/api/assessment/generate")
async def generate_assessment(
    req: GenerateAssessmentRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]

    # Verify the user has concepts
    concepts = await crud.get_concepts(db, clerk_id)
    if not concepts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No concepts found. Please upload study materials and mine concepts before starting assessments."
        )

    # Filter targeted concepts
    target_concepts = concepts
    if req.concept_id:
        target = await crud.get_concept(db, req.concept_id, clerk_id)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected concept not found."
            )
        target_concepts = [target]

    try:
        from .services.context_service import UserContextService
        # 1. Fetch personalization context
        user_context = await UserContextService.get_full_context(db, clerk_id)
        user_profile = user_context.profile

        # 2. RAG Retrieval - fetch chunks relevant to target concepts
        context_chunks = []
        retrieved_chunk_docs = []
        # Generate search query from target concepts
        query_text = " ".join([c["name"] + ": " + c.get("description", "") for c in target_concepts])
        query_emb_list = await AIService.generate_embeddings([query_text])
        if query_emb_list:
            query_embedding = query_emb_list[0]
            # Retrieve chunks using vector search
            retrieved_chunk_docs = await crud.TEMPORARY_VECTOR_SEARCH_FALLBACK(db, clerk_id, query_embedding, top_k=5, min_similarity=0.3)
            context_chunks = [d["text"] for d in retrieved_chunk_docs if "text" in d]

        raw_questions = await AIService.generate_questions_for_concepts(
            target_concepts, 
            req.num_questions, 
            user_profile=user_profile, 
            context_chunks=context_chunks
        )
        
        # 3. Post-Generation Server-Side Source Validation
        if retrieved_chunk_docs:
            # Validate source references on any questions that included them
            validated_questions_raw = AIService.validate_source_refs(
                raw_questions, 
                retrieved_chunk_docs,
                expected_clerk_user_id=clerk_id
            )
            # If questions passed validation, use them; if not, fallback to raw questions with grounded context
            if validated_questions_raw:
                raw_questions = validated_questions_raw
            
    except Exception as e:
        logger.error(f"Error generating questions via AI Service: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed to generate assessment questions."
        )

    validated_questions = []
    for q in raw_questions:
        concept_name = q.get("concept_name", target_concepts[0]["name"])
        concept_id = q.get("concept_id", str(target_concepts[0]["_id"]))
        
        matched_concept = next((c for c in target_concepts if c["name"] == concept_name), None)
        if matched_concept:
            concept_id = str(matched_concept["_id"])
            concept_name = matched_concept["name"]

        q_model = Question(
            clerk_user_id=clerk_id,
            concept_id=concept_id,
            concept_name=concept_name,
            question_text=q["question_text"],
            options=q["options"],
            correct_option_index=q["correct_option_index"],
            difficulty=q.get("difficulty", "basic").lower(),
            explanation=q.get("explanation", "Matches curriculum mapping."),
            source_refs=q.get("source_refs", [])
        )
        validated_questions.append(q_model)

    if not validated_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INSUFFICIENT_SOURCE_CONTENT: The uploaded materials do not contain enough factual information to generate relevant questions for these concepts."
        )

    saved_questions = await crud.create_questions(db, validated_questions)

    # Sanitize questions (Remove correct index and explanation)
    sanitized = []
    for sq in saved_questions:
        sanitized.append({
            "_id": sq["_id"],
            "concept_id": sq["concept_id"],
            "concept_name": sq["concept_name"],
            "question_text": sq["question_text"],
            "options": sq["options"],
            "difficulty": sq["difficulty"]
        })

    return sanitized

@app.post("/api/assessment/submit")
async def submit_assessment(
    req: AssessmentSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    results_review = []
    correct_count = 0
    total_questions = len(req.attempts)

    # 1. Base study-path completion reward (50 XP)
    await GamificationService.award_xp(db, clerk_id, "study_path_completion", {"total_questions": total_questions})

    for att in req.attempts:
        question = await crud.get_question(db, att.question_id, clerk_id)
        if not question:
            continue

        is_correct = (att.selected_option_index == question["correct_option_index"])
        if is_correct:
            correct_count += 1
            # Award successful retrieval reward (5 XP)
            await GamificationService.award_xp(
                db, 
                clerk_id, 
                "successful_retrieval", 
                {"question_id": att.question_id, "concept_name": question["concept_name"], "confidence": att.confidence, "difficulty": question.get("difficulty", "basic")}
            )

        # Save Attempt document
        attempt_model = Attempt(
            clerk_user_id=clerk_id,
            concept_id=question["concept_id"],
            question_id=att.question_id,
            selected_option_index=att.selected_option_index,
            is_correct=is_correct,
            confidence=att.confidence,
            response_time_seconds=att.response_time_seconds,
            created_at=datetime.utcnow()
        )
        await crud.create_attempt(db, attempt_model)

        # Retrieve previous mastery details for XP transition checks
        old_mastery = await crud.get_mastery_by_concept(db, question["concept_id"], clerk_id)
        old_category = old_mastery["category"] if old_mastery else None

        # Update mastery details using the Bayesian Knowledge Tracing / baseline service
        mastery_record = await KTService.update_mastery(
            db=db,
            clerk_user_id=clerk_id,
            concept_id=question["concept_id"],
            concept_name=question["concept_name"],
            is_correct=is_correct,
            confidence=att.confidence,
            response_time=att.response_time_seconds
        )
        
        new_score = mastery_record["mastery_score"]
        category = mastery_record["category"]

        # 2. Mastery category improvement rewards (20 XP)
        if (old_category is None or old_category == "Weak") and category in ("Learning", "Proficient", "Mastered"):
            await GamificationService.award_xp(db, clerk_id, "mastery_improvement", {"concept_id": question["concept_id"], "concept_name": question["concept_name"], "new_category": category})

        # 3. Completion of difficult concepts (intermediate or advanced) (30 XP)
        if (old_category is None or old_category != "Mastered") and category == "Mastered":
            if question.get("difficulty", "basic").lower() in ("intermediate", "advanced"):
                await GamificationService.award_xp(db, clerk_id, "difficult_concept_completion", {"concept_id": question["concept_id"], "concept_name": question["concept_name"]})

        # 4. Prerequisite chain completion check (25 XP)
        concepts_list = await crud.get_concepts(db, clerk_id)
        current_concept_doc = next((c for c in concepts_list if str(c["_id"]) == question["concept_id"]), None)
        if current_concept_doc and current_concept_doc.get("prerequisites"):
            prereqs_list = current_concept_doc["prerequisites"]
            all_prereqs_mastered = True
            all_user_masteries = await crud.get_mastery(db, clerk_id)
            mastery_map = {m["concept_name"]: m for m in all_user_masteries}
            
            for pr in prereqs_list:
                m_pr = mastery_map.get(pr)
                if not m_pr or m_pr.get("category") in ("Weak", "Not assessed"):
                    all_prereqs_mastered = False
                    break
            
            if all_prereqs_mastered:
                await GamificationService.award_xp(db, clerk_id, "prerequisite_completion", {"concept_id": question["concept_id"], "concept_name": question["concept_name"]})

        results_review.append({
            "question_id": att.question_id,
            "concept_name": question["concept_name"],
            "question_text": question["question_text"],
            "options": question["options"],
            "selected_option_index": att.selected_option_index,
            "correct_option_index": question["correct_option_index"],
            "is_correct": is_correct,
            "confidence": att.confidence,
            "explanation": question["explanation"],
            "new_mastery_score": new_score,
            "mastery_state": category
        })

    # Read latest gamification profile to return to frontend
    game_profile = await crud.get_gamification(db, clerk_id)
    if not game_profile:
        game_profile = {"xp": 0, "level": 1, "level_name": "Beginner"}

    percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0.0

    return {
        "total_questions": total_questions,
        "correct_answers": correct_count,
        "percentage": round(percentage, 2),
        "review": results_review,
        "gained_xp": 0,
        "xp_events": [],
        "total_xp": game_profile.get("xp", 0),
        "level": game_profile.get("level", 1),
        "level_name": game_profile.get("level_name", "Beginner")
    }

def get_decayed_score(score: float, last_reviewed: datetime) -> float:
    """Applies exponential forgetting curve decay of 5% per day elapsed."""
    days_elapsed = (datetime.utcnow() - last_reviewed).total_seconds() / (24.0 * 3600.0)
    decay_factor = math.exp(-0.05 * days_elapsed)
    return max(0.0, min(100.0, score * decay_factor))

CURATED_RESOURCES = [
    {
        "concept_name": "Linear Regression",
        "title": "Linear Regression Complete Guide - Scikit-Learn Docs",
        "type": "documentation",
        "url": "https://scikit-learn.org/stable/modules/linear_model.html#ordinary-least-squares",
        "source": "Scikit-Learn Official",
        "trust_score": 98
    },
    {
        "concept_name": "Linear Regression",
        "title": "StatQuest: Fitting a Line with Linear Regression",
        "type": "video",
        "url": "https://www.youtube.com/watch?v=PaFPbb66DxQ",
        "source": "StatQuest by Josh Starmer",
        "trust_score": 95
    },
    {
        "concept_name": "Logistic Regression",
        "title": "Logistic Regression Overview - StatQuest Video",
        "type": "video",
        "url": "https://www.youtube.com/watch?v=yIYKR4sgzI8",
        "source": "StatQuest by Josh Starmer",
        "trust_score": 95
    },
    {
        "concept_name": "Logistic Regression",
        "title": "Understanding Logistic Regression - Towards Data Science",
        "type": "article",
        "url": "https://towardsdatascience.com/logistic-regression-detailed-overview-46c4af43035a",
        "source": "Towards Data Science",
        "trust_score": 85
    },
    {
        "concept_name": "Decision Trees",
        "title": "Decision Tree Classifier Reference Guide",
        "type": "documentation",
        "url": "https://scikit-learn.org/stable/modules/tree.html",
        "source": "Scikit-Learn Official",
        "trust_score": 98
    },
    {
        "concept_name": "Decision Trees",
        "title": "Decision Trees in Machine Learning - StatQuest Video",
        "type": "video",
        "url": "https://www.youtube.com/watch?v=7VeUPuFGJHk",
        "source": "StatQuest by Josh Starmer",
        "trust_score": 95
    },
    {
        "concept_name": "Random Forests",
        "title": "StatQuest: Random Forests Part 1 - Construction",
        "type": "video",
        "url": "https://www.youtube.com/watch?v=J4Wdy0Wc_xQ",
        "source": "StatQuest by Josh Starmer",
        "trust_score": 96
    },
    {
        "concept_name": "Random Forests",
        "title": "Ensemble Methods: Random Forests Reference",
        "type": "documentation",
        "url": "https://scikit-learn.org/stable/modules/ensemble.html#forests-of-randomized-trees",
        "source": "Scikit-Learn Official",
        "trust_score": 98
    },
    {
        "concept_name": "Neural Networks",
        "title": "3Blue1Brown: Neural Networks Deep Dive Playlist",
        "type": "video",
        "url": "https://www.youtube.com/watch?v=aircAruvnKk",
        "source": "3Blue1Brown",
        "trust_score": 99
    },
    {
        "concept_name": "Gradient Descent",
        "title": "StatQuest: Gradient Descent, Step-by-Step",
        "type": "video",
        "url": "https://www.youtube.com/watch?v=sDv4f4s2SB8",
        "source": "StatQuest by Josh Starmer",
        "trust_score": 95
    },
    {
        "concept_name": "K-Means Clustering",
        "title": "K-Means Clustering - StatQuest Step-by-Step",
        "type": "video",
        "url": "https://www.youtube.com/watch?v=4b5d3muPQmA",
        "source": "StatQuest by Josh Starmer",
        "trust_score": 94
    },
    {
        "concept_name": "Support Vector Machines",
        "title": "Support Vector Machine Classification - Scikit-Learn Docs",
        "type": "documentation",
        "url": "https://scikit-learn.org/stable/modules/svm.html",
        "source": "Scikit-Learn Official",
        "trust_score": 98
    }
]

@app.get("/api/mastery")
async def get_mastery(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        masteries = await crud.get_mastery(db, clerk_id)
        decayed = []
        for m in masteries:
            dec_score = get_decayed_score(m["mastery_score"], m["last_reviewed_at"])
            
            if dec_score < 40.0:
                category = "Weak"
            elif dec_score < 70.0:
                category = "Learning"
            elif dec_score < 85.0:
                category = "Proficient"
            else:
                category = "Mastered"

            decayed.append({
                "concept_id": m["concept_id"],
                "concept_name": m["concept_name"],
                "mastery_score": dec_score,
                "category": category,
                "last_reviewed_at": m["last_reviewed_at"],
                "next_review": m.get("next_review", m["last_reviewed_at"] + timedelta(days=1))
            })
        return decayed
    except Exception as e:
        logger.error(f"Error retrieving mastery levels: {e}")
        return []

@app.get("/api/study-path")
async def get_study_path(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        concepts = await crud.get_concepts(db, clerk_id)
        if not concepts:
            return {"ordered_concepts": []}

        masteries = await crud.get_mastery(db, clerk_id)
        mastery_map = {m["concept_id"]: m for m in masteries}

        # 1. Fetch active planner model from user profile (default to graph_aware)
        user_profile = await crud.get_user_profile(db, clerk_id)
        active_planner = "graph_aware"
        if user_profile and "active_planner_model" in user_profile:
            active_planner = user_profile["active_planner_model"]

        # 2. Instantiate and generate path using active planner
        if active_planner == "baseline":
            planner = BaselinePlanner()
        elif active_planner == "rl":
            planner = RLStudyPathPlanner()
        else:
            planner = GraphAwarePlanner()

        ordered_concepts = await planner.generate_path(db, clerk_id, concepts, mastery_map)

        # 3. Shadow Mode: calculate recommendation outcomes for alternative planners
        try:
            shadow_planner = BaselinePlanner() if active_planner != "baseline" else GraphAwarePlanner()
            shadow_path = await shadow_planner.generate_path(db, clerk_id, concepts, mastery_map)
            # Log Phase 13 Event: study_path_generated
            event = LearnerEvent(
                clerk_user_id=clerk_id,
                event_type="study_path_generated",
                metadata={
                    "active_planner": active_planner,
                    "active_top_concept": ordered_concepts[0]["concept_name"] if ordered_concepts else None,
                    "shadow_top_concept": shadow_path[0]["concept_name"] if shadow_path else None
                }
            )
            await crud.create_learner_event(db, event)
        except Exception as e:
            logger.error(f"Shadow planner execution failed: {e}")

        # 4. Save active path to DB
        now = datetime.utcnow()
        from .models import StudyPathItem, StudyPath
        ordered_items = [
            StudyPathItem(
                concept_id=p["concept_id"],
                concept_name=p["concept_name"],
                priority_score=p["priority_score"],
                reason=p["reason"]
            )
            for p in ordered_concepts
        ]
        path_model = StudyPath(
            clerk_user_id=clerk_id,
            ordered_concepts=ordered_items,
            updated_at=now
        )
        await crud.create_or_update_study_path(db, path_model)

        return {
            "ordered_concepts": ordered_concepts
        }
    except Exception as e:
        logger.error(f"Error computing study path: {e}")
        return {"ordered_concepts": []}

@app.get("/api/resources")
async def get_resources(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        masteries = await crud.get_mastery(db, clerk_id)
        
        # Identify weak concepts (score < 70.0) or not assessed
        weak_concept_names = set()
        for m in masteries:
            dec_score = get_decayed_score(m["mastery_score"], m["last_reviewed_at"])
            if dec_score < 70.0:
                weak_concept_names.add(m["concept_name"])
                
        concepts = await crud.get_concepts(db, clerk_id)
        if not concepts:
            return []

        # Find concepts not assessed yet
        assessed_names = {m["concept_name"] for m in masteries}
        for c in concepts:
            if c["name"] not in assessed_names:
                weak_concept_names.add(c["name"])

        # Filter Curated Catalogue
        recommended = []
        for r in CURATED_RESOURCES:
            if r["concept_name"] in weak_concept_names:
                recommended.append(r)

        # If no weak concepts exist (all mastered), default to all resources in catalog matching user's concepts
        if not recommended:
            user_concept_names = {c["name"] for c in concepts}
            for r in CURATED_RESOURCES:
                if r["concept_name"] in user_concept_names:
                    recommended.append(r)

        # Dynamic fallback: If concepts have no curated catalogue entries, generate verified high-trust documentation guides
        matched_concept_names = {r["concept_name"] for r in recommended}
        for c in concepts:
            c_name = c["name"]
            if c_name not in matched_concept_names:
                import urllib.parse
                encoded = urllib.parse.quote(c_name)
                # Video resource
                recommended.append({
                    "concept_name": c_name,
                    "title": f"Deep Dive Video Guide: {c_name}",
                    "type": "video",
                    "url": f"https://www.youtube.com/results?search_query={encoded}+concept+tutorial+deep+dive",
                    "source": "Educational Video Lectures",
                    "trust_score": 92
                })
                # Official Documentation / Reference
                recommended.append({
                    "concept_name": c_name,
                    "title": f"Authoritative Technical Reference: {c_name}",
                    "type": "documentation",
                    "url": f"https://devdocs.io/#q={encoded}",
                    "source": "DevDocs & Verified Docs",
                    "trust_score": 96
                })

        return recommended
    except Exception as e:
        logger.error(f"Error recommending resources: {e}")
        return []

@app.get("/api/gamification")
async def get_gamification(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        game = await crud.get_gamification(db, clerk_id)
        if game:
            return game
        
        # Default starting stats
        return {
            "clerk_user_id": clerk_id,
            "xp": 0,
            "level": 1,
            "level_name": "Beginner",
            "achievements": [],
            "updated_at": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error retrieving gamification profile: {e}")
        return {"xp": 0, "level": 1, "level_name": "Beginner", "achievements": []}

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        concepts = await crud.get_concepts(db, clerk_id)
        masteries = await crud.get_mastery(db, clerk_id)
        attempts = await db.get_collection("attempts").find({"clerk_user_id": clerk_id}).sort("created_at", -1).to_list(length=1000)
        game = await crud.get_gamification(db, clerk_id)
        
        # Calculate average decayed mastery
        decayed_scores = []
        weak_concepts = []
        for m in masteries:
            dec_score = get_decayed_score(m["mastery_score"], m["last_reviewed_at"])
            decayed_scores.append(dec_score)
            if dec_score < 40.0:
                weak_concepts.append({
                    "concept_id": m["concept_id"],
                    "concept_name": m["concept_name"],
                    "score": dec_score
                })

        # Add concepts not assessed yet to weak list
        assessed_ids = {m["concept_id"] for m in masteries}
        for c in concepts:
            c_id = str(c["_id"])
            if c_id not in assessed_ids:
                weak_concepts.append({
                    "concept_id": c_id,
                    "concept_name": c["name"],
                    "score": 0.0
                })

        avg_mastery = sum(decayed_scores) / len(decayed_scores) if decayed_scores else None

        # Calculate study streak
        streak = 0
        if attempts:
            unique_days = sorted(list({a["created_at"].date() for a in attempts}), reverse=True)
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)
            
            if unique_days[0] in (today, yesterday):
                streak = 1
                for idx in range(len(unique_days) - 1):
                    if unique_days[idx] - unique_days[idx+1] == timedelta(days=1):
                        streak += 1
                    else:
                        break

        # Calculate next review session concept
        next_session_concept = None
        if masteries:
            sorted_m = sorted(masteries, key=lambda x: x.get("next_review", datetime.utcnow()))
            next_session_concept = {
                "concept_id": sorted_m[0]["concept_id"],
                "concept_name": sorted_m[0]["concept_name"],
                "next_review": sorted_m[0].get("next_review", datetime.utcnow())
            }
        elif concepts:
            next_session_concept = {
                "concept_id": str(concepts[0]["_id"]),
                "concept_name": concepts[0]["name"],
                "next_review": datetime.utcnow()
            }

        return {
            "average_mastery": avg_mastery,
            "concepts_count": len(concepts),
            "streak_days": streak,
            "xp": game["xp"] if game else 0,
            "level": game["level"] if game else 1,
            "level_name": game["level_name"] if game else "Beginner",
            "weak_concepts": weak_concepts[:4],  # limit to top 4
            "next_session_concept": next_session_concept,
            "recent_achievements": game["achievements"][-3:] if game and game.get("achievements") else []
        }
    except Exception as e:
        logger.error(f"Error computing dashboard stats: {e}")
        return {
            "average_mastery": None,
            "concepts_count": 0,
            "streak_days": 0,
            "xp": 0,
            "level": 1,
            "level_name": "Beginner",
            "weak_concepts": [],
            "next_session_concept": None,
            "recent_achievements": []
        }

@app.post("/api/demo/load")
async def load_demo_data(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        # Check if they already have concepts to avoid seeding repeatedly
        existing = await crud.get_concepts(db, clerk_id)
        if existing:
            return {"status": "skipped", "message": "Demo data load skipped: concepts already exist."}

        # 1. Seed concepts
        demo_concepts = [
            Concept(
                clerk_user_id=clerk_id,
                material_id="6a8d63147d7ec00f92d02160",
                name="Linear Regression",
                description="A linear model predicting a quantitative target using feature parameters via ordinary least squares.",
                exam_relevance=85,
                industry_relevance=75,
                difficulty="basic",
                prerequisites=[]
            ),
            Concept(
                clerk_user_id=clerk_id,
                material_id="6a8d63147d7ec00f92d02160",
                name="Decision Trees",
                description="A non-parametric supervised learning method dividing datasets into axis-aligned partitions.",
                exam_relevance=80,
                industry_relevance=80,
                difficulty="basic",
                prerequisites=[]
            ),
            Concept(
                clerk_user_id=clerk_id,
                material_id="6a8d63147d7ec00f92d02160",
                name="Random Forests",
                description="An ensemble classifier aggregating predictions of multiple decision trees constructed via bootstrapping.",
                exam_relevance=95,
                industry_relevance=90,
                difficulty="intermediate",
                prerequisites=["Decision Trees"]
            )
        ]
        saved = await crud.create_concepts(db, demo_concepts)
        
        # 2. Seed relationships
        demo_relationships = [
            Relationship(
                clerk_user_id=clerk_id,
                material_id="6a8d63147d7ec00f92d02160",
                source_concept_name="Decision Trees",
                target_concept_name="Random Forests",
                relationship_type="prerequisite_of",
                description="Decision Trees are the base estimators for constructing Random Forests."
            )
        ]
        await crud.create_relationships(db, demo_relationships)

        # 3. Seed mastery levels
        now = datetime.utcnow()
        demo_mastery = [
            Mastery(
                clerk_user_id=clerk_id,
                concept_id=str(saved[0]["_id"]),
                concept_name="Linear Regression",
                mastery_score=92.5,
                category="Mastered",
                last_reviewed_at=now,
                next_review=now + timedelta(days=7),
                updated_at=now
            ),
            Mastery(
                clerk_user_id=clerk_id,
                concept_id=str(saved[1]["_id"]),
                concept_name="Decision Trees",
                mastery_score=75.0,
                category="Proficient",
                last_reviewed_at=now,
                next_review=now + timedelta(days=3),
                updated_at=now
            ),
            Mastery(
                clerk_user_id=clerk_id,
                concept_id=str(saved[2]["_id"]),
                concept_name="Random Forests",
                mastery_score=35.0,
                category="Weak",
                last_reviewed_at=now,
                next_review=now + timedelta(hours=12),
                updated_at=now
            )
        ]
        for m in demo_mastery:
            await crud.create_or_update_mastery(db, m)

        # 4. Seed attempts (to make streak days look nice!)
        demo_attempts = [
            Attempt(
                clerk_user_id=clerk_id,
                concept_id=str(saved[0]["_id"]),
                question_id="6a8d63147d7ec00f92d02170",
                selected_option_index=1,
                is_correct=True,
                confidence=5,
                response_time_seconds=6.2,
                created_at=now
            ),
            Attempt(
                clerk_user_id=clerk_id,
                concept_id=str(saved[2]["_id"]),
                question_id="6a8d63147d7ec00f92d02171",
                selected_option_index=0,
                is_correct=False,
                confidence=4,
                response_time_seconds=12.5,
                created_at=now - timedelta(days=1)
            )
        ]
        for a in demo_attempts:
            await crud.create_attempt(db, a)

        # 5. Seed gamification stats
        demo_game = Gamification(
            clerk_user_id=clerk_id,
            xp=180,
            level=2,
            level_name="Learner",
            achievements=["Enrolled: Machine Learning Core", "Completed Regression Assessment", "Ranked Up: Unlocked 'Learner' status!"],
            updated_at=now
        )
        await crud.create_or_update_gamification(db, demo_game)

        return {"status": "success", "message": "Demo curriculum and user attempts seeded successfully."}
    except Exception as e:
        logger.error(f"Error loading demo curriculum: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load demo dataset: {e}"
        )


# --- Phase 13: Learner Event and Behavior Data Foundation Routes ---

@app.post("/api/events")
async def log_learner_event(
    event: LearnerEvent,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    if event.clerk_user_id != clerk_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit events for your own profile."
        )
    try:
        res = await crud.create_learner_event(db, event)
        return res
    except Exception as e:
        logger.error(f"Error logging learner event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record learner event."
        )

@app.get("/api/events/analytics")
async def get_learner_events_analytics(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        analytics = await crud.get_learner_analytics(db, clerk_id)
        return analytics
    except Exception as e:
        logger.error(f"Error computing learner analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to aggregate learner metrics."
        )


# --- Phase 14: Neo4j Graph Intelligence Layer Routes ---

@app.get("/api/graph/path")
async def get_shortest_prerequisite_path(
    source: str,
    target: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        path = await neo4j_service.shortest_prerequisite_path(clerk_id, source, target)
        return {"path": path}
    except Exception as e:
        logger.error(f"Error computing shortest prerequisite path: {e}")
        return {"path": []}

@app.get("/api/graph/neighborhood")
async def get_concept_neighborhood(
    concept_name: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        neighbors = await neo4j_service.get_neighborhood(clerk_id, concept_name)
        return {"neighborhood": neighbors}
    except Exception as e:
        logger.error(f"Error computing concept neighborhood: {e}")
        return {"neighborhood": []}

@app.get("/api/graph/centrality")
async def get_concepts_centrality(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        centrality = await neo4j_service.concept_centrality(clerk_id)
        return centrality
    except Exception as e:
        logger.error(f"Error computing concepts centrality: {e}")
        return []

@app.get("/api/graph/prerequisites")
async def get_concept_prerequisites(
    concept_name: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        prereqs = await neo4j_service.get_prerequisites(clerk_id, concept_name)
        return {"prerequisites": prereqs}
    except Exception as e:
        logger.error(f"Error retrieving prerequisites: {e}")
        return {"prerequisites": []}


# --- Phase 15: Bayesian Knowledge Tracing (BKT) Routes ---

@app.get("/api/kt/evaluate")
async def evaluate_knowledge_tracing(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        evaluation = await KTService.evaluate_models(db, clerk_id)
        return evaluation
    except Exception as e:
        logger.error(f"Error evaluating knowledge tracing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run model evaluation."
        )

class PromoteModelRequest(BaseModel):
    model_name: str  # baseline or knowledge_tracing

@app.post("/api/kt/promote")
async def promote_knowledge_tracing_model(
    req: PromoteModelRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        res = await KTService.promote_model(db, clerk_id, req.model_name)
        return res
    except Exception as e:
        logger.error(f"Error promoting model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# --- Phase 16: Adaptive Quiz Policy Routes ---

@app.get("/api/assessment/adaptive")
async def get_adaptive_question(
    exclude_ids: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    exclude_list = []
    if exclude_ids:
        exclude_list = [i.strip() for i in exclude_ids.split(",") if i.strip()]
        
    try:
        question = await AdaptivePolicy.get_next_question(db, clerk_id, exclude_list)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No adaptive questions available. Please upload and extract concepts first."
            )
        
        # Sanitize correct answer and explanation for learner presentation
        return {
            "_id": question["_id"],
            "concept_id": question["concept_id"],
            "concept_name": question["concept_name"],
            "question_text": question["question_text"],
            "options": question["options"],
            "difficulty": question.get("difficulty", "basic")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating adaptive question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query adaptive quiz database."
        )


# --- Phase 17 & 18: Study Path Planner Evaluation & Promotion Routes ---

@app.get("/api/planner/evaluate")
async def evaluate_study_planners(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        concepts = await crud.get_concepts(db, clerk_id)
        if not concepts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 1 extracted concept is required for planner evaluation."
            )
        
        evaluation = await run_simulation_comparison(concepts)
        return evaluation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error evaluating study planners in simulation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run study planner simulations."
        )

class PromotePlannerRequest(BaseModel):
    planner_name: str  # baseline, graph_aware, or rl

@app.post("/api/planner/promote")
async def promote_study_planner(
    req: PromotePlannerRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    if req.planner_name not in ("baseline", "graph_aware", "rl"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Planner name must be 'baseline', 'graph_aware', or 'rl'"
        )
    try:
        if db.is_online:
            col = db.get_collection("user_profiles")
            await col.update_one(
                {"clerk_user_id": clerk_id},
                {"$set": {"active_planner_model": req.planner_name}},
                upsert=True
            )
        else:
            # Update local profile dictionary or mock settings
            from .crud import _DEMO_DB
            if "user_profiles" not in _DEMO_DB:
                _DEMO_DB["user_profiles"] = []
            
            profile = next((p for p in _DEMO_DB["user_profiles"] if p.get("clerk_user_id") == clerk_id), None)
            if profile:
                profile["active_planner_model"] = req.planner_name
            else:
                _DEMO_DB["user_profiles"].append({
                    "clerk_user_id": clerk_id,
                    "active_planner_model": req.planner_name
                })
        
        return {
            "status": "success",
            "active_planner_model": req.planner_name,
            "message": f"Successfully promoted study planner: {req.planner_name}"
        }
    except Exception as e:
        logger.error(f"Error promoting study planner: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update active study planner configuration."
        )


# --- Phase 19: Trust-Aware Resource Recommendation Routes ---

class ResourceFeedbackRequest(BaseModel):
    rating: Optional[int] = None
    helpful: Optional[bool] = None

@app.post("/api/resources/{id}/feedback")
async def submit_resource_feedback(
    id: str,
    req: ResourceFeedbackRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        feedback = ResourceFeedback(
            clerk_user_id=clerk_id,
            resource_id=id,
            rating=req.rating,
            helpful=req.helpful,
            completed=False
        )
        saved = await crud.create_or_update_resource_feedback(db, feedback)
        
        # Award usefulness reward (10 XP)
        if req.helpful is not None or req.rating is not None:
            await GamificationService.award_xp(
                db, 
                clerk_id, 
                "resource_usefulness", 
                {"resource_id": id}
            )
            
        return saved
    except Exception as e:
        logger.error(f"Error submitting resource feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit resource feedback."
        )

@app.post("/api/resources/{id}/complete")
async def complete_resource(
    id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        # Log event of type resource_completed
        event = LearnerEvent(
            clerk_user_id=clerk_id,
            event_type="resource_completed",
            resource_id=id
        )
        await crud.create_learner_event(db, event)
        
        # Fetch current feedback to upsert completion
        feedback = ResourceFeedback(
            clerk_user_id=clerk_id,
            resource_id=id,
            completed=True
        )
        saved = await crud.create_or_update_resource_feedback(db, feedback)
        return saved
    except Exception as e:
        logger.error(f"Error completing resource: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record resource completion."
        )

@app.post("/api/resources/{id}/click")
async def track_resource_click(
    id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        event = LearnerEvent(
            clerk_user_id=clerk_id,
            event_type="resource_viewed",
            resource_id=id
        )
        await crud.create_learner_event(db, event)
        return {"status": "success", "message": "Resource click logged successfully."}
    except Exception as e:
        logger.error(f"Error tracking resource click: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to log resource click-through."
        )

@app.get("/api/resources/recommend")
async def get_recommended_resources(
    concept_name: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        # Fetch concept details
        concepts_list = await crud.get_concepts(db, clerk_id)
        concept = next((c for c in concepts_list if c["name"] == concept_name), None)
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept '{concept_name}' not found."
            )

        # Get learner's current concept mastery
        mastery_record = await crud.get_mastery_by_concept(db, str(concept["_id"]), clerk_id)
        mastery_score = mastery_record.get("mastery_score", 50.0) if mastery_record else 50.0

        # Fetch global catalog resources
        all_resources = await crud.get_resources(db)
        concept_resources = [r for r in all_resources if r.get("concept_name") == concept_name]

        # Get active recommendation model from user profile
        user_profile = await crud.get_user_profile(db, clerk_id)
        active_recommender = "trust_aware"
        if user_profile and "active_recommender_model" in user_profile:
            active_recommender = user_profile["active_recommender_model"]

        # Run selected ranker
        if active_recommender == "baseline":
            ranker = BaselineResourceRanker()
        else:
            ranker = TrustAwareResourceRanker()

        recommended = await ranker.rank_resources(db, clerk_id, concept_resources, mastery_score)

        # Shadow Mode: run alternate ranker
        try:
            shadow_ranker = BaselineResourceRanker() if active_recommender != "baseline" else TrustAwareResourceRanker()
            shadow_recommended = await shadow_ranker.rank_resources(db, clerk_id, concept_resources, mastery_score)
            
            # Log event with top alternative recommendation
            event = LearnerEvent(
                clerk_user_id=clerk_id,
                event_type="resource_recommendation_generated",
                metadata={
                    "active_recommender": active_recommender,
                    "top_active_resource": recommended[0]["title"] if recommended else None,
                    "top_shadow_resource": shadow_recommended[0]["title"] if shadow_recommended else None
                }
            )
            await crud.create_learner_event(db, event)
        except Exception as e:
            logger.error(f"Shadow recommender execution failed: {e}")

        return recommended
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving recommended resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query recommended study guides."
        )

@app.get("/api/resources/recommend/evaluate")
async def evaluate_resource_recommendation_models(
    concept_name: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        evaluation = await run_recommender_evaluation(db, clerk_id, concept_name)
        return evaluation
    except Exception as e:
        logger.error(f"Error evaluating recommender: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run model evaluation."
        )

class PromoteRecommenderRequest(BaseModel):
    recommender_name: str  # baseline or trust_aware

@app.post("/api/resources/recommend/promote")
async def promote_resource_recommender(
    req: PromoteRecommenderRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    if req.recommender_name not in ("baseline", "trust_aware"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recommender name must be 'baseline' or 'trust_aware'"
        )
    try:
        if db.is_online:
            col = db.get_collection("user_profiles")
            await col.update_one(
                {"clerk_user_id": clerk_id},
                {"$set": {"active_recommender_model": req.recommender_name}},
                upsert=True
            )
        else:
            from .crud import _DEMO_DB
            if "user_profiles" not in _DEMO_DB:
                _DEMO_DB["user_profiles"] = []
            
            profile = next((p for p in _DEMO_DB["user_profiles"] if p.get("clerk_user_id") == clerk_id), None)
            if profile:
                profile["active_recommender_model"] = req.recommender_name
            else:
                _DEMO_DB["user_profiles"].append({
                    "clerk_user_id": clerk_id,
                    "active_recommender_model": req.recommender_name
                })
        
        return {
            "status": "success",
            "active_recommender_model": req.recommender_name,
            "message": f"Successfully promoted resource recommender: {req.recommender_name}"
        }
    except Exception as e:
        logger.error(f"Error promoting resource recommender: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update active resource recommender configuration."
        )


# --- Phase 20: Gamification Audit Routes ---

@app.get("/api/gamification/audit")
async def audit_gamification_consistency(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    clerk_id = current_user["clerk_user_id"]
    try:
        audit_result = await GamificationService.audit_user_xp(db, clerk_id)
        return audit_result
    except Exception as e:
        logger.error(f"Error auditing gamification profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run player XP consistency audit."
        )

# ─── Phase Final: User Preferences / Extended Profile ──────────────────────────

@app.get("/api/user/preferences")
async def get_user_preferences(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get the authenticated user's extended learning preferences."""
    clerk_id = current_user["clerk_user_id"]
    prefs = await crud.get_user_preferences(db, clerk_id)
    if not prefs:
        return {"clerk_user_id": clerk_id}
    return prefs


@app.put("/api/user/preferences")
async def update_user_preferences(
    body: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Upsert the authenticated user's extended learning preferences."""
    clerk_id = current_user["clerk_user_id"]
    body["clerk_user_id"] = clerk_id  # Always derive from authenticated session
    try:
        prefs_model = UserPreferences(**body)
        result = await crud.upsert_user_preferences(db, prefs_model)
        return result
    except Exception as e:
        logger.error(f"Error upserting user preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Phase Final: Material Delete (Cascade) ────────────────────────────────────

@app.delete("/api/materials/{material_id}")
async def delete_material(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Delete a material owned by the authenticated user.
    Cascade-deletes concepts, questions, attempts, mastery, and graph relationships.
    """
    clerk_id = current_user["clerk_user_id"]
    success = await crud.delete_material(db, material_id, clerk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Material not found or access denied.")
    return {"deleted": True, "material_id": material_id}


# ─── Phase Final: Concept Delete (Cascade) ─────────────────────────────────────

@app.delete("/api/concepts/all")
async def delete_all_concepts(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete all concepts for the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    res = await crud.clear_user_data(db, clerk_id, "concepts")
    return {"success": True, "message": "All concepts deleted.", **res}


@app.delete("/api/concepts/{concept_id}")
async def delete_concept(
    concept_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Delete a single concept owned by the authenticated user.
    Cascade-deletes associated questions, attempts, and mastery records.
    """
    clerk_id = current_user["clerk_user_id"]
    if concept_id == "all":
        res = await crud.clear_user_data(db, clerk_id, "concepts")
        return {"success": True, "message": "All concepts deleted.", **res}
    success = await crud.delete_concept(db, concept_id, clerk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Concept not found or access denied.")
    return {"deleted": True, "concept_id": concept_id}


# ─── Phase Final: Global Search ────────────────────────────────────────────────

@app.get("/api/search")
async def global_search(
    q: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Global search across the authenticated user's materials, concepts, questions, and assignments.
    Returns categorized results.
    """
    clerk_id = current_user["clerk_user_id"]
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters.")
    results = await crud.search_user_data(db, clerk_id, q.strip())
    total = sum(len(v) for v in results.values())
    return {"query": q, "total": total, "results": results}


# ─── Phase Final: Data Clearing ─────────────────────────────────────────────────

class DataClearRequest(BaseModel):
    category: str  # assessments, gamification, materials, concepts, study_paths, resources, all


@app.post("/api/data/clear")
async def clear_user_data(
    body: DataClearRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Clear a specific category of the authenticated user's data.
    This does NOT delete the Clerk account — only application-level data.
    """
    clerk_id = current_user["clerk_user_id"]
    valid_categories = {
        "assessments", "gamification", "materials", "concepts", 
        "flashcards", "study_notes", "podcasts", "tutor", "assignments", 
        "study_paths", "resources", "all"
    }
    if body.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
    result = await crud.clear_user_data(db, clerk_id, body.category)
    return {"success": True, "category": body.category, **result}


# ─── Phase Final: Assignments CRUD ─────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    title: str
    description: str = ""
    concept_ids: List[str] = []
    concept_names: List[str] = []
    source_material_ids: List[str] = []
    difficulty: str = "intermediate"
    estimated_duration_minutes: int = 20
    due_date: Optional[str] = None
    assignment_type: str = "practice"
    questions: List[dict] = []


class AssignmentSubmitRequest(BaseModel):
    answers: List[dict]  # [{question_index: int, selected_option_index: int, confidence: int, response_time_seconds: float}]
    time_spent_seconds: float = 0.0


class AssignmentSaveProgressRequest(BaseModel):
    draft_answers: dict  # {str(question_index): selected_option_index}


@app.get("/api/assignments")
async def list_assignments(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List all assignments belonging to the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    assignments = await crud.get_assignments(db, clerk_id)
    # Update overdue statuses
    now = datetime.utcnow()
    for a in assignments:
        if a.get("status") == "pending" and a.get("due_date"):
            due = a["due_date"]
            if isinstance(due, str):
                try:
                    from dateutil.parser import parse
                    due = parse(due)
                except Exception:
                    due = None
            if due and due < now:
                a["status"] = "overdue"
    return {"assignments": assignments, "total": len(assignments)}


@app.post("/api/assignments")
async def create_assignment(
    body: AssignmentCreate,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new assignment for the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    
    # Auto-generate questions via AI if none provided and concept_names/ids are given
    questions = body.questions
    if not questions and (body.concept_names or body.concept_ids):
        try:
            # Get concepts from DB or build minimal descriptors
            all_user_concepts = await crud.get_concepts(db, clerk_id)
            concept_data = []
            if body.concept_ids:
                id_set = set(body.concept_ids)
                concept_data = [c for c in all_user_concepts if str(c["_id"]) in id_set or c.get("name") in id_set]
            if not concept_data and body.concept_names:
                name_set = set(body.concept_names)
                concept_data = [c for c in all_user_concepts if c.get("name") in name_set]
            if not concept_data:
                concept_data = all_user_concepts[:3]

            if concept_data:
                generated = await AIService.generate_questions_for_concepts(
                    concepts=concept_data,
                    num_questions=min(5, max(3, len(concept_data) * 2)),
                    user_profile={"preferred_difficulty": body.difficulty}
                )
                questions = [
                    {
                        "question_text": q.get("question_text", "Conceptual Question"),
                        "options": q.get("options", ["A", "B", "C", "D"]),
                        "correct_option_index": q.get("correct_option_index", 0),
                        "question_type": "mcq",
                        "concept_name": q.get("concept_name", concept_data[0]["name"]),
                        "difficulty": body.difficulty,
                        "explanation": q.get("explanation", "Matches curriculum standard.")
                    }
                    for q in generated
                ]
        except Exception as e:
            logger.warning(f"AI question generation failed for assignment: {e}")
            questions = []

    # If still no questions generated, create standard conceptual review questions
    if not questions and body.concept_names:
        for idx, c_name in enumerate(body.concept_names[:4]):
            questions.append({
                "question_text": f"What is the primary architectural principle and objective of {c_name}?",
                "options": [
                    f"It provides structured, robust modeling and encapsulation for {c_name}.",
                    f"It completely disables all error-handling in {c_name}.",
                    f"It forces linear execution without memory allocation.",
                    f"It is an obsolete legacy construct."
                ],
                "correct_option_index": 0,
                "question_type": "mcq",
                "concept_name": c_name,
                "difficulty": body.difficulty,
                "explanation": f"Foundational understanding of {c_name} in the curriculum."
            })

    due_date = None
    if body.due_date:
        try:
            from dateutil.parser import parse
            due_date = parse(body.due_date)
        except Exception:
            due_date = None

    assignment_model = Assignment(
        clerk_user_id=clerk_id,
        title=body.title,
        description=body.description,
        concept_ids=body.concept_ids,
        concept_names=body.concept_names,
        source_material_ids=body.source_material_ids,
        questions=[AssignmentQuestion(**q) for q in questions],
        difficulty=body.difficulty,
        estimated_duration_minutes=body.estimated_duration_minutes,
        due_date=due_date,
        status="pending",
        assignment_type=body.assignment_type,
    )
    result = await crud.create_assignment(db, assignment_model)
    return result


@app.get("/api/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get a single assignment by ID, verified against the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    assignment = await crud.get_assignment(db, assignment_id, clerk_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return assignment


@app.put("/api/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update assignment metadata (title, description, due_date, etc.)."""
    clerk_id = current_user["clerk_user_id"]
    # Prevent clerk_user_id spoofing
    body.pop("clerk_user_id", None)
    result = await crud.update_assignment(db, assignment_id, clerk_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return result


@app.delete("/api/assignments/all")
async def delete_all_assignments(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete all assignments owned by the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    res = await crud.clear_user_data(db, clerk_id, "assignments")
    return {"success": True, "message": "All assignments deleted.", **res}


@app.delete("/api/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete an assignment owned by the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    if assignment_id == "all":
        res = await crud.clear_user_data(db, clerk_id, "assignments")
        return {"success": True, "message": "All assignments deleted.", **res}
    success = await crud.delete_assignment(db, assignment_id, clerk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return {"deleted": True, "assignment_id": assignment_id}


@app.post("/api/assignments/{assignment_id}/save-progress")
async def save_assignment_progress(
    assignment_id: str,
    body: AssignmentSaveProgressRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Save draft answers for an in-progress assignment without submitting."""
    clerk_id = current_user["clerk_user_id"]
    updates = {
        "draft_answers": body.draft_answers,
        "status": "in_progress"
    }
    result = await crud.update_assignment(db, assignment_id, clerk_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return {"saved": True, "draft_answers": body.draft_answers}


@app.post("/api/assignments/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: str,
    body: AssignmentSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Submit an assignment. Scores answers, updates mastery, and awards XP.
    """
    clerk_id = current_user["clerk_user_id"]
    assignment = await crud.get_assignment(db, assignment_id, clerk_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    
    questions = assignment.get("questions", [])
    answers = body.answers
    correct_count = 0
    total_questions = len(questions)
    per_question_results = []

    for answer in answers:
        idx = answer.get("question_index", -1)
        if idx < 0 or idx >= total_questions:
            continue
        q = questions[idx]
        correct_idx = q.get("correct_option_index")
        selected_idx = answer.get("selected_option_index", -1)
        is_correct = (selected_idx == correct_idx)
        if is_correct:
            correct_count += 1
        per_question_results.append({
            "question_index": idx,
            "is_correct": is_correct,
            "correct_option_index": correct_idx,
            "selected_option_index": selected_idx,
            "explanation": q.get("explanation", "")
        })

    accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0
    score = accuracy

    # Award XP
    xp_earned = 0
    try:
        xp_earned = await GamificationService.award_xp(
            db, clerk_id, "assessment_completed",
            {"score": score, "questions_answered": total_questions}
        )
    except Exception as e:
        logger.warning(f"XP award failed for assignment submit: {e}")

    # Update assignment as completed
    updates = {
        "status": "completed",
        "score": score,
        "accuracy": accuracy,
        "time_spent_seconds": body.time_spent_seconds,
        "submitted_at": datetime.utcnow(),
        "draft_answers": {}
    }
    await crud.update_assignment(db, assignment_id, clerk_id, updates)

    return {
        "submitted": True,
        "score": round(score, 1),
        "accuracy": round(accuracy, 1),
        "correct": correct_count,
        "total": total_questions,
        "xp_earned": xp_earned,
        "per_question_results": per_question_results
    }


# ─── Spaced Repetition Flashcards & Active Recall API ──────────────────────────

@app.get("/api/flashcards")
async def get_flashcards(
    concept_id: Optional[str] = None,
    material_id: Optional[str] = None,
    state: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve all flashcards for the current user with optional filters."""
    clerk_id = current_user["clerk_user_id"]
    try:
        cards = await crud.get_flashcards(db, clerk_id, concept_id=concept_id, material_id=material_id, state=state)
        return cards
    except Exception as e:
        logger.error(f"Error fetching flashcards for user {clerk_id}: {e}")
        return []

@app.get("/api/flashcards/due")
async def get_due_flashcards(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve flashcards due for spaced-repetition review today."""
    clerk_id = current_user["clerk_user_id"]
    try:
        due_cards = await crud.get_due_flashcards(db, clerk_id, limit=limit)
        return due_cards
    except Exception as e:
        logger.error(f"Error fetching due flashcards: {e}")
        return []

@app.post("/api/flashcards/generate")
async def generate_flashcards(
    req: GenerateFlashcardsRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Generate high-yield active-recall flashcards using grounded AI."""
    clerk_id = current_user["clerk_user_id"]
    
    # 1. Resolve Target Concepts
    all_concepts = await crud.get_concepts(db, clerk_id)
    if not all_concepts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No concepts found. Please upload materials and extract concepts first."
        )
        
    target_concepts = all_concepts
    if req.concept_ids:
        id_set = set(req.concept_ids)
        target_concepts = [c for c in all_concepts if str(c["_id"]) in id_set or c.get("name") in id_set]
    elif req.material_id:
        target_concepts = [c for c in all_concepts if str(c.get("material_id")) == req.material_id]
        
    if not target_concepts:
        target_concepts = all_concepts[:5] # Default to first 5 concepts

    # 2. Retrieve relevant context chunks if material provided
    context_chunks = []
    if req.material_id:
        chunks = await crud.get_material_chunks(db, req.material_id)
        context_chunks = [c.get("text", "") for c in chunks if c.get("text")]
        
    # 3. Call AI Service
    try:
        generated_raw = await AIService.generate_flashcards(
            concepts=target_concepts,
            cards_per_concept=req.cards_per_concept,
            context_chunks=context_chunks
        )
    except Exception as e:
        logger.error(f"Error generating flashcards with AI: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed to generate flashcards."
        )

    # 4. Map and Validate Flashcard Models
    name_to_concept = {c["name"]: c for c in target_concepts}
    default_concept = target_concepts[0]
    
    flashcard_models: List[Flashcard] = []
    for g in generated_raw:
        matched = name_to_concept.get(g.get("concept_name"), default_concept)
        concept_id = str(matched["_id"])
        concept_name = matched["name"]
        material_id = str(matched.get("material_id")) if matched.get("material_id") else req.material_id
        
        card = Flashcard(
            clerk_user_id=clerk_id,
            concept_id=concept_id,
            concept_name=concept_name,
            material_id=material_id,
            front=g.get("front", f"Explain {concept_name}"),
            back=g.get("back", matched.get("description", "")),
            card_type=g.get("card_type", "standard"),
            difficulty=g.get("difficulty", matched.get("difficulty", "basic")),
            repetitions=0,
            interval_days=1.0,
            ease_factor=2.5,
            next_review_at=datetime.utcnow(),
            state="new"
        )
        flashcard_models.append(card)

    if not flashcard_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No flashcards could be generated from the selected concepts."
        )

    saved_cards = await crud.create_flashcards(db, flashcard_models)
    
    # Log user activity
    await crud.log_user_activity(
        db, clerk_id,
        event_type="flashcards_generated",
        entity_type="flashcard_deck",
        metadata={"count": len(saved_cards), "concepts": [c["name"] for c in target_concepts]}
    )
    
    return {
        "success": True,
        "count": len(saved_cards),
        "flashcards": saved_cards
    }

@app.post("/api/flashcards/review")
async def review_flashcard(
    req: FlashcardReviewRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Review a flashcard using the SuperMemo-2 (SM-2) spaced repetition algorithm.
    Rating scale:
      1: Again (Complete blackout / Fail)
      2: Hard (Recall with heavy hesitation)
      3: Good (Accurate recall with reasonable effort)
      4: Easy (Flawless, instantaneous recall)
    """
    clerk_id = current_user["clerk_user_id"]
    card = await crud.get_flashcard(db, req.card_id, clerk_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard not found."
        )

    # Current SM-2 Parameters
    repetitions = card.get("repetitions", 0)
    interval = card.get("interval_days", 1.0)
    ease_factor = card.get("ease_factor", 2.5)
    total_reviews = card.get("total_reviews", 0) + 1
    lapses = card.get("lapses", 0)
    rating = req.rating  # 1, 2, 3, 4

    # Calculate SM-2 Step
    # Quality scale (q from 0 to 5, mapped from 1-4 rating: 1->0, 2->3, 3->4, 4->5)
    quality_map = {1: 0, 2: 3, 3: 4, 4: 5}
    q = quality_map.get(rating, 3)

    if q < 3:
        # Failed recall (Again)
        repetitions = 0
        interval = 1.0
        lapses += 1
        state = "learning"
        is_correct = False
    else:
        # Successful recall (Hard, Good, Easy)
        if repetitions == 0:
            interval = 1.0
        elif repetitions == 1:
            interval = 6.0 if rating >= 3 else 3.0
        else:
            multiplier = ease_factor * (1.3 if rating == 4 else 1.0 if rating == 3 else 0.8)
            interval = max(1.0, interval * multiplier)
            
        repetitions += 1
        state = "mastered" if (repetitions >= 4 and ease_factor >= 2.3) else "review"
        is_correct = True

    # Update Ease Factor: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ease_factor = ease_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ease_factor = max(1.3, round(ease_factor, 3)) # Minimum threshold is 1.3

    now = datetime.utcnow()
    next_review = now + timedelta(days=interval)

    updates = {
        "repetitions": repetitions,
        "interval_days": round(interval, 2),
        "ease_factor": ease_factor,
        "last_reviewed_at": now,
        "next_review_at": next_review,
        "state": state,
        "total_reviews": total_reviews,
        "lapses": lapses
    }

    await crud.update_flashcard(db, req.card_id, clerk_id, updates)

    # Gamification XP: +5 XP for successful recall, +10 XP for Easy, +15 XP for card mastery
    xp_awarded = 0
    try:
        if is_correct:
            xp_awarded = await GamificationService.award_xp(
                db, clerk_id, "flashcard_reviewed",
                {"card_id": req.card_id, "rating": rating, "concept_name": card.get("concept_name")}
            )
    except Exception as e:
        logger.warning(f"XP award for flashcard review failed: {e}")

    # Synchronize with Bayesian Knowledge Tracing (KTService)
    try:
        await KTService.update_mastery(
            db=db,
            clerk_user_id=clerk_id,
            concept_id=card["concept_id"],
            concept_name=card["concept_name"],
            is_correct=is_correct,
            confidence=max(1, min(5, rating + 1)),
            response_time=req.response_time_seconds or 5.0
        )
    except Exception as e:
        logger.warning(f"BKT sync failed for flashcard: {e}")

    return {
        "success": True,
        "card_id": req.card_id,
        "is_correct": is_correct,
        "repetitions": repetitions,
        "interval_days": round(interval, 2),
        "ease_factor": ease_factor,
        "next_review_at": next_review,
        "state": state,
        "xp_earned": xp_awarded
    }

@app.delete("/api/flashcards/all")
async def delete_all_flashcards(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete all flashcards for the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    res = await crud.clear_user_data(db, clerk_id, "flashcards")
    return {"success": True, "message": "All flashcards deleted.", **res}

@app.delete("/api/flashcards/{card_id}")
async def delete_flashcard(
    card_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete an individual flashcard."""
    clerk_id = current_user["clerk_user_id"]
    if card_id == "all":
        res = await crud.clear_user_data(db, clerk_id, "flashcards")
        return {"success": True, "message": "All flashcards deleted.", **res}
    deleted = await crud.delete_flashcard(db, card_id, clerk_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard not found or not owned by user."
        )
    return {"success": True, "deleted_id": card_id}


# ─── Export Studio & Comprehensive Report API ─────────────────────────────────

@app.get("/api/export/curriculum-report")
async def get_curriculum_export_report(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Compile a complete structured curriculum audit, concept hierarchy cheat-sheet,
    mastery analytics, and knowledge graph dataset ready for export or client-side print/PDF.
    """
    clerk_id = current_user["clerk_user_id"]
    
    # 1. Fetch user records
    user_profile = await crud.get_user_profile(db, clerk_id) or {}
    concepts = await crud.get_concepts(db, clerk_id)
    relationships = await crud.get_relationships(db, clerk_id)
    mastery_records = await crud.get_mastery(db, clerk_id)
    materials = await crud.get_materials(db, clerk_id)
    flashcards = await crud.get_flashcards(db, clerk_id)
    gamification = await crud.get_gamification(db, clerk_id) or {}

    # 2. Compute Analytics
    mastery_map = {m["concept_id"]: m for m in mastery_records}
    name_to_id = {c["name"]: str(c["_id"]) for c in concepts}
    
    enriched_concepts = []
    category_counts = {"weak": 0, "learning": 0, "proficient": 0, "mastered": 0, "unassessed": 0}
    
    for c in concepts:
        cid = str(c["_id"])
        m_data = mastery_map.get(cid, {})
        score = m_data.get("mastery_score")
        category = m_data.get("category", "unassessed")
        category_counts[category] = category_counts.get(category, 0) + 1
        
        # Ingoing/Outgoing edges
        prereqs = [r["source_concept_name"] for r in relationships if r.get("target_concept_name") == c["name"]]
        dependents = [r["target_concept_name"] for r in relationships if r.get("source_concept_name") == c["name"]]
        
        enriched_concepts.append({
            "id": cid,
            "name": c["name"],
            "description": c.get("description", ""),
            "difficulty": c.get("difficulty", "basic"),
            "exam_relevance": c.get("exam_relevance", 80),
            "industry_relevance": c.get("industry_relevance", 80),
            "mastery_score": round(score, 1) if score is not None else None,
            "mastery_category": category,
            "prerequisites": prereqs or c.get("prerequisites", []),
            "dependents": dependents,
            "decayed_mastery": round(m_data.get("decayed_mastery", score), 1) if score is not None else None,
            "last_assessed_at": m_data.get("last_assessed_at")
        })

    # Overall Metrics
    assessed_scores = [c["mastery_score"] for c in enriched_concepts if c["mastery_score"] is not None]
    avg_mastery = sum(assessed_scores) / len(assessed_scores) if assessed_scores else 0.0

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "learner": {
            "display_name": user_profile.get("display_name", "MK-Path Learner"),
            "email": user_profile.get("email", ""),
            "xp": gamification.get("xp", 0),
            "level": gamification.get("level", 1),
            "level_name": gamification.get("level_name", "Beginner"),
            "achievements_count": len(gamification.get("achievements", []))
        },
        "summary": {
            "total_concepts": len(concepts),
            "total_relationships": len(relationships),
            "total_materials": len(materials),
            "total_flashcards": len(flashcards),
            "average_mastery": round(avg_mastery, 1),
            "category_distribution": category_counts
        },
        "concepts": enriched_concepts,
        "relationships": [
            {
                "source": r["source_concept_name"],
                "target": r["target_concept_name"],
                "type": r.get("relationship_type", "prerequisite_of"),
                "origin": r.get("relationship_origin", "explicit")
            }
            for r in relationships
        ],
        "materials": [
            {
                "title": m["title"],
                "file_name": m["file_name"],
                "content_type": m.get("content_type", "application/pdf"),
                "created_at": m.get("created_at")
            }
            for m in materials
        ]
    }


# ─── Study Notes & Hierarchical Mind-Map API ──────────────────────────────────

@app.get("/api/study-notes")
async def get_study_notes(
    concept_id: Optional[str] = None,
    material_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve all synthesized study notes and visual mind-maps for the learner."""
    clerk_id = current_user["clerk_user_id"]
    try:
        notes = await crud.get_study_notes(db, clerk_id, concept_id, material_id)
        return notes
    except Exception as e:
        logger.error(f"Error fetching study notes: {e}")
        return []

@app.get("/api/study-notes/{note_id}")
async def get_study_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve a single study note and mind-map by ID."""
    clerk_id = current_user["clerk_user_id"]
    note = await crud.get_study_note(db, note_id, clerk_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study note not found."
        )
    return note

@app.post("/api/study-notes/generate")
async def generate_study_notes(
    req: GenerateStudyNotesRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Generate structured study notes and visual mind-map trees for concepts."""
    clerk_id = current_user["clerk_user_id"]
    
    # 1. Resolve Target Concepts
    all_concepts = await crud.get_concepts(db, clerk_id)
    if not all_concepts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No concepts found. Please upload materials and extract concepts first."
        )
        
    target_concepts = all_concepts
    if req.concept_ids:
        id_set = set(req.concept_ids)
        target_concepts = [c for c in all_concepts if str(c["_id"]) in id_set or c.get("name") in id_set]
    elif req.material_id:
        target_concepts = [c for c in all_concepts if str(c.get("material_id")) == req.material_id]
        
    if not target_concepts:
        target_concepts = all_concepts[:4]
        
    # 2. Retrieve context chunks
    context_chunks = []
    if req.material_id:
        chunks = await crud.get_material_chunks(db, req.material_id)
        context_chunks = [c.get("text", "") for c in chunks if c.get("text")]
        
    # 3. Call AI Service
    try:
        raw_notes = await AIService.generate_study_notes(
            concepts=target_concepts,
            depth=req.depth,
            context_chunks=context_chunks
        )
    except Exception as e:
        logger.error(f"Error generating study notes with AI: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service failed to synthesize study notes."
        )

    # 4. Map to StudyNote model instances
    name_to_concept = {c["name"]: c for c in target_concepts}
    default_concept = target_concepts[0]
    
    note_models: List[StudyNote] = []
    for item in raw_notes:
        matched_concept = name_to_concept.get(item.get("concept_name"), default_concept)
        concept_id_str = str(matched_concept["_id"]) if "_id" in matched_concept else matched_concept.get("id")
        material_id_str = str(matched_concept.get("material_id", "")) if matched_concept.get("material_id") else None
        
        # Guarantee mind_map_tree structure
        tree = item.get("mind_map_tree") or {}
        if not tree or not tree.get("label"):
            tree = {
                "id": "root",
                "label": matched_concept["name"],
                "details": item.get("summary", matched_concept.get("description", "")),
                "children": [
                    {
                        "id": "branch_takeaways",
                        "label": "Core Principles & Takeaways",
                        "details": "Key conceptual pillars",
                        "children": [
                            {"id": f"leaf_t_{i}", "label": t, "details": ""}
                            for i, t in enumerate(item.get("key_takeaways", [])[:4])
                        ]
                    },
                    {
                        "id": "branch_rules",
                        "label": "Axioms & Rules",
                        "details": "Formulae, syntax, or theoretical laws",
                        "children": [
                            {"id": f"leaf_r_{i}", "label": r, "details": ""}
                            for i, r in enumerate(item.get("formulae_or_rules", [])[:3])
                        ]
                    },
                    {
                        "id": "branch_traps",
                        "label": "Exam Traps & Pitfalls",
                        "details": "Frequent misconceptions",
                        "children": [
                            {"id": f"leaf_p_{i}", "label": p, "details": ""}
                            for i, p in enumerate(item.get("common_pitfalls", [])[:3])
                        ]
                    }
                ]
            }

        note_models.append(
            StudyNote(
                clerk_user_id=clerk_id,
                concept_id=concept_id_str,
                concept_name=matched_concept["name"],
                material_id=material_id_str,
                title=item.get("title", f"Study Note: {matched_concept['name']}"),
                summary=item.get("summary", matched_concept.get("description", "")),
                key_takeaways=item.get("key_takeaways", []),
                formulae_or_rules=item.get("formulae_or_rules", []),
                common_pitfalls=item.get("common_pitfalls", []),
                mind_map_tree=tree,
                markdown_content=item.get("markdown_content", "")
            )
        )
        
    # 5. Persist to database
    saved_notes = await crud.create_study_notes(db, note_models)
    
    # 6. Award Gamification XP (15 XP for synthesizing study notes)
    try:
        await GamificationService.award_xp(
            db=db,
            clerk_user_id=clerk_id,
            action="synthesis",
            metadata={"notes_count": len(saved_notes)}
        )
    except Exception as e:
        logger.warning(f"XP award for study notes synthesis failed: {e}")
        
    return {
        "success": True,
        "count": len(saved_notes),
        "notes": saved_notes
    }

@app.delete("/api/study-notes/all")
async def delete_all_study_notes(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete all study notes for the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    res = await crud.clear_user_data(db, clerk_id, "study_notes")
    return {"success": True, "message": "All study notes deleted.", **res}

@app.delete("/api/study-notes/{note_id}")
async def delete_study_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete an individual study note and mind-map."""
    clerk_id = current_user["clerk_user_id"]
    if note_id == "all":
        res = await crud.clear_user_data(db, clerk_id, "study_notes")
        return {"success": True, "message": "All study notes deleted.", **res}
    deleted = await crud.delete_study_note(db, note_id, clerk_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study note not found or not owned by user."
        )
    return {"success": True, "deleted_id": note_id}


# ─── Socratic AI Tutor & Real-Time Concept Chat API ───────────────────────────

@app.get("/api/tutor/sessions")
async def list_tutor_sessions(
    concept_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve all tutor sessions for the user."""
    clerk_id = current_user["clerk_user_id"]
    sessions = await crud.get_tutor_sessions(db, clerk_id, concept_id)
    return sessions

@app.get("/api/tutor/sessions/{session_id}")
async def get_tutor_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get single session conversation history."""
    clerk_id = current_user["clerk_user_id"]
    session = await crud.get_tutor_session(db, session_id, clerk_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutor session not found."
        )
    return session

@app.post("/api/tutor/chat")
async def socratic_tutor_chat(
    req: TutorChatRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Real-time interactive Socratic dialogue grounded in knowledge graph & source chunks.
    """
    clerk_id = current_user["clerk_user_id"]
    
    # 1. Retrieve or Create Session
    session = None
    if req.session_id:
        session = await crud.get_tutor_session(db, req.session_id, clerk_id)
        
    concept_name = req.concept_name
    concept_id = req.concept_id
    
    if not session:
        # Resolve concept name if only ID provided
        if concept_id and not concept_name:
            c = await crud.get_concept(db, concept_id, clerk_id)
            if c:
                concept_name = c.get("name")
                
        title = f"Tutoring: {concept_name or 'General Curriculum'}"
        new_session = TutorSession(
            clerk_user_id=clerk_id,
            concept_id=concept_id,
            concept_name=concept_name,
            session_title=title,
            messages=[]
        )
        session = await crud.create_tutor_session(db, new_session)
        
    session_id = str(session["_id"])
    
    # 2. Append User Message to DB
    user_msg = TutorChatMessage(
        role="user",
        content=req.message,
        concept_references=[concept_name] if concept_name else []
    )
    await crud.append_tutor_message(db, session_id, clerk_id, user_msg)
    
    # 3. Retrieve Grounding Material Chunks for Concept
    context_chunks = []
    if concept_id or concept_name:
        concepts = await crud.get_concepts(db, clerk_id)
        matched = next((c for c in concepts if str(c.get("_id")) == concept_id or c.get("name") == concept_name), None)
        if matched and matched.get("material_id"):
            m_chunks = await crud.get_material_chunks(db, matched["material_id"])
            context_chunks = [ch.get("text", "") for ch in m_chunks if ch.get("text")]
            
    # 4. Determine Learner Mastery State
    mastery_cat = "Learning"
    if concept_id:
        m = await crud.get_mastery_by_concept(db, concept_id, clerk_id)
        if m:
            mastery_cat = m.get("category", "Learning")

    # 5. Format conversation history for LLM
    all_msgs = session.get("messages", []) + [user_msg.model_dump()]
    llm_history = [{"role": m["role"], "content": m["content"]} for m in all_msgs[-8:]]
    
    # 6. Call Socratic AI Service
    ai_reply_text = await AIService.socratic_chat(
        messages=llm_history,
        concept_name=concept_name,
        context_chunks=context_chunks,
        tutor_mode=req.tutor_mode,
        mastery_category=mastery_cat
    )
    
    # 7. Append Assistant Message
    assistant_msg = TutorChatMessage(
        role="assistant",
        content=ai_reply_text,
        concept_references=[concept_name] if concept_name else []
    )
    updated_session = await crud.append_tutor_message(db, session_id, clerk_id, assistant_msg)
    
    # 8. Award Gamification XP (+5 XP for active inquiry)
    try:
        await GamificationService.award_xp(
            db=db,
            clerk_user_id=clerk_id,
            action_type="tutor_chat",
            metadata={"concept_name": concept_name}
        )
    except Exception as e:
        logger.warning(f"XP award for tutor chat failed: {e}")

    return {
        "session_id": session_id,
        "reply": ai_reply_text,
        "message": assistant_msg.model_dump(),
        "concept_name": concept_name
    }

@app.delete("/api/tutor/sessions/all")
async def delete_all_tutor_sessions(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete all tutor sessions for the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    res = await crud.clear_user_data(db, clerk_id, "tutor")
    return {"success": True, "message": "All tutor sessions deleted.", **res}

@app.delete("/api/tutor/sessions/{session_id}")
async def delete_tutor_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a tutor conversation session."""
    clerk_id = current_user["clerk_user_id"]
    if session_id == "all":
        res = await crud.clear_user_data(db, clerk_id, "tutor")
        return {"success": True, "message": "All tutor sessions deleted.", **res}
    deleted = await crud.delete_tutor_session(db, session_id, clerk_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutor session not found or not owned by user."
        )
    return {"success": True, "deleted_id": session_id}


# ─── Multi-Speaker Audio Podcast Overview API (NotebookLM-Style) ──────────────

@app.get("/api/podcasts")
async def list_podcasts(
    material_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List all synthesized audio podcast overviews for the user."""
    clerk_id = current_user["clerk_user_id"]
    podcasts = await crud.get_podcasts(db, clerk_id, material_id)
    return podcasts

@app.get("/api/podcasts/{podcast_id}")
async def get_podcast(
    podcast_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve single podcast episode with full dialogue script."""
    clerk_id = current_user["clerk_user_id"]
    podcast = await crud.get_podcast(db, podcast_id, clerk_id)
    if not podcast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast episode not found."
        )
    return podcast

@app.post("/api/podcasts/generate")
async def generate_podcast_episode(
    req: GeneratePodcastRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Generate a dynamic two-host conversational deep-dive audio podcast from materials.
    """
    clerk_id = current_user["clerk_user_id"]
    
    # 1. Resolve Target Material & Concepts
    material_title = "Curriculum Overview"
    context_chunks = []
    
    if req.material_id:
        mat = await crud.get_material(db, req.material_id, clerk_id)
        if mat:
            material_title = mat.get("title", "Study Material")
        m_chunks = await crud.get_material_chunks(db, req.material_id, clerk_user_id=clerk_id)
        context_chunks = [c.get("text", "") for c in m_chunks if c.get("text")]
        
    all_concepts = await crud.get_concepts(db, clerk_id)
    target_concepts = []
    if req.concept_ids:
        target_concepts = [c for c in all_concepts if str(c.get("_id")) in req.concept_ids or c.get("id") in req.concept_ids]
    elif req.material_id:
        target_concepts = [c for c in all_concepts if c.get("material_id") == req.material_id]
        
    if not target_concepts:
        target_concepts = all_concepts[:6]
        
    # If no chunk text found from material, construct from concepts
    if not context_chunks:
        context_chunks = [
            f"Concept {c['name']} (Difficulty: {c.get('difficulty')}): {c.get('description', '')}"
            for c in target_concepts
        ]

    # 2. Call AI Synthesis Engine
    raw_podcast = await AIService.generate_podcast(
        material_title=material_title,
        concepts=target_concepts,
        context_chunks=context_chunks,
        style=getattr(req, "style", "dynamic") or "dynamic"
    )
    
    # 3. Build Model Object
    script_turns = []
    for turn in raw_podcast.get("script", []):
        speaker = turn.get("speaker", "Alex")
        # Ensure pitch and rate differences between hosts
        pitch = 1.05 if speaker == "Sam" else 0.95
        rate = 1.02 if speaker == "Sam" else 0.98
        script_turns.append(
            PodcastDialogueTurn(
                speaker=speaker,
                text=turn.get("text", ""),
                emotion=turn.get("emotion", "enthusiastic"),
                pitch=pitch,
                rate=rate
            )
        )
        
    podcast_model = PodcastOverview(
        clerk_user_id=clerk_id,
        material_id=req.material_id,
        material_title=material_title,
        concept_ids=[str(c.get("_id") or c.get("id")) for c in target_concepts],
        title=raw_podcast.get("title", f"Deep Dive: {material_title}"),
        summary=raw_podcast.get("summary", "Interactive conversational audio overview."),
        episode_duration_est_minutes=round(len(script_turns) * 0.25, 1),
        hosts=["Alex (Lead Researcher)", "Sam (Curious Explorer)"],
        script=script_turns
    )
    
    # 4. Save in DB
    saved_podcast = await crud.create_podcast(db, podcast_model)
    
    # 5. Award Gamification XP (+20 XP for audio synthesis)
    try:
        await GamificationService.award_xp(
            db=db,
            clerk_user_id=clerk_id,
            action_type="podcast_generation",
            metadata={"title": podcast_model.title}
        )
    except Exception as e:
        logger.warning(f"XP award for podcast generation failed: {e}")
        
    return {
        "success": True,
        "podcast": saved_podcast
    }

@app.delete("/api/podcasts/all")
async def delete_all_podcasts(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete all podcasts for the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
    res = await crud.clear_user_data(db, clerk_id, "podcasts")
    return {"success": True, "message": "All podcasts deleted.", **res}

@app.delete("/api/podcasts/{podcast_id}")
async def delete_podcast(
    podcast_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a podcast episode."""
    clerk_id = current_user["clerk_user_id"]
    if podcast_id == "all":
        res = await crud.clear_user_data(db, clerk_id, "podcasts")
        return {"success": True, "message": "All podcasts deleted.", **res}
    deleted = await crud.delete_podcast(db, podcast_id, clerk_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast episode not found or not owned by user."
        )
    return {"success": True, "deleted_id": podcast_id}


# ─── Phase 26: Goal-to-Skill Gap Intelligence Routes ─────────────────────────

class GoalCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    target_role: Optional[str] = None
    target_exam: Optional[str] = None
    target_date: Optional[datetime] = None
    required_skills: List[RequiredSkill] = []

class GoalUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_role: Optional[str] = None
    target_exam: Optional[str] = None
    target_date: Optional[datetime] = None
    required_skills: Optional[List[RequiredSkill]] = None

@app.post("/api/goals")
async def create_goal(
    body: GoalCreateRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Create a persistent learning goal with target skills and mastery requirements.
    Supports learner-defined skills, verified system mappings, or reviewable AI suggestions.
    """
    clerk_id = current_user["clerk_user_id"]
    goal_model = Goal(
        clerk_user_id=clerk_id,
        title=body.title.strip(),
        description=body.description,
        target_role=body.target_role,
        target_exam=body.target_exam,
        target_date=body.target_date,
        required_skills=body.required_skills,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    saved = await crud.create_goal(db, goal_model)
    return saved

@app.get("/api/goals")
async def list_goals(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """List all goals belonging to the authenticated learner."""
    clerk_id = current_user["clerk_user_id"]
    return await crud.get_goals(db, clerk_id)

@app.get("/api/goals/{goal_id}")
async def get_goal_detail(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve detailed goal metadata and required skill benchmarks."""
    clerk_id = current_user["clerk_user_id"]
    goal = await crud.get_goal(db, goal_id, clerk_id)
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found or access denied."
        )
    return goal

@app.patch("/api/goals/{goal_id}")
async def update_goal(
    goal_id: str,
    body: GoalUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update goal benchmarks, target role/exam, or required skills."""
    clerk_id = current_user["clerk_user_id"]
    update_dict = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_dict:
        raise HTTPException(status_code=400, detail="No valid update fields provided.")
    updated = await crud.update_goal(db, goal_id, clerk_id, update_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="Goal not found or access denied.")
    return updated

@app.delete("/api/goals/{goal_id}")
async def delete_goal(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a goal owned by the authenticated learner."""
    clerk_id = current_user["clerk_user_id"]
    deleted = await crud.delete_goal(db, goal_id, clerk_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found or access denied.")
    return {"success": True, "deleted_goal_id": goal_id}

@app.get("/api/goals/{goal_id}/skill-gaps")
async def get_goal_skill_gaps(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Goal-to-Skill Gap Intelligence Analysis.
    Calculates required levels, current mastery (BKT), gaps, prerequisite blocking, evidence strength, and readiness.
    """
    clerk_id = current_user["clerk_user_id"]
    goal = await crud.get_goal(db, goal_id, clerk_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found or access denied.")
        
    analysis = await GoalGapAnalysisService.analyze_goal_gaps(db, clerk_id, goal)
    return analysis


# ==========================================
# PHASE 27 — LEARNER MISCONCEPTION & DIAGNOSIS
# ==========================================

diagnosis_service = LearningDiagnosisService()

@app.post("/api/learning/diagnosis", response_model=LearningDiagnosis)
async def create_learning_diagnosis(
    payload: DiagnosisRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Diagnose WHY the learner is struggling on a concept.
    Inputs: question, answer, correct_answer, concept, prerequisites, confidence, response time, BKT metrics.
    Output: Deterministic root cause (misconception, prerequisite weakness, confidence mismatch, retention decay, insufficient evidence).
    """
    clerk_id = current_user["clerk_user_id"]
    diagnosis = await diagnosis_service.diagnose_learner(
        user_id=clerk_id,
        concept_id=payload.concept_id,
        question=payload.question,
        answer=payload.answer,
        correct_answer=payload.correct_answer,
        confidence=payload.confidence,
        response_time_ms=payload.response_time_ms,
        prerequisites=payload.prerequisites,
        bkt_probability=payload.bkt_probability,
        bkt_uncertainty=payload.bkt_uncertainty,
        persist=True
    )
    return diagnosis

@app.get("/api/learning/diagnosis")
async def get_user_diagnoses(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all historical learning diagnoses for the authenticated learner."""
    clerk_id = current_user["clerk_user_id"]
    diagnoses = await crud.get_diagnoses(clerk_id)
    return diagnoses

@app.get("/api/learning/diagnosis/{concept_id}")
async def get_concept_diagnosis(
    concept_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get diagnoses for a specific concept for the authenticated learner."""
    clerk_id = current_user["clerk_user_id"]
    diagnoses = await crud.get_diagnoses(clerk_id, concept_id=concept_id)
    return diagnoses


# ==========================================
# PHASE 28 — WHAT-IF LEARNING SIMULATOR
# ==========================================

simulation_service = LearningSimulationService()

@app.post("/api/learning/simulate", response_model=SimulationResult)
async def simulate_learner_counterfactual(
    payload: SimulationRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Pure in-memory counterfactual simulator for "What-If" learner states.
    DOES NOT modify real database mastery, create events, award XP, or alter study paths.
    """
    clerk_id = current_user["clerk_user_id"]
    sim_result = await simulation_service.simulate_learning(
        user_id=clerk_id,
        request=payload
    )
    return sim_result


# ==========================================
# PHASE 29 — NEXT-BEST-LEARNING-ACTION ENGINE
# ==========================================

nba_service = NextBestLearningActionService()

@app.get("/api/learning/next-action", response_model=NextBestActionRecommendation)
async def get_next_best_learning_action(
    goal_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Deterministically computes the learner's single highest-leverage NEXT learning action.
    Inputs: Goal gap, prerequisite tree, BKT uncertainty, retention decay, active diagnoses.
    """
    clerk_id = current_user["clerk_user_id"]
    action = await nba_service.compute_next_best_action(
        clerk_user_id=clerk_id,
        goal_id=goal_id
    )
    return action


# ==========================================
# PHASE 30 — MASTERY EVIDENCE CHAIN
# ==========================================

mastery_evidence_service = MasteryEvidenceChainService()

@app.get("/api/learning/mastery-evidence/{concept_id}", response_model=MasteryEvidenceChain)
async def get_concept_mastery_evidence(
    concept_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Synthesizes the explainable proof chain behind a learner's concept mastery score.
    Answers 'WHY IS MY MASTERY X%?' with concrete, unfabricated evidence.
    """
    clerk_id = current_user["clerk_user_id"]
    evidence_chain = await mastery_evidence_service.get_mastery_evidence(
        clerk_user_id=clerk_id,
        concept_id=concept_id
    )
# ==========================================
# PHASE 32 — UNIFIED LEARNER INTELLIGENCE DASHBOARD
# ==========================================

@app.get("/api/dashboard/intelligence")
async def get_unified_learner_intelligence(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Unified Learner Intelligence Control Center.
    Aggregates:
    1. Active Goal
    2. Goal Readiness
    3. Skill Gap Summary
    4. Prerequisite Bottlenecks
    5. Recent Diagnoses
    6. Next-Best Learning Action
    7. Mastery Evidence Summary
    8. Adaptive Study Path
    9. Assignments
    10. Review-Due Concepts
    11. Resources
    12. XP / Level
    13. Recent Learner Activity
    14. What-If Simulator Capability
    """
    clerk_id = current_user["clerk_user_id"]
    
    # 1. Active Goal & Readiness
    goals = await crud.get_goals(db, clerk_id)
    active_goal = goals[0] if goals else None
    
    goal_gap_analysis = None
    if active_goal:
        try:
            goal_gap_analysis = await GoalGapAnalysisService.analyze_goal_gaps(db, clerk_id, active_goal)
        except Exception as e:
            logger.warning(f"Goal gap analysis error on dashboard: {e}")
            
    # 2. Next Best Action
    next_action = None
    try:
        next_action = await nba_service.compute_next_best_action(
            clerk_user_id=clerk_id,
            goal_id=str(active_goal.get("_id")) if active_goal else None
        )
    except Exception as e:
        logger.warning(f"NBA generation error on dashboard: {e}")

    # 3. Diagnoses
    diagnoses = await crud.get_diagnoses(clerk_id)
    
    # 4. Masteries & Review-due concepts
    masteries = await crud.get_mastery(db, clerk_id)
    concepts = await crud.get_concepts(db, clerk_id)
    
    review_due_concepts = []
    now = datetime.utcnow()
    for m in masteries:
        last_dt = m.get("last_reviewed_at")
        if last_dt:
            if isinstance(last_dt, str):
                try:
                    last_dt = datetime.fromisoformat(last_dt.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    last_dt = now
            days_since = (now - last_dt).total_seconds() / 86400.0
            if days_since >= 7.0:
                review_due_concepts.append({
                    "concept_id": m.get("concept_id"),
                    "concept_name": m.get("concept_name"),
                    "mastery_score": m.get("mastery_score"),
                    "days_inactive": int(days_since)
                })

    # 5. Assignments
    assignments = await crud.get_assignments(db, clerk_id) if hasattr(crud, "get_assignments") else []
    
    # 6. Gamification
    gamification = await crud.get_gamification(db, clerk_id)
    
    # 7. Recent Activity
    recent_events = await db.get_collection("learner_events").find({"clerk_user_id": clerk_id}).sort("timestamp", -1).to_list(length=10) if db.is_online else []

    # 8. Curated Resources
    resources = await get_resources(current_user=current_user, db=db)

    # 9. Adaptive Study Path
    study_path = await crud.get_study_path(db, clerk_id)

    return {
        "active_goal": active_goal,
        "goal_gap_analysis": goal_gap_analysis,
        "next_best_action": next_action,
        "recent_diagnoses": diagnoses[:5],
        "review_due_concepts": review_due_concepts[:5],
        "assignments": assignments[:5],
        "gamification": gamification or {"xp": 0, "level": 1, "level_name": "Beginner"},
        "recent_activity": crud.serialize_docs(recent_events),
        "study_path": study_path,
        "resources_count": len(resources),
        "total_concepts": len(concepts),
        "average_mastery": goal_gap_analysis.get("readiness_percentage") if goal_gap_analysis else (
            sum(m.get("mastery_score", 0.0) for m in masteries) / max(len(masteries), 1) if masteries else 0.0
        ),
        "simulator_ready": True
    }


# ─── MK-PATH 2.0: PHASE 1 — PERSONAL AI LEARNING & CAREER AGENT ──────────────

from .agent import (
    PersonalLearningAgent, AgentChatRequest, AgentChatResponse,
    AgentConversation, AgentIntent
)

@app.post("/api/agent/chat", response_model=AgentChatResponse)
async def agent_chat(
    req: AgentChatRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Central MK-Path Personal AI Learning & Career Agent chat endpoint.
    Orchestrates intent routing, unified learner context building, source attribution, and action recommendations.
    """
    clerk_id = current_user["clerk_user_id"]
    try:
        response = await PersonalLearningAgent.chat(
            db=db,
            clerk_user_id=clerk_id,
            request=req
        )
        return response
    except Exception as e:
        logger.error(f"Agent chat execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent consultation failed: {str(e)}"
        )

@app.get("/api/agent/conversations")
async def get_agent_conversations(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve all AI Agent learning conversations for current user."""
    clerk_id = current_user["clerk_user_id"]
    return await crud.get_agent_conversations(db, clerk_id)

@app.get("/api/agent/conversations/{conversation_id}")
async def get_agent_conversation_detail(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve single AI Agent learning conversation history."""
    clerk_id = current_user["clerk_user_id"]
    conv = await crud.get_agent_conversation(db, conversation_id, clerk_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conv

@app.delete("/api/agent/conversations/{conversation_id}")
async def delete_agent_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete single AI Agent learning conversation."""
    clerk_id = current_user["clerk_user_id"]
    success = await crud.delete_agent_conversation(db, conversation_id, clerk_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or unauthorized"
        )
    return {"status": "success", "message": "Conversation deleted"}


# ─── MK-PATH 2.0: PHASE 2 — YOUTUBE LEARNING INTELLIGENCE ─────────────────────

from .services.youtube import (
    YouTubeProcessor, YouTubeIngestRequest, YouTubeProcessResult
)

@app.post("/api/youtube/ingest")
async def ingest_youtube_video(
    req: YouTubeIngestRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Ingest YouTube educational video, extract captions with timestamps, chunk, embed, and extract concepts.
    """
    clerk_id = current_user["clerk_user_id"]
    try:
        result = await YouTubeProcessor.ingest_video(
            db=db,
            clerk_user_id=clerk_id,
            request=req
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"YouTube ingestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YouTube ingestion failed: {str(e)}"
        )

@app.get("/api/youtube/{material_id}")
async def get_youtube_details(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve detailed YouTube ingested material, video metadata, and status."""
    clerk_id = current_user["clerk_user_id"]
    mat = await crud.get_material(db, material_id, clerk_id)
    if not mat or mat.get("source_type") != "youtube":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube material not found")
    return mat

@app.get("/api/youtube/{material_id}/transcript")
async def get_youtube_transcript_route(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve complete normalized transcript of an ingested YouTube video."""
    clerk_id = current_user["clerk_user_id"]
    mat = await crud.get_material(db, material_id, clerk_id)
    if not mat or mat.get("source_type") != "youtube":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube material not found")
    return {
        "material_id": material_id,
        "title": mat.get("title"),
        "transcript": mat.get("raw_text", ""),
        "duration": mat.get("duration")
    }

@app.get("/api/youtube/{material_id}/segments")
async def get_youtube_segments_route(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve timestamped semantic video segments and chunks."""
    clerk_id = current_user["clerk_user_id"]
    mat = await crud.get_material(db, material_id, clerk_id)
    if not mat or mat.get("source_type") != "youtube":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube material not found")
    
    chunks = await crud.get_material_chunks(db, material_id=material_id, clerk_user_id=clerk_id)
    return {
        "material_id": material_id,
        "title": mat.get("title"),
        "segments": mat.get("segments", []),
        "chunks": chunks
    }

@app.post("/api/youtube/{material_id}/process")
async def reprocess_youtube_video(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Re-run concept extraction and RAG indexing on an ingested YouTube video."""
    clerk_id = current_user["clerk_user_id"]
    mat = await crud.get_material(db, material_id, clerk_id)
    if not mat or mat.get("source_type") != "youtube":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube material not found")

    text = mat.get("raw_text", "")
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Material has no transcript to process")

    # Extract concepts
    extraction = await AIService.extract_concepts_and_relationships(text[:12000])
    concepts = extraction.get("concepts", [])
    
    for c in concepts:
        concept_model = Concept(
            clerk_user_id=clerk_id,
            material_id=material_id,
            name=c["name"],
            description=c.get("description", ""),
            difficulty=c.get("difficulty", "intermediate"),
            prerequisites=c.get("prerequisites", []),
            exam_relevance=c.get("exam_relevance", 80),
            industry_relevance=c.get("industry_relevance", 85)
        )
        await crud.create_concept(db, concept_model)

    return {
        "material_id": material_id,
        "status": "READY",
        "concepts_extracted_count": len(concepts),
        "message": f"Successfully extracted {len(concepts)} concepts from YouTube video."
    }

@app.get("/api/youtube/{material_id}/notes")
async def get_youtube_study_notes(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Generate or retrieve structured high-yield notes from YouTube lecture content."""
    clerk_id = current_user["clerk_user_id"]
    mat = await crud.get_material(db, material_id, clerk_id)
    if not mat or mat.get("source_type") != "youtube":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube material not found")

    text = mat.get("raw_text", "")
    notes = await AIService.generate_study_notes(
        material_title=mat.get("title", "YouTube Lecture"),
        concepts=[],
        context_chunks=[text[:6000]]
    )
    return {
        "material_id": material_id,
        "video_title": mat.get("title"),
        "notes": notes
    }

# ==============================================================================
# PHASE 3: CAREER TWIN REST ENDPOINTS
# ==============================================================================

from .services.career_twin_service import CareerTwinService
from .services.career_twin_models import CareerTwinGoal

class AnalyzeJobRequest(BaseModel):
    job_description: str
    role_hint: Optional[str] = None

class CreateCareerGoalRequest(BaseModel):
    role: str
    company_or_industry: Optional[str] = None
    experience_level: Optional[str] = "Mid-Level"
    location_preference: Optional[str] = "Remote"
    target_date: Optional[datetime] = None
    job_description_raw: Optional[str] = None
    job_url: Optional[str] = None
    extracted_skills: Optional[List[dict]] = None

@app.get("/api/career/goals")
async def get_career_goals(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve all active career goals for the authenticated learner."""
    clerk_id = current_user["clerk_user_id"]
    goals = await crud.get_goals(db, clerk_id)
    return {"goals": goals}

@app.post("/api/career/analyze-job")
async def analyze_job_description(
    req: AnalyzeJobRequest,
    current_user: dict = Depends(get_current_user)
):
    """Parses a job description to extract technical competencies, frameworks, soft skills, and interview topics."""
    result = await CareerTwinService.analyze_job_description(req.job_description, req.role_hint)
    return result.model_dump()

@app.post("/api/career/goals")
async def create_career_goal(
    req: CreateCareerGoalRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create or extend a persistent Career Twin target goal."""
    clerk_id = current_user["clerk_user_id"]
    
    extracted_skills = req.extracted_skills or []
    if req.job_description_raw and not extracted_skills:
        analysis = await CareerTwinService.analyze_job_description(req.job_description_raw, req.role)
        extracted_skills = analysis.extracted_skill_nodes

    goal_doc = {
        "clerk_user_id": clerk_id,
        "title": req.role,
        "role": req.role,
        "company_or_industry": req.company_or_industry,
        "experience_level": req.experience_level,
        "location_preference": req.location_preference,
        "target_date": req.target_date,
        "job_description_raw": req.job_description_raw,
        "job_url": req.job_url,
        "extracted_skills": extracted_skills,
        "required_skills": [
            {"name": s.get("name"), "required_level": s.get("required_level", 75.0), "source": "job_description", "weight": s.get("career_importance", 1.2)}
            for s in extracted_skills
        ] if extracted_skills else []
    }
    
    if db.is_online:
        col = db.get_collection("goals")
        goal_doc["created_at"] = datetime.utcnow()
        goal_doc["updated_at"] = datetime.utcnow()
        res = await col.insert_one(goal_doc)
        goal_doc["_id"] = str(res.inserted_id)
    else:
        goal_doc["_id"] = "career_goal_" + str(len(crud._DEMO_DB.get("goals", [])) + 1)
        goal_doc["created_at"] = datetime.utcnow()
        goal_doc["updated_at"] = datetime.utcnow()
        crud._DEMO_DB.setdefault("goals", []).append(goal_doc)

    return {"goal": crud.serialize_doc(goal_doc), "message": "Career Goal created successfully"}

@app.get("/api/career/goals/{goal_id}")
async def get_career_goal(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Retrieve single career goal by ID."""
    clerk_id = current_user["clerk_user_id"]
    goal = await crud.get_goal(db, goal_id, clerk_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career goal not found")
    return {"goal": goal}

@app.get("/api/career/goals/{goal_id}/skills")
async def get_career_goal_skills(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get multi-dimensional Career Skill Graph with Knowledge, Practical, and Interview scores."""
    clerk_id = current_user["clerk_user_id"]
    goal = await crud.get_goal(db, goal_id, clerk_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career goal not found")
    nodes = await CareerTwinService.get_career_skill_graph(db, clerk_id, goal)
    return {"goal_id": goal_id, "skills": [n.model_dump() for n in nodes]}

@app.get("/api/career/goals/{goal_id}/gaps")
async def get_career_goal_gaps(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get knowledge gaps, evidence deficits, and prerequisite blockers for a career goal."""
    clerk_id = current_user["clerk_user_id"]
    goal = await crud.get_goal(db, goal_id, clerk_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career goal not found")
    nodes = await CareerTwinService.get_career_skill_graph(db, clerk_id, goal)
    gaps = [n.model_dump() for n in nodes if n.gap > 0 or n.has_evidence_deficit or n.prerequisite_status == "BLOCKED"]
    return {"goal_id": goal_id, "gaps": gaps}

@app.get("/api/career/goals/{goal_id}/readiness")
async def get_career_goal_readiness(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get explainable Career Twin readiness report, trajectory, and recommended next action."""
    clerk_id = current_user["clerk_user_id"]
    goal = await crud.get_goal(db, goal_id, clerk_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career goal not found")
    report = await CareerTwinService.calculate_career_readiness(db, clerk_id, goal)
    return report.model_dump()

@app.get("/api/career/goals/{goal_id}/evidence")
async def get_career_goal_evidence(
    goal_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get itemized evidence chain backing Career Twin skills."""
    clerk_id = current_user["clerk_user_id"]
    goal = await crud.get_goal(db, goal_id, clerk_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career goal not found")
    nodes = await CareerTwinService.get_career_skill_graph(db, clerk_id, goal)
    evidence_summary = [
        {
            "skill_name": n.skill_name,
            "knowledge_score": n.knowledge_score,
            "practical_score": n.practical_evidence_score,
            "interview_score": n.interview_evidence_score,
            "evidence_quality": n.evidence_quality.value,
            "evidence_count": n.evidence_count,
            "has_evidence_deficit": n.has_evidence_deficit
        }
        for n in nodes
    ]
    return {"goal_id": goal_id, "evidence_summary": evidence_summary}

# ==============================================================================
# PHASE 4: MK-PATH MCP TOOL EXECUTION REST ENDPOINTS
# ==============================================================================

from .mcp.server import MCPToolRegistry

class MCPExecuteRequest(BaseModel):
    tool_name: str
    arguments: Optional[dict] = None

@app.get("/api/mcp/tools")
async def list_mcp_tools(current_user: dict = Depends(get_current_user)):
    """List available MCP tools for the authenticated learner."""
    return {
        "tools": [
            {"name": "mkpath_get_learner_profile", "type": "READ", "description": "Get authenticated learner profile"},
            {"name": "mkpath_get_goals", "type": "READ", "description": "Get user learning & career goals"},
            {"name": "mkpath_get_mastery", "type": "READ", "description": "Get BKT concept mastery scores & probabilities"},
            {"name": "mkpath_get_skill_gap", "type": "READ", "description": "Analyze persistent skill gaps for a goal"},
            {"name": "mkpath_get_diagnosis", "type": "READ", "description": "Get misconception & prerequisite diagnoses"},
            {"name": "mkpath_search_materials", "type": "READ", "description": "Vector search in user's study materials"},
            {"name": "mkpath_search_knowledge_graph", "type": "READ", "description": "Fetch user concepts & relationships"},
            {"name": "mkpath_get_next_action", "type": "READ", "description": "Compute highest-impact Next Best Action"},
            {"name": "mkpath_get_career_requirements", "type": "READ", "description": "Get Career Twin readiness & evidence"},
            {"name": "mkpath_search_current_industry", "type": "READ", "description": "Live web search for latest industry tech"},
            {"name": "mkpath_get_assignments", "type": "READ", "description": "Fetch pending/completed assignments"},
            {"name": "mkpath_create_assignment", "type": "WRITE", "description": "Create a new targeted practice assignment"}
        ]
    }

@app.post("/api/mcp/execute")
async def execute_mcp_tool(
    req: MCPExecuteRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Execute an authorized MK-Path MCP tool within user scope."""
    clerk_id = current_user["clerk_user_id"]
    try:
        result = await MCPToolRegistry.execute_tool(
            db=db,
            clerk_user_id=clerk_id,
            tool_name=req.tool_name,
            arguments=req.arguments or {}
        )
        return {"success": True, "tool_name": req.tool_name, "result": result}
    except Exception as e:
        logger.error(f"MCP Tool execution error ({req.tool_name}): {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))




