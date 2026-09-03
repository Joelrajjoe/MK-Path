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
    UserProfile, Material, Concept, Relationship, Question, Attempt, 
    Mastery, AttemptSubmit, Gamification, LearnerEvent, UserPreferences, 
    Assignment, AssignmentQuestion, ResourceFeedback, Flashcard, 
    FlashcardReviewRequest, GenerateFlashcardsRequest, StudyNote, GenerateStudyNotesRequest,
    TutorChatMessage, TutorSession, TutorChatRequest,
    PodcastOverview, PodcastDialogueTurn, GeneratePodcastRequest
)
from .services.ai import AIService
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
    Protected route retrieving user profile.
    If database is online, lazily creates/updates user in MongoDB user_profiles.
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
        return profile_record
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
    try:
        extract_result = await extractor.extract(file_bytes, content_type or f"application/{ext}")
        
        extracted_text = extract_result.get("text", "").strip()
        segments = extract_result.get("segments", [])
        metadata = extract_result.get("metadata", {})
        extraction_status = extract_result.get("extraction_status", "failed")
        ocr_status = extract_result.get("ocr_status", "n/a")
        transcription_status = extract_result.get("transcription_status", "n/a")
        extraction_method = extract_result.get("extraction_method", "direct_text")
    except Exception as e:
        logger.error(f"Unified extraction failed for {filename}: {e}")
        extracted_text = ""
        segments = []
        metadata = {}
        extraction_status = "failed"
        ocr_status = "failed"
        transcription_status = "failed"
        extraction_method = "direct_text"

    # 4. Save to Database
    material_model = Material(
        clerk_user_id=clerk_id,
        title=filename,
        file_name=filename,
        file_size=file_size,
        content_type=content_type or f"application/{ext}",
        raw_text=extracted_text,
        status=extraction_status,
        created_at=datetime.utcnow(),
        source_type=source_type,
        mime_type=content_type or f"application/{ext}",
        duration=metadata.get("duration"),
        page_count=metadata.get("page_count"),
        transcription_status=transcription_status,
        ocr_status=ocr_status,
        extraction_method=extraction_method,
        segments=segments
    )

    try:
        material_record = await crud.create_material(db, material_model)
        
        # 5. RAG Pipeline: Chunking and Embedding
        if extracted_text and extraction_status == "processed":
            try:
                # Simple chunking: 500 words per chunk
                words = extracted_text.split()
                chunk_size = 500
                chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
                if chunks:
                    # Generate embeddings via Gemini
                    embeddings = await AIService.generate_embeddings(chunks)
                    
                    # Prepare chunk records
                    chunks_data = []
                    for idx, (text_chunk, emb) in enumerate(zip(chunks, embeddings)):
                        chunks_data.append({
                            "chunk_index": idx,
                            "text": text_chunk,
                            "embedding": emb,
                            "clerk_user_id": clerk_id
                        })
                    
                    # Save to db
                    await crud.save_material_chunks(db, str(material_record["_id"]), chunks_data)
            except Exception as e:
                logger.error(f"Failed to process RAG chunks for material {material_record.get('_id')}: {e}")
                
        # 6. Log User Activity
        await crud.log_user_activity(
            db, 
            clerk_id, 
            event_type="material_uploaded", 
            entity_type="material",
            entity_id=str(material_record["_id"]),
            metadata={"filename": filename}
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
        return []

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

    if material["status"] == "failed":
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

    # Map concepts to React Flow Nodes arranged in col grids
    idx = 0
    for c in concepts:
        concept_id_str = str(c["_id"])
        m_info = mastery_map.get(concept_id_str)
        
        if m_info:
            mastery_score = m_info["score"]
            mastery_state = m_info["category"]
        else:
            mastery_score = None
            mastery_state = "Not assessed"

        row = idx // 3
        col = idx % 3
        x = col * 280
        y = row * 160

        nodes.append({
            "id": concept_id_str,
            "type": "default",
            "position": {"x": x, "y": y},
            "data": {
                "label": c["name"],
                "name": c["name"],
                "difficulty": c["difficulty"],
                "exam_relevance": c["exam_relevance"],
                "industry_relevance": c["industry_relevance"],
                "mastery_score": mastery_score,
                "mastery_state": mastery_state,
                "description": c["description"],
                "prerequisites": c.get("prerequisites", [])
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
        idx += 1

    # Map relationships to React Flow Edges
    name_to_id = {c["name"]: str(c["_id"]) for c in concepts}
    for r in relationships:
        source_id = name_to_id.get(r["source_concept_name"])
        target_id = name_to_id.get(r["target_concept_name"])
        
        if source_id and target_id:
            edges.append({
                "id": f"e_{source_id}_{target_id}",
                "source": source_id,
                "target": target_id,
                "label": r["relationship_type"].replace("_", " "),
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
        if db.is_online:
            # Generate search query from target concepts
            query_text = " ".join([c["name"] + ": " + c.get("description", "") for c in target_concepts])
            query_emb_list = await AIService.generate_embeddings([query_text])
            if query_emb_list:
                query_embedding = query_emb_list[0]
                # Retrieve chunks using fallback vector search
                relevant_chunk_docs = await crud.TEMPORARY_VECTOR_SEARCH_FALLBACK(db, clerk_id, query_embedding, top_k=5)
                context_chunks = [d["text"] for d in relevant_chunk_docs if "text" in d]

        raw_questions = await AIService.generate_questions_for_concepts(
            target_concepts, 
            req.num_questions, 
            user_profile=user_profile, 
            context_chunks=context_chunks
        )
        
        # 3. Post-Generation Source Validation
        if db.is_online:
            # Re-fetch chunks if we had them, to pass chunk IDs
            pass # Currently generate_questions_for_concepts does not strictly remove ungrounded questions without validate_source_refs, but Groq prompt forces INSUFFICIENT_SOURCE_CONTENT.
            
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
            explanation=q.get("explanation", "Matches curriculum mapping.")
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
    valid_categories = {"assessments", "gamification", "materials", "concepts", "study_paths", "resources", "all"}
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
    
    # Auto-generate questions via AI if none provided and concept_names are given
    questions = body.questions
    if not questions and body.concept_names:
        try:
            ai = AIService()
            # Get some concepts from DB to generate questions
            concept_data = []
            for cid in body.concept_ids[:3]:
                col = db.get_collection("concepts") if db.is_online else None
                if col:
                    from bson import ObjectId as OID
                    doc = await col.find_one({"_id": OID(cid), "clerk_user_id": clerk_id})
                    if doc:
                        concept_data.append({"name": doc["name"], "description": doc.get("description", "")})
            if concept_data:
                generated = await ai.generate_questions(concept_data, body.difficulty)
                questions = [{"question_text": q["question"], "options": q["options"],
                              "correct_option_index": q["correct_option"], "question_type": "mcq",
                              "concept_name": q.get("concept_name", ""), "difficulty": body.difficulty,
                              "explanation": q.get("explanation", "")} for q in generated]
        except Exception as e:
            logger.warning(f"AI question generation failed for assignment: {e}")
            questions = []

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


@app.delete("/api/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete an assignment owned by the authenticated user."""
    clerk_id = current_user["clerk_user_id"]
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

@app.delete("/api/flashcards/{card_id}")
async def delete_flashcard(
    card_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete an individual flashcard."""
    clerk_id = current_user["clerk_user_id"]
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

@app.delete("/api/study-notes/{note_id}")
async def delete_study_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete an individual study note and mind-map."""
    clerk_id = current_user["clerk_user_id"]
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
            action="tutor_chat",
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

@app.delete("/api/tutor/sessions/{session_id}")
async def delete_tutor_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a tutor conversation session."""
    clerk_id = current_user["clerk_user_id"]
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
        m_chunks = await crud.get_material_chunks(db, req.material_id)
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
        style=req.style
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
            action="podcast_generation",
            metadata={"title": podcast_model.title}
        )
    except Exception as e:
        logger.warning(f"XP award for podcast generation failed: {e}")
        
    return {
        "success": True,
        "podcast": saved_podcast
    }

@app.delete("/api/podcasts/{podcast_id}")
async def delete_podcast(
    podcast_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a podcast episode."""
    clerk_id = current_user["clerk_user_id"]
    deleted = await crud.delete_podcast(db, podcast_id, clerk_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podcast episode not found or not owned by user."
        )
    return {"success": True, "deleted_id": podcast_id}







