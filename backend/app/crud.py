import logging
from datetime import datetime
from bson import ObjectId
from typing import List, Optional, Dict, Any
from .models import (
    UserProfile, Material, Concept, Relationship, Question, Attempt, 
    Mastery, StudyPath, Resource, Gamification, LearnerEvent, ResourceFeedback, 
    MaterialChunk, UserActivity, Flashcard, StudyNote, TutorSession, TutorChatMessage,
    PodcastOverview
)
import math
from .database import DatabaseManager

logger = logging.getLogger("mkpath.crud")

# --- Helper Functions for MongoDB Document Serialization ---

def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB _id ObjectId to string for JSON serialization."""
    if not doc:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [serialize_doc(d) for d in docs if d]


# --- In-Memory Demo Database Fallback ---

_DEMO_DB: Dict[str, List[Dict[str, Any]]] = {
    "user_profiles": [
        {
            "_id": ObjectId("64e8cf65f5a65c4dbf000001"),
            "clerk_user_id": "user_demo_12345",
            "email": "demo_user@mkpath.edu",
            "display_name": "Demo Student",
            "avatar_url": "",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ],
    "materials": [],
    "concepts": [],
    "relationships": [],
    "questions": [],
    "attempts": [],
    "mastery": [],
    "study_paths": [],
    "resources": [],
    "material_chunks": [],
    "user_activity": [],
    "flashcards": [],
    "study_notes": [],
    "tutor_sessions": [],
    "podcasts": [],
    "assignments": [],
    "goals": [],
    "learning_diagnoses": [],
    "gamification": [
        {
            "_id": ObjectId("64e8cf65f5a65c4dbf000002"),
            "clerk_user_id": "user_demo_12345",
            "xp": 0,
            "level": 1,
            "level_name": "Beginner",
            "achievements": [],
            "updated_at": datetime.utcnow()
        }
    ]
}

def _demo_get_all(collection: str, clerk_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    docs = _DEMO_DB.get(collection, [])
    if clerk_user_id:
        return [d for d in docs if d.get("clerk_user_id") == clerk_user_id]
    return docs

def _demo_get_by_id(collection: str, doc_id: str, clerk_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    docs = _DEMO_DB.get(collection, [])
    for d in docs:
        d_id = str(d.get("_id"))
        if d_id == doc_id or d.get("clerk_user_id") == doc_id:
            if not clerk_user_id or d.get("clerk_user_id") == clerk_user_id:
                return d
    return None

def _demo_insert(collection: str, data: Dict[str, Any]) -> Dict[str, Any]:
    if "_id" not in data:
        data["_id"] = ObjectId()
    if collection not in _DEMO_DB:
        _DEMO_DB[collection] = []
    _DEMO_DB[collection].append(data)
    return data

def _demo_update(collection: str, doc_id: str, clerk_user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    docs = _DEMO_DB.get(collection, [])
    for d in docs:
        if str(d.get("_id")) == doc_id:
            if d.get("clerk_user_id") == clerk_user_id:
                d.update(updates)
                d["updated_at"] = datetime.utcnow()
                return d
    return None

def _demo_delete(collection: str, doc_id: str, clerk_user_id: str) -> bool:
    docs = _DEMO_DB.get(collection, [])
    for i, d in enumerate(docs):
        if str(d.get("_id")) == doc_id:
            if d.get("clerk_user_id") == clerk_user_id:
                docs.pop(i)
                return True
    return False


# --- User Profile Operations ---

async def get_user_profile(db: DatabaseManager, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("user_profiles")
        return serialize_doc(await col.find_one({"clerk_user_id": clerk_user_id}))
    else:
        return serialize_doc(_demo_get_by_id("user_profiles", clerk_user_id))

async def create_or_update_user_profile(db: DatabaseManager, profile: UserProfile) -> Dict[str, Any]:
    profile_dict = profile.model_dump()
    if db.is_online:
        col = db.get_collection("user_profiles")
        
        # Remove created_at from the $set document to avoid conflict with $setOnInsert
        if "created_at" in profile_dict:
            del profile_dict["created_at"]
            
        await col.update_one(
            {"clerk_user_id": profile.clerk_user_id},
            {
                "$set": profile_dict,
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
        return serialize_doc(await col.find_one({"clerk_user_id": profile.clerk_user_id}))
    else:
        existing = _demo_get_by_id("user_profiles", profile.clerk_user_id)
        if existing:
            existing.update(profile_dict)
            existing["updated_at"] = datetime.utcnow()
            return serialize_doc(existing)
        return serialize_doc(_demo_insert("user_profiles", profile_dict))


# --- Materials Operations (User Isolated) ---

async def get_materials(db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("materials")
        cursor = col.find({"clerk_user_id": clerk_user_id})
        return serialize_docs(await cursor.to_list(length=100))
    else:
        return serialize_docs(_demo_get_all("materials", clerk_user_id))

async def get_material(db: DatabaseManager, material_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    try:
        obj_id = ObjectId(material_id)
    except Exception:
        return None

    if db.is_online:
        col = db.get_collection("materials")
        # Enforce clerk_user_id scoping on read
        return serialize_doc(await col.find_one({"_id": obj_id, "clerk_user_id": clerk_user_id}))
    else:
        return serialize_doc(_demo_get_by_id("materials", material_id, clerk_user_id))

async def create_material(db: DatabaseManager, material: Material) -> Dict[str, Any]:
    material_dict = material.model_dump()
    if db.is_online:
        col = db.get_collection("materials")
        res = await col.insert_one(material_dict)
        return serialize_doc(await col.find_one({"_id": res.inserted_id}))
    else:
        return serialize_doc(_demo_insert("materials", material_dict))

async def update_material_status(db: DatabaseManager, material_id: str, clerk_user_id: str, status: str, error_message: str = None) -> bool:
    update_fields = {"status": status}
    if error_message is not None:
        update_fields["error_message"] = error_message
    if db.is_online:
        col = db.get_collection("materials")
        try:
            res = await col.update_one(
                {"_id": ObjectId(material_id), "clerk_user_id": clerk_user_id},
                {"$set": update_fields}
            )
            return res.modified_count > 0
        except Exception:
            return False
    else:
        mat = next((d for d in _DEMO_DB.get("materials", []) if str(d.get("_id")) == material_id and d.get("clerk_user_id") == clerk_user_id), None)
        if mat:
            mat["status"] = status
            if error_message is not None:
                mat["error_message"] = error_message
            return True
        return False

async def update_material_title(db: DatabaseManager, material_id: str, clerk_user_id: str, title: str) -> bool:
    if db.is_online:
        col = db.get_collection("materials")
        try:
            res = await col.update_one(
                {"_id": ObjectId(material_id), "clerk_user_id": clerk_user_id},
                {"$set": {"title": title}}
            )
            return res.modified_count > 0
        except Exception:
            return False
    else:
        mat = next((d for d in _DEMO_DB.get("materials", []) if str(d.get("_id")) == material_id and d.get("clerk_user_id") == clerk_user_id), None)
        if mat:
            mat["title"] = title
            return True
        return False

async def update_concept(db: DatabaseManager, concept_id: str, clerk_user_id: str, update_fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Remove immutable keys
    update_fields.pop("_id", None)
    update_fields.pop("clerk_user_id", None)
    
    if db.is_online:
        col = db.get_collection("concepts")
        try:
            res = await col.update_one(
                {"_id": ObjectId(concept_id), "clerk_user_id": clerk_user_id},
                {"$set": update_fields}
            )
            return await get_concept(db, concept_id, clerk_user_id)
        except Exception:
            return None
    else:
        con = next((d for d in _DEMO_DB.get("concepts", []) if str(d.get("_id")) == concept_id and d.get("clerk_user_id") == clerk_user_id), None)
        if con:
            con.update(update_fields)
            return serialize_doc(con)
        return None

async def merge_concepts(db: DatabaseManager, clerk_user_id: str, primary_concept_id: str, duplicate_concept_id: str) -> Optional[Dict[str, Any]]:
    """Merges duplicate_concept into primary_concept and re-points questions, attempts, relationships, and mastery."""
    primary = await get_concept(db, primary_concept_id, clerk_user_id)
    duplicate = await get_concept(db, duplicate_concept_id, clerk_user_id)
    if not primary or not duplicate:
        return None

    p_id = str(primary["_id"])
    d_id = str(duplicate["_id"])
    p_name = primary["name"]
    d_name = duplicate["name"]

    # Merge prerequisites (union without duplicates)
    merged_prereqs = list(set(primary.get("prerequisites", []) + duplicate.get("prerequisites", [])))
    if p_name in merged_prereqs:
        merged_prereqs.remove(p_name)
    if d_name in merged_prereqs:
        merged_prereqs.remove(d_name)

    # Merge source_refs
    merged_refs = primary.get("source_refs", []) + duplicate.get("source_refs", [])

    # Update primary concept
    await update_concept(db, p_id, clerk_user_id, {
        "prerequisites": merged_prereqs,
        "source_refs": merged_refs,
        "exam_relevance": max(primary.get("exam_relevance", 80), duplicate.get("exam_relevance", 80)),
        "industry_relevance": max(primary.get("industry_relevance", 80), duplicate.get("industry_relevance", 80))
    })

    # Repoint Questions
    if db.is_online:
        await db.get_collection("questions").update_many(
            {"concept_id": d_id, "clerk_user_id": clerk_user_id},
            {"$set": {"concept_id": p_id, "concept_name": p_name}}
        )
        await db.get_collection("attempts").update_many(
            {"concept_id": d_id, "clerk_user_id": clerk_user_id},
            {"$set": {"concept_id": p_id}}
        )
        # Update relationships referencing duplicate name
        await db.get_collection("relationships").update_many(
            {"source_concept_name": d_name, "clerk_user_id": clerk_user_id},
            {"$set": {"source_concept_name": p_name}}
        )
        await db.get_collection("relationships").update_many(
            {"target_concept_name": d_name, "clerk_user_id": clerk_user_id},
            {"$set": {"target_concept_name": p_name}}
        )
        # Delete duplicate concept record
        await db.get_collection("concepts").delete_one({"_id": ObjectId(d_id), "clerk_user_id": clerk_user_id})
        await db.get_collection("mastery").delete_many({"concept_id": d_id, "clerk_user_id": clerk_user_id})
    else:
        for q in _DEMO_DB.get("questions", []):
            if q.get("concept_id") == d_id and q.get("clerk_user_id") == clerk_user_id:
                q["concept_id"] = p_id
                q["concept_name"] = p_name
        for a in _DEMO_DB.get("attempts", []):
            if a.get("concept_id") == d_id and a.get("clerk_user_id") == clerk_user_id:
                a["concept_id"] = p_id
        for r in _DEMO_DB.get("relationships", []):
            if r.get("clerk_user_id") == clerk_user_id:
                if r.get("source_concept_name") == d_name:
                    r["source_concept_name"] = p_name
                if r.get("target_concept_name") == d_name:
                    r["target_concept_name"] = p_name
        _DEMO_DB["concepts"] = [c for c in _DEMO_DB.get("concepts", []) if not (str(c.get("_id")) == d_id and c.get("clerk_user_id") == clerk_user_id)]
        _DEMO_DB["mastery"] = [m for m in _DEMO_DB.get("mastery", []) if not (m.get("concept_id") == d_id and m.get("clerk_user_id") == clerk_user_id)]

    return await get_concept(db, p_id, clerk_user_id)


# --- Concepts & Relationships Operations (User Isolated) ---

async def get_concepts(db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("concepts")
        cursor = col.find({"clerk_user_id": clerk_user_id})
        return serialize_docs(await cursor.to_list(length=500))
    else:
        return serialize_docs(_demo_get_all("concepts", clerk_user_id))

async def get_concept(db: DatabaseManager, concept_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    try:
        obj_id = ObjectId(concept_id)
    except Exception:
        return None

    if db.is_online:
        col = db.get_collection("concepts")
        return serialize_doc(await col.find_one({"_id": obj_id, "clerk_user_id": clerk_user_id}))
    else:
        return serialize_doc(_demo_get_by_id("concepts", concept_id, clerk_user_id))

async def create_concepts(db: DatabaseManager, concepts: List[Concept]) -> List[Dict[str, Any]]:
    concept_dicts = [c.model_dump() for c in concepts]
    if not concept_dicts:
        return []

    if db.is_online:
        col = db.get_collection("concepts")
        res = await col.insert_many(concept_dicts)
        inserted_ids = res.inserted_ids
        cursor = col.find({"_id": {"$in": inserted_ids}})
        return serialize_docs(await cursor.to_list(length=len(inserted_ids)))
    else:
        inserted = []
        for c in concept_dicts:
            inserted.append(_demo_insert("concepts", c))
        return serialize_docs(inserted)

async def get_relationships(db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("relationships")
        cursor = col.find({"clerk_user_id": clerk_user_id})
        return serialize_docs(await cursor.to_list(length=1000))
    else:
        return serialize_docs(_demo_get_all("relationships", clerk_user_id))

async def create_relationships(db: DatabaseManager, relationships: List[Relationship]) -> List[Dict[str, Any]]:
    rel_dicts = [r.model_dump() for r in relationships]
    if not rel_dicts:
        return []

    if db.is_online:
        col = db.get_collection("relationships")
        res = await col.insert_many(rel_dicts)
        cursor = col.find({"_id": {"$in": res.inserted_ids}})
        return serialize_docs(await cursor.to_list(length=len(res.inserted_ids)))
    else:
        inserted = []
        for r in rel_dicts:
            inserted.append(_demo_insert("relationships", r))
        return serialize_docs(inserted)


# --- Quiz Questions Operations (User Isolated) ---

async def get_questions(db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("questions")
        cursor = col.find({"clerk_user_id": clerk_user_id})
        return serialize_docs(await cursor.to_list(length=1000))
    else:
        return serialize_docs(_demo_get_all("questions", clerk_user_id))

async def get_question(db: DatabaseManager, question_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    try:
        obj_id = ObjectId(question_id)
    except Exception:
        return None
    if db.is_online:
        col = db.get_collection("questions")
        return serialize_doc(await col.find_one({"_id": obj_id, "clerk_user_id": clerk_user_id}))
    else:
        return serialize_doc(_demo_get_by_id("questions", question_id, clerk_user_id))

async def create_questions(db: DatabaseManager, questions: List[Question]) -> List[Dict[str, Any]]:
    q_dicts = [q.model_dump() for q in questions]
    if not q_dicts:
        return []

    if db.is_online:
        col = db.get_collection("questions")
        res = await col.insert_many(q_dicts)
        cursor = col.find({"_id": {"$in": res.inserted_ids}})
        return serialize_docs(await cursor.to_list(length=len(res.inserted_ids)))
    else:
        inserted = []
        for q in q_dicts:
            inserted.append(_demo_insert("questions", q))
        return serialize_docs(inserted)


# --- Attempts & Mastery Operations (User Isolated) ---

async def get_attempts(db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("attempts")
        cursor = col.find({"clerk_user_id": clerk_user_id})
        return serialize_docs(await cursor.to_list(length=5000))
    else:
        return serialize_docs(_demo_get_all("attempts", clerk_user_id))

async def create_attempt(db: DatabaseManager, attempt: Attempt) -> Dict[str, Any]:
    attempt_dict = attempt.model_dump()
    if db.is_online:
        col = db.get_collection("attempts")
        res = await col.insert_one(attempt_dict)
        return serialize_doc(await col.find_one({"_id": res.inserted_id}))
    else:
        return serialize_doc(_demo_insert("attempts", attempt_dict))

async def get_mastery_by_concept(db: DatabaseManager, concept_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("mastery")
        return serialize_doc(await col.find_one({"concept_id": concept_id, "clerk_user_id": clerk_user_id}))
    else:
        docs = _demo_get_all("mastery", clerk_user_id)
        for d in docs:
            if d.get("concept_id") == concept_id:
                return serialize_doc(d)
        return None

async def get_mastery(db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("mastery")
        cursor = col.find({"clerk_user_id": clerk_user_id})
        return serialize_docs(await cursor.to_list(length=500))
    else:
        return serialize_docs(_demo_get_all("mastery", clerk_user_id))

async def create_or_update_mastery(db: DatabaseManager, mastery: Mastery) -> Dict[str, Any]:
    m_dict = mastery.model_dump()
    if db.is_online:
        col = db.get_collection("mastery")
        await col.update_one(
            {"clerk_user_id": mastery.clerk_user_id, "concept_id": mastery.concept_id},
            {"$set": m_dict},
            upsert=True
        )
        return serialize_doc(await col.find_one({"clerk_user_id": mastery.clerk_user_id, "concept_id": mastery.concept_id}))
    else:
        # Find in demo DB
        docs = _demo_get_all("mastery", mastery.clerk_user_id)
        existing = None
        for d in docs:
            if d.get("concept_id") == mastery.concept_id:
                existing = d
                break
        
        if existing:
            existing.update(m_dict)
            return serialize_doc(existing)
        return serialize_doc(_demo_insert("mastery", m_dict))


# --- Study Path Operations (User Isolated) ---

async def get_study_path(db: DatabaseManager, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("study_paths")
        return serialize_doc(await col.find_one({"clerk_user_id": clerk_user_id}))
    else:
        return serialize_doc(_demo_get_by_id("study_paths", clerk_user_id))

async def create_or_update_study_path(db: DatabaseManager, path: StudyPath) -> Dict[str, Any]:
    p_dict = path.model_dump()
    if db.is_online:
        col = db.get_collection("study_paths")
        await col.update_one(
            {"clerk_user_id": path.clerk_user_id},
            {"$set": p_dict},
            upsert=True
        )
        return serialize_doc(await col.find_one({"clerk_user_id": path.clerk_user_id}))
    else:
        existing = _demo_get_by_id("study_paths", path.clerk_user_id)
        if existing:
            existing.update(p_dict)
            existing["updated_at"] = datetime.utcnow()
            return serialize_doc(existing)
        return serialize_doc(_demo_insert("study_paths", p_dict))


# --- Global Resources Operations (Shared / Global) ---

async def get_resources(db: DatabaseManager) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("resources")
        cursor = col.find({})
        return serialize_docs(await cursor.to_list(length=100))
    else:
        return serialize_docs(_demo_get_all("resources"))

async def create_resource(db: DatabaseManager, resource: Resource) -> Dict[str, Any]:
    res_dict = resource.model_dump()
    if db.is_online:
        col = db.get_collection("resources")
        res = await col.insert_one(res_dict)
        return serialize_doc(await col.find_one({"_id": res.inserted_id}))
    else:
        return serialize_doc(_demo_insert("resources", res_dict))

async def create_or_update_resource_feedback(db: DatabaseManager, feedback: ResourceFeedback) -> Dict[str, Any]:
    f_dict = feedback.model_dump()
    if db.is_online:
        col = db.get_collection("resource_feedback")
        await col.update_one(
            {"clerk_user_id": feedback.clerk_user_id, "resource_id": feedback.resource_id},
            {"$set": f_dict},
            upsert=True
        )
        return serialize_doc(await col.find_one({"clerk_user_id": feedback.clerk_user_id, "resource_id": feedback.resource_id}))
    else:
        if "resource_feedback" not in _DEMO_DB:
            _DEMO_DB["resource_feedback"] = []
        docs = _demo_get_all("resource_feedback", feedback.clerk_user_id)
        existing = None
        for d in docs:
            if d.get("resource_id") == feedback.resource_id:
                existing = d
                break
        if existing:
            existing.update(f_dict)
            return serialize_doc(existing)
        return serialize_doc(_demo_insert("resource_feedback", f_dict))

async def get_resource_feedback(db: DatabaseManager, resource_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("resource_feedback")
        cursor = col.find({"resource_id": resource_id})
        return serialize_docs(await cursor.to_list(length=1000))
    else:
        if "resource_feedback" not in _DEMO_DB:
            _DEMO_DB["resource_feedback"] = []
        return serialize_docs([f for f in _DEMO_DB["resource_feedback"] if f.get("resource_id") == resource_id])

async def get_user_resource_feedback(db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("resource_feedback")
        cursor = col.find({"clerk_user_id": clerk_user_id})
        return serialize_docs(await cursor.to_list(length=1000))
    else:
        if "resource_feedback" not in _DEMO_DB:
            _DEMO_DB["resource_feedback"] = []
        return serialize_docs([f for f in _DEMO_DB["resource_feedback"] if f.get("clerk_user_id") == clerk_user_id])


# --- Gamification Operations (User Isolated) ---

async def get_gamification(db: DatabaseManager, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("gamification")
        return serialize_doc(await col.find_one({"clerk_user_id": clerk_user_id}))
    else:
        return serialize_doc(_demo_get_by_id("gamification", clerk_user_id))

async def create_or_update_gamification(db: DatabaseManager, gamification: Gamification) -> Dict[str, Any]:
    g_dict = gamification.model_dump()
    if db.is_online:
        col = db.get_collection("gamification")
        await col.update_one(
            {"clerk_user_id": gamification.clerk_user_id},
            {"$set": g_dict},
            upsert=True
        )
        return serialize_doc(await col.find_one({"clerk_user_id": gamification.clerk_user_id}))
    else:
        existing = _demo_get_by_id("gamification", gamification.clerk_user_id)
        if existing:
            existing.update(g_dict)
            existing["updated_at"] = datetime.utcnow()
            return serialize_doc(existing)
        return serialize_doc(_demo_insert("gamification", g_dict))



# --- Learner Event Operations (User Isolated - Phase 13) ---

async def create_learner_event(db: DatabaseManager, event: LearnerEvent) -> Dict[str, Any]:
    e_dict = event.model_dump()
    if db.is_online:
        col = db.get_collection("learner_events")
        # Ensure indexes exist
        await col.create_index("clerk_user_id")
        await col.create_index("event_type")
        await col.create_index("timestamp")
        
        await col.insert_one(e_dict)
        return serialize_doc(e_dict)
    else:
        if "learner_events" not in _DEMO_DB:
            _DEMO_DB["learner_events"] = []
        return serialize_doc(_demo_insert("learner_events", e_dict))

async def get_learner_events(db: DatabaseManager, clerk_user_id: str, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("learner_events")
        query = {"clerk_user_id": clerk_user_id}
        if event_type:
            query["event_type"] = event_type
        cursor = col.find(query).sort("timestamp", -1)
        docs = await cursor.to_list(length=1000)
        return serialize_docs(docs)
    else:
        if "learner_events" not in _DEMO_DB:
            _DEMO_DB["learner_events"] = []
        events = [e for e in _DEMO_DB["learner_events"] if e.get("clerk_user_id") == clerk_user_id]
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        events.sort(key=lambda x: x.get("timestamp", datetime.utcnow()), reverse=True)
        return serialize_docs(events)

async def get_learner_analytics(db: DatabaseManager, clerk_user_id: str) -> Dict[str, Any]:
    if db.is_online:
        attempts_col = db.get_collection("attempts")
        cursor = attempts_col.find({"clerk_user_id": clerk_user_id}).sort("created_at", 1)
        attempts = await cursor.to_list(length=1000)
        
        mastery_col = db.get_collection("mastery")
        cursor_m = mastery_col.find({"clerk_user_id": clerk_user_id})
        mastery_records = await cursor_m.to_list(length=1000)
        
        events_col = db.get_collection("learner_events")
        cursor_e = events_col.find({"clerk_user_id": clerk_user_id}).sort("timestamp", 1)
        events = await cursor_e.to_list(length=1000)
    else:
        attempts = [a for a in _DEMO_DB.get("attempts", []) if a.get("clerk_user_id") == clerk_user_id]
        attempts.sort(key=lambda x: x.get("created_at", datetime.utcnow()))
        mastery_records = [m for m in _DEMO_DB.get("mastery", []) if m.get("clerk_user_id") == clerk_user_id]
        if "learner_events" not in _DEMO_DB:
            _DEMO_DB["learner_events"] = []
        events = [e for e in _DEMO_DB["learner_events"] if e.get("clerk_user_id") == clerk_user_id]
        events.sort(key=lambda x: x.get("timestamp", datetime.utcnow()))

    concept_stats = {}
    for att in attempts:
        c_name = att.get("concept_name", "Unknown")
        if c_name not in concept_stats:
            concept_stats[c_name] = {
                "attempts": 0,
                "correct": 0,
                "confidence_sum": 0,
                "speed_sum": 0
            }
        concept_stats[c_name]["attempts"] += 1
        if att.get("is_correct", False):
            concept_stats[c_name]["correct"] += 1
        concept_stats[c_name]["confidence_sum"] += att.get("confidence", 3)
        concept_stats[c_name]["speed_sum"] += att.get("response_time_seconds", 10.0)

    attempts_per_concept = {}
    accuracy_per_concept = {}
    for c_name, stats in concept_stats.items():
        attempts_per_concept[c_name] = stats["attempts"]
        accuracy_per_concept[c_name] = round((stats["correct"] / stats["attempts"]) * 100, 2)

    confidence_trends = []
    response_time_trends = []
    for att in attempts:
        t = att.get("created_at")
        timestamp_str = t.isoformat() if isinstance(t, datetime) else str(t)
        
        confidence_trends.append({
            "timestamp": timestamp_str,
            "confidence": att.get("confidence", 3),
            "concept_name": att.get("concept_name")
        })
        response_time_trends.append({
            "timestamp": timestamp_str,
            "response_time": att.get("response_time_seconds", 10.0),
            "concept_name": att.get("concept_name")
        })

    mastery_history = []
    for m in mastery_records:
        t = m.get("updated_at")
        updated_str = t.isoformat() if isinstance(t, datetime) else str(t)
        mastery_history.append({
            "concept_name": m.get("concept_name"),
            "mastery_score": m.get("mastery_score"),
            "kt_mastery_probability": m.get("kt_mastery_probability"),
            "active_model": m.get("active_mastery_model", "baseline"),
            "category": m.get("category"),
            "updated_at": updated_str
        })

    review_events = [e for e in events if e.get("event_type") == "concept_reviewed"]
    review_frequency = len(review_events)

    session_starts = [e for e in events if e.get("event_type") == "study_session_started"]
    session_completes = [e for e in events if e.get("event_type") == "study_session_completed"]
    study_session_behavior = {
        "started_count": len(session_starts),
        "completed_count": len(session_completes)
    }

    return {
        "attempts_per_concept": attempts_per_concept,
        "accuracy_per_concept": accuracy_per_concept,
        "confidence_trends": confidence_trends,
        "response_time_trends": response_time_trends,
        "review_frequency": review_frequency,
        "mastery_history": mastery_history,
        "study_session_behavior": study_session_behavior
    }


# ─── User Preferences ─────────────────────────────────────────────────────────

async def get_user_preferences(db, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("user_preferences")
        doc = await col.find_one({"clerk_user_id": clerk_user_id})
        return serialize_doc(doc)
    return next((d for d in _DEMO_DB.get("user_preferences", []) if d.get("clerk_user_id") == clerk_user_id), None)


async def upsert_user_preferences(db, prefs) -> Dict[str, Any]:
    data = prefs.model_dump()
    data["updated_at"] = datetime.utcnow()
    if db.is_online:
        col = db.get_collection("user_preferences")
        await col.update_one(
            {"clerk_user_id": data["clerk_user_id"]},
            {"$set": data},
            upsert=True
        )
        doc = await col.find_one({"clerk_user_id": data["clerk_user_id"]})
        return serialize_doc(doc)
    if "user_preferences" not in _DEMO_DB:
        _DEMO_DB["user_preferences"] = []
    existing = next((d for d in _DEMO_DB["user_preferences"] if d.get("clerk_user_id") == data["clerk_user_id"]), None)
    if existing:
        existing.update(data)
        return existing
    _DEMO_DB["user_preferences"].append(data)
    return data


async def get_user_profile(db, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    """Get user profile by clerk_user_id."""
    if db.is_online:
        col = db.get_collection("user_profiles")
        doc = await col.find_one({"clerk_user_id": clerk_user_id})
        return serialize_doc(doc)
    return next((d for d in _DEMO_DB.get("user_profiles", []) if d.get("clerk_user_id") == clerk_user_id), None)


# ─── Material Delete (Cascade) ────────────────────────────────────────────────

async def delete_material(db, material_id: str, clerk_user_id: str) -> bool:
    """Delete a material and cascade-delete all derived data (concepts, relationships, questions, attempts, mastery, flashcards, study_notes, tutor_sessions, podcasts, and chunks)."""
    if db.is_online:
        # Verify ownership
        col_mat = db.get_collection("materials")
        mat = await col_mat.find_one({"_id": ObjectId(material_id), "clerk_user_id": clerk_user_id})
        if not mat:
            return False
        # Find concepts derived from this material
        col_con = db.get_collection("concepts")
        concepts = await col_con.find({"material_id": material_id, "clerk_user_id": clerk_user_id}).to_list(None)
        concept_ids = [str(c["_id"]) for c in concepts]
        concept_names = [c["name"] for c in concepts]

        # Cascade delete across all collections
        await db.get_collection("material_chunks").delete_many({"material_id": material_id, "clerk_user_id": clerk_user_id})
        await db.get_collection("questions").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": {"$in": concept_ids}}, {"concept_name": {"$in": concept_names}}]
        })
        await db.get_collection("attempts").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": {"$in": concept_ids}}, {"concept_name": {"$in": concept_names}}]
        })
        await db.get_collection("mastery").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": {"$in": concept_ids}}, {"concept_name": {"$in": concept_names}}]
        })
        await db.get_collection("flashcards").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [
                {"material_id": material_id},
                {"concept_id": {"$in": concept_ids}},
                {"concept_name": {"$in": concept_names}}
            ]
        })
        await db.get_collection("study_notes").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [
                {"material_id": material_id},
                {"concept_id": {"$in": concept_ids}},
                {"concept_name": {"$in": concept_names}}
            ]
        })
        await db.get_collection("podcasts").delete_many({"material_id": material_id, "clerk_user_id": clerk_user_id})
        await db.get_collection("tutor_sessions").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": {"$in": concept_ids}}, {"concept_name": {"$in": concept_names}}]
        })
        await db.get_collection("assignments").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"source_material_ids": material_id}, {"concept_ids": {"$in": concept_ids}}]
        })
        await db.get_collection("relationships").delete_many({"material_id": material_id, "clerk_user_id": clerk_user_id})
        await col_con.delete_many({"material_id": material_id, "clerk_user_id": clerk_user_id})
        await col_mat.delete_one({"_id": ObjectId(material_id), "clerk_user_id": clerk_user_id})
        return True

    # Demo mode
    mat = next((d for d in _DEMO_DB.get("materials", []) if str(d.get("_id")) == material_id and d.get("clerk_user_id") == clerk_user_id), None)
    if not mat:
        return False
    concepts = [c for c in _DEMO_DB.get("concepts", []) if c.get("material_id") == material_id]
    concept_ids = [str(c["_id"]) for c in concepts]
    concept_names = [c.get("name") for c in concepts]

    for col in ["questions", "attempts", "mastery"]:
        _DEMO_DB[col] = [d for d in _DEMO_DB.get(col, []) if d.get("concept_id") not in concept_ids and d.get("concept_name") not in concept_names]
    
    _DEMO_DB["flashcards"] = [
        d for d in _DEMO_DB.get("flashcards", [])
        if d.get("material_id") != material_id and d.get("concept_id") not in concept_ids and d.get("concept_name") not in concept_names
    ]
    _DEMO_DB["study_notes"] = [
        d for d in _DEMO_DB.get("study_notes", [])
        if d.get("material_id") != material_id and d.get("concept_id") not in concept_ids and d.get("concept_name") not in concept_names
    ]
    _DEMO_DB["podcasts"] = [d for d in _DEMO_DB.get("podcasts", []) if d.get("material_id") != material_id]
    _DEMO_DB["tutor_sessions"] = [
        d for d in _DEMO_DB.get("tutor_sessions", [])
        if d.get("concept_id") not in concept_ids and d.get("concept_name") not in concept_names
    ]
    _DEMO_DB["relationships"] = [d for d in _DEMO_DB.get("relationships", []) if d.get("material_id") != material_id]
    _DEMO_DB["concepts"] = [d for d in _DEMO_DB.get("concepts", []) if d.get("material_id") != material_id]
    _DEMO_DB["materials"] = [d for d in _DEMO_DB.get("materials", []) if str(d.get("_id")) != material_id]
    return True


# ─── Concept Delete (Cascade) ─────────────────────────────────────────────────

async def delete_concept(db, concept_id: str, clerk_user_id: str) -> bool:
    """Delete a concept and cascade-delete questions, attempts, mastery, flashcards, and notes for it."""
    if db.is_online:
        col_con = db.get_collection("concepts")
        con = await col_con.find_one({"_id": ObjectId(concept_id), "clerk_user_id": clerk_user_id})
        if not con:
            return False
        concept_name = con.get("name", "")
        await db.get_collection("questions").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": concept_id}, {"concept_name": concept_name}]
        })
        await db.get_collection("attempts").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": concept_id}, {"concept_name": concept_name}]
        })
        await db.get_collection("mastery").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": concept_id}, {"concept_name": concept_name}]
        })
        await db.get_collection("flashcards").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": concept_id}, {"concept_name": concept_name}]
        })
        await db.get_collection("study_notes").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": concept_id}, {"concept_name": concept_name}]
        })
        await db.get_collection("tutor_sessions").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"concept_id": concept_id}, {"concept_name": concept_name}]
        })
        await db.get_collection("relationships").delete_many({
            "clerk_user_id": clerk_user_id,
            "$or": [{"source_concept_name": concept_name}, {"target_concept_name": concept_name}]
        })
        await col_con.delete_one({"_id": ObjectId(concept_id), "clerk_user_id": clerk_user_id})
        return True

    # Demo mode
    con = next((d for d in _DEMO_DB.get("concepts", []) if str(d.get("_id")) == concept_id and d.get("clerk_user_id") == clerk_user_id), None)
    if not con:
        return False
    concept_name = con.get("name", "")
    for col in ["questions", "attempts", "mastery"]:
        _DEMO_DB[col] = [d for d in _DEMO_DB.get(col, []) if d.get("concept_id") != concept_id and d.get("concept_name") != concept_name]
    _DEMO_DB["flashcards"] = [d for d in _DEMO_DB.get("flashcards", []) if d.get("concept_id") != concept_id and d.get("concept_name") != concept_name]
    _DEMO_DB["study_notes"] = [d for d in _DEMO_DB.get("study_notes", []) if d.get("concept_id") != concept_id and d.get("concept_name") != concept_name]
    _DEMO_DB["tutor_sessions"] = [d for d in _DEMO_DB.get("tutor_sessions", []) if d.get("concept_id") != concept_id and d.get("concept_name") != concept_name]
    _DEMO_DB["relationships"] = [d for d in _DEMO_DB.get("relationships", []) if d.get("source_concept_name") != concept_name and d.get("target_concept_name") != concept_name]
    _DEMO_DB["concepts"] = [d for d in _DEMO_DB.get("concepts", []) if str(d.get("_id")) != concept_id]
    return True


# ─── Data Clearing ────────────────────────────────────────────────────────────

async def clear_user_data(db, clerk_user_id: str, category: str) -> Dict[str, Any]:
    """
    Clear a category of authenticated user data.
    category: 'assessments' | 'gamification' | 'materials' | 'concepts' | 'flashcards' | 'study_notes' | 'podcasts' | 'tutor' | 'assignments' | 'study_paths' | 'resources' | 'all'
    Never touches Clerk account or another user's data.
    """
    cleared = []
    if db.is_online:
        async def _del(collection: str, extra_filter: dict = {}):
            col = db.get_collection(collection)
            result = await col.delete_many({"clerk_user_id": clerk_user_id, **extra_filter})
            cleared.append(f"{collection}: {result.deleted_count} removed")

        if category in ("assessments", "all"):
            await _del("attempts")
        if category in ("gamification", "all"):
            col = db.get_collection("gamification")
            await col.update_one({"clerk_user_id": clerk_user_id}, {"$set": {"xp": 0, "level": 1, "level_name": "Beginner", "achievements": []}})
            cleared.append("gamification: reset")
            await _del("learner_events")
        if category in ("materials", "all"):
            await _del("materials")
            await _del("material_chunks")
            await _del("concepts")
            await _del("relationships")
            await _del("questions")
            await _del("attempts")
            await _del("mastery")
            await _del("flashcards")
            await _del("study_notes")
            await _del("podcasts")
            await _del("tutor_sessions")
            await _del("assignments")
            await _del("study_paths")
        if category in ("concepts", "all"):
            await _del("concepts")
            await _del("relationships")
            await _del("questions")
            await _del("mastery")
            await _del("flashcards")
            await _del("study_notes")
        if category in ("flashcards", "all"):
            await _del("flashcards")
        if category in ("study_notes", "all"):
            await _del("study_notes")
        if category in ("podcasts", "all"):
            await _del("podcasts")
        if category in ("tutor", "all"):
            await _del("tutor_sessions")
        if category in ("assignments", "all"):
            await _del("assignments")
        if category in ("study_paths", "all"):
            await _del("study_paths")
        if category in ("resources", "all"):
            await _del("resource_feedback")
        return {"cleared": cleared}

    # Demo mode
    if category in ("assessments", "all"):
        _DEMO_DB["attempts"] = [d for d in _DEMO_DB.get("attempts", []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("attempts cleared")
    if category in ("gamification", "all"):
        for g in _DEMO_DB.get("gamification", []):
            if g.get("clerk_user_id") == clerk_user_id:
                g.update({"xp": 0, "level": 1, "level_name": "Beginner", "achievements": []})
        cleared.append("gamification reset")
    if category in ("materials", "all"):
        for col in ["materials", "concepts", "relationships", "questions", "attempts", "mastery", "flashcards", "study_notes", "podcasts", "tutor_sessions", "assignments", "study_paths"]:
            _DEMO_DB[col] = [d for d in _DEMO_DB.get(col, []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("all learning data cleared")
    if category in ("concepts", "all"):
        for col in ["concepts", "relationships", "questions", "mastery", "flashcards", "study_notes"]:
            _DEMO_DB[col] = [d for d in _DEMO_DB.get(col, []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("concepts cleared")
    if category in ("flashcards", "all"):
        _DEMO_DB["flashcards"] = [d for d in _DEMO_DB.get("flashcards", []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("flashcards cleared")
    if category in ("study_notes", "all"):
        _DEMO_DB["study_notes"] = [d for d in _DEMO_DB.get("study_notes", []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("study notes cleared")
    if category in ("podcasts", "all"):
        _DEMO_DB["podcasts"] = [d for d in _DEMO_DB.get("podcasts", []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("podcasts cleared")
    if category in ("tutor", "all"):
        _DEMO_DB["tutor_sessions"] = [d for d in _DEMO_DB.get("tutor_sessions", []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("tutor sessions cleared")
    if category in ("assignments", "all"):
        _DEMO_DB["assignments"] = [d for d in _DEMO_DB.get("assignments", []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("assignments cleared")
    if category in ("study_paths", "all"):
        _DEMO_DB["study_paths"] = [d for d in _DEMO_DB.get("study_paths", []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("study paths cleared")
    if category in ("resources", "all"):
        _DEMO_DB["resource_feedback"] = [d for d in _DEMO_DB.get("resource_feedback", []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("resource feedback cleared")
    return {"cleared": cleared}


# ─── Global Search ────────────────────────────────────────────────────────────

async def search_user_data(db, clerk_user_id: str, query: str) -> Dict[str, Any]:
    """Search across the authenticated user's materials, concepts, questions, assignments, resources, study paths, and activity."""
    q = query.lower().strip()
    results = {
        "materials": [], 
        "concepts": [], 
        "questions": [], 
        "assignments": [],
        "resources": [],
        "study_paths": [],
        "activity": []
    }

    def _text_match(doc: dict, fields: list) -> bool:
        return any(q in str(doc.get(f, "")).lower() for f in fields)

    if db.is_online:
        # Materials
        col = db.get_collection("materials")
        async for doc in col.find({"clerk_user_id": clerk_user_id, "$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"raw_text": {"$regex": query, "$options": "i"}}
        ]}).limit(10):
            results["materials"].append(serialize_doc(doc))
        # Concepts
        col = db.get_collection("concepts")
        async for doc in col.find({"clerk_user_id": clerk_user_id, "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]}).limit(15):
            results["concepts"].append(serialize_doc(doc))
        # Questions
        col = db.get_collection("questions")
        async for doc in col.find({"clerk_user_id": clerk_user_id, "$or": [
            {"question_text": {"$regex": query, "$options": "i"}},
            {"concept_name": {"$regex": query, "$options": "i"}}
        ]}).limit(10):
            results["questions"].append(serialize_doc(doc))
        # Assignments
        col = db.get_collection("assignments")
        async for doc in col.find({"clerk_user_id": clerk_user_id, "$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
            {"concept_names": {"$in": [query]}}
        ]}).limit(10):
            results["assignments"].append(serialize_doc(doc))
        # Resources
        col = db.get_collection("resources")
        async for doc in col.find({"$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"concept_name": {"$regex": query, "$options": "i"}}
        ]}).limit(10):
            results["resources"].append(serialize_doc(doc))
        # Study Paths
        col = db.get_collection("study_paths")
        async for doc in col.find({"clerk_user_id": clerk_user_id, "$or": [
            {"ordered_concepts.concept_name": {"$regex": query, "$options": "i"}},
            {"ordered_concepts.reason": {"$regex": query, "$options": "i"}}
        ]}).limit(5):
            results["study_paths"].append(serialize_doc(doc))
        # Activity
        col = db.get_collection("user_activity")
        async for doc in col.find({"clerk_user_id": clerk_user_id, "$or": [
            {"event_type": {"$regex": query, "$options": "i"}},
            {"entity_type": {"$regex": query, "$options": "i"}}
        ]}).sort("timestamp", -1).limit(10):
            results["activity"].append(serialize_doc(doc))
    else:
        # Demo mode – in-memory search
        results["materials"] = [serialize_doc(d) for d in _DEMO_DB.get("materials", [])
                                 if d.get("clerk_user_id") == clerk_user_id and _text_match(d, ["title", "raw_text"])][:10]
        results["concepts"] = [serialize_doc(d) for d in _DEMO_DB.get("concepts", [])
                                if d.get("clerk_user_id") == clerk_user_id and _text_match(d, ["name", "description"])][:15]
        results["questions"] = [serialize_doc(d) for d in _DEMO_DB.get("questions", [])
                                 if d.get("clerk_user_id") == clerk_user_id and _text_match(d, ["question_text", "concept_name"])][:10]
        results["assignments"] = [serialize_doc(d) for d in _DEMO_DB.get("assignments", [])
                                   if d.get("clerk_user_id") == clerk_user_id and _text_match(d, ["title", "description"])][:10]
        results["resources"] = [serialize_doc(d) for d in _DEMO_DB.get("resources", [])
                                 if _text_match(d, ["title", "concept_name"])][:10]
        results["study_paths"] = [serialize_doc(d) for d in _DEMO_DB.get("study_paths", [])
                                   if d.get("clerk_user_id") == clerk_user_id][:5]
        results["activity"] = [serialize_doc(d) for d in _DEMO_DB.get("user_activity", [])
                                if d.get("clerk_user_id") == clerk_user_id and _text_match(d, ["event_type", "entity_type"])][:10]
    return results


# ─── Assignments CRUD ─────────────────────────────────────────────────────────

async def get_assignments(db, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("assignments")
        docs = await col.find({"clerk_user_id": clerk_user_id}).sort("created_at", -1).to_list(None)
        return serialize_docs(docs)
    return serialize_docs([d for d in _DEMO_DB.get("assignments", []) if d.get("clerk_user_id") == clerk_user_id])


async def get_assignment(db, assignment_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("assignments")
        doc = await col.find_one({"_id": ObjectId(assignment_id), "clerk_user_id": clerk_user_id})
        return serialize_doc(doc)
    return serialize_doc(next((d for d in _DEMO_DB.get("assignments", [])
                               if str(d.get("_id")) == assignment_id and d.get("clerk_user_id") == clerk_user_id), None))


async def create_assignment(db, assignment) -> Dict[str, Any]:
    data = assignment.model_dump()
    data["updated_at"] = datetime.utcnow()
    if db.is_online:
        col = db.get_collection("assignments")
        result = await col.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data
    return _demo_insert("assignments", data)


async def update_assignment(db, assignment_id: str, clerk_user_id: str, updates: dict) -> Optional[Dict[str, Any]]:
    updates["updated_at"] = datetime.utcnow()
    if db.is_online:
        col = db.get_collection("assignments")
        result = await col.find_one_and_update(
            {"_id": ObjectId(assignment_id), "clerk_user_id": clerk_user_id},
            {"$set": updates},
            return_document=True
        )
        return serialize_doc(result)
    target = next((d for d in _DEMO_DB.get("assignments", [])
                   if str(d.get("_id")) == assignment_id and d.get("clerk_user_id") == clerk_user_id), None)
    if target:
        target.update(updates)
    return serialize_doc(target)


async def delete_assignment(db, assignment_id: str, clerk_user_id: str) -> bool:
    if db.is_online:
        col = db.get_collection("assignments")
        result = await col.delete_one({"_id": ObjectId(assignment_id), "clerk_user_id": clerk_user_id})
        return result.deleted_count > 0
    before = len(_DEMO_DB.get("assignments", []))
    _DEMO_DB["assignments"] = [d for d in _DEMO_DB.get("assignments", [])
                                if not (str(d.get("_id")) == assignment_id and d.get("clerk_user_id") == clerk_user_id)]
    return len(_DEMO_DB.get("assignments", [])) < before


# ─── Material Chunks and Vector Search (RAG) ─────────────────────────────────

async def save_material_chunks(db, material_id: str, chunks_data: List[Dict[str, Any]]) -> bool:
    if not chunks_data:
        return True
    
    # Ensure all canonical fields are present
    for c in chunks_data:
        c["material_id"] = str(material_id)
        if "created_at" not in c or not c["created_at"]:
            c["created_at"] = datetime.utcnow()
    
    if db.is_online:
        col = db.get_collection("material_chunks")
        await col.insert_many(chunks_data)
        return True
    
    for c in chunks_data:
        _demo_insert("material_chunks", c)
    return True

async def get_material_chunks(db, material_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("material_chunks")
        docs = await col.find({"material_id": str(material_id)}).to_list(None)
        return serialize_docs(docs)
    return serialize_docs([d for d in _DEMO_DB.get("material_chunks", []) if str(d.get("material_id")) == str(material_id)])

async def TEMPORARY_VECTOR_SEARCH_FALLBACK(db, clerk_user_id: str, query_embedding: List[float], top_k: int = 5, min_similarity: float = 0.5, material_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """In-memory cosine similarity retrieval for RAG chunks, enforcing strict user ownership and optional material scoping."""
    if not query_embedding:
        return []
        
    all_chunks = []
    query_filter: Dict[str, Any] = {"clerk_user_id": clerk_user_id}
    if material_id:
        query_filter["material_id"] = str(material_id)

    if db.is_online:
        col = db.get_collection("material_chunks")
        all_chunks = await col.find(query_filter).to_list(None)
    else:
        all_chunks = [
            d for d in _DEMO_DB.get("material_chunks", []) 
            if d.get("clerk_user_id") == clerk_user_id and (not material_id or str(d.get("material_id")) == str(material_id))
        ]
    
    def cosine_similarity(v1, v2):
        if not v1 or not v2 or len(v1) != len(v2): return 0.0
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_v1 = math.sqrt(sum(a * a for a in v1))
        norm_v2 = math.sqrt(sum(b * b for b in v2))
        if norm_v1 == 0 or norm_v2 == 0: return 0.0
        return dot_product / (norm_v1 * norm_v2)

    scored_chunks = []
    for chunk in all_chunks:
        emb = chunk.get("embedding", [])
        score = cosine_similarity(query_embedding, emb)
        if score >= min_similarity:
            chunk_copy = dict(chunk)
            chunk_copy["similarity_score"] = score
            scored_chunks.append((score, chunk_copy))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [serialize_doc(chunk) for score, chunk in scored_chunks[:top_k]]


# ─── User Activity Logging ────────────────────────────────────────────────────

async def log_user_activity(db, clerk_user_id: str, event_type: str, entity_type: str = None, entity_id: str = None, session_id: str = None, metadata: dict = None) -> bool:
    """Track user activity for context and personalization."""
    activity = {
        "event_id": str(ObjectId()),
        "clerk_user_id": clerk_user_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "session_id": session_id,
        "metadata": metadata or {},
        "timestamp": datetime.utcnow()
    }
    if db.is_online:
        col = db.get_collection("user_activity")
        await col.insert_one(activity)
        return True
    _demo_insert("user_activity", activity)
    return True


# ─── Spaced Repetition Flashcard CRUD ─────────────────────────────────────────

async def create_flashcards(db, flashcards: List[Flashcard]) -> List[Dict[str, Any]]:
    """Bulk create flashcards for a user."""
    docs = [f.model_dump() for f in flashcards]
    for d in docs:
        d["created_at"] = d.get("created_at") or datetime.utcnow()
        d["updated_at"] = d.get("updated_at") or datetime.utcnow()
    
    if db.is_online:
        col = db.get_collection("flashcards")
        result = await col.insert_many(docs)
        for idx, inserted_id in enumerate(result.inserted_ids):
            docs[idx]["_id"] = inserted_id
        return serialize_docs(docs)
    
    for d in docs:
        _demo_insert("flashcards", d)
    return serialize_docs(docs)

async def get_flashcards(db, clerk_user_id: str, concept_id: str = None, material_id: str = None, state: str = None) -> List[Dict[str, Any]]:
    """Retrieve flashcards with optional filtering."""
    query: Dict[str, Any] = {"clerk_user_id": clerk_user_id}
    if concept_id:
        query["concept_id"] = concept_id
    if material_id:
        query["material_id"] = material_id
    if state:
        query["state"] = state
        
    if db.is_online:
        col = db.get_collection("flashcards")
        cursor = col.find(query).sort("created_at", -1)
        cards = await cursor.to_list(length=500)
        return serialize_docs(cards)
    
    results = [
        d for d in _DEMO_DB.get("flashcards", [])
        if d.get("clerk_user_id") == clerk_user_id
        and (not concept_id or d.get("concept_id") == concept_id)
        and (not material_id or d.get("material_id") == material_id)
        and (not state or d.get("state") == state)
    ]
    return serialize_docs(results)

async def get_flashcard(db, card_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single flashcard by ID."""
    if db.is_online:
        col = db.get_collection("flashcards")
        try:
            doc = await col.find_one({"_id": ObjectId(card_id), "clerk_user_id": clerk_user_id})
            return serialize_doc(doc)
        except Exception:
            return None
    doc = _demo_find_one("flashcards", {"_id": card_id, "clerk_user_id": clerk_user_id})
    return serialize_doc(doc)

async def update_flashcard(db, card_id: str, clerk_user_id: str, updates: Dict[str, Any]) -> bool:
    """Update review parameters and state of a flashcard."""
    updates["updated_at"] = datetime.utcnow()
    if db.is_online:
        col = db.get_collection("flashcards")
        try:
            res = await col.update_one(
                {"_id": ObjectId(card_id), "clerk_user_id": clerk_user_id},
                {"$set": updates}
            )
            return res.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating flashcard {card_id}: {e}")
            return False
            
    doc = _demo_find_one("flashcards", {"_id": card_id, "clerk_user_id": clerk_user_id})
    if doc:
        doc.update(updates)
        return True
    return False

async def delete_flashcard(db, card_id: str, clerk_user_id: str) -> bool:
    """Delete a flashcard by ID."""
    if db.is_online:
        col = db.get_collection("flashcards")
        try:
            res = await col.delete_one({"_id": ObjectId(card_id), "clerk_user_id": clerk_user_id})
            return res.deleted_count > 0
        except Exception:
            return False
            
    cards = _DEMO_DB.get("flashcards", [])
    before_len = len(cards)
    _DEMO_DB["flashcards"] = [c for c in cards if not (str(c.get("_id")) == card_id and c.get("clerk_user_id") == clerk_user_id)]
    return len(_DEMO_DB["flashcards"]) < before_len

async def get_due_flashcards(db, clerk_user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve flashcards that are due for spaced repetition review today."""
    now = datetime.utcnow()
    if db.is_online:
        col = db.get_collection("flashcards")
        query = {
            "clerk_user_id": clerk_user_id,
            "next_review_at": {"$lte": now}
        }
        cursor = col.find(query).sort("next_review_at", 1).limit(limit)
        cards = await cursor.to_list(length=limit)
        return serialize_docs(cards)
        
    results = [
        d for d in _DEMO_DB.get("flashcards", [])
        if d.get("clerk_user_id") == clerk_user_id
        and (d.get("next_review_at", now) <= now or d.get("state") == "new")
    ]
    results.sort(key=lambda x: x.get("next_review_at", now))
    return serialize_docs(results[:limit])


# --- Study Notes & Mind-Maps CRUD ---

async def create_study_notes(db, notes: List[StudyNote]) -> List[Dict[str, Any]]:
    """Persist generated study notes with mind-maps."""
    docs = [n.model_dump() for n in notes]
    for d in docs:
        d["created_at"] = datetime.utcnow()
        d["updated_at"] = datetime.utcnow()
        
    if db.is_online:
        col = db.get_collection("study_notes")
        res = await col.insert_many(docs)
        for d, inserted_id in zip(docs, res.inserted_ids):
            d["_id"] = inserted_id
        return serialize_docs(docs)
        
    for d in docs:
        d["_id"] = ObjectId()
        _DEMO_DB["study_notes"].append(d)
    return serialize_docs(docs)

async def get_study_notes(db, clerk_user_id: str, concept_id: Optional[str] = None, material_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve user study notes with optional concept or material filtering."""
    if db.is_online:
        col = db.get_collection("study_notes")
        query: Dict[str, Any] = {"clerk_user_id": clerk_user_id}
        if concept_id:
            query["concept_id"] = concept_id
        if material_id:
            query["material_id"] = material_id
        cursor = col.find(query).sort("created_at", -1)
        notes = await cursor.to_list(length=200)
        return serialize_docs(notes)
        
    results = [
        d for d in _DEMO_DB.get("study_notes", [])
        if d.get("clerk_user_id") == clerk_user_id
        and (not concept_id or d.get("concept_id") == concept_id)
        and (not material_id or d.get("material_id") == material_id)
    ]
    results.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    return serialize_docs(results)

async def get_study_note(db, note_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single study note by ID."""
    if db.is_online:
        col = db.get_collection("study_notes")
        try:
            doc = await col.find_one({"_id": ObjectId(note_id), "clerk_user_id": clerk_user_id})
            return serialize_doc(doc)
        except Exception:
            return None
            
    for d in _DEMO_DB.get("study_notes", []):
        if str(d.get("_id")) == note_id and d.get("clerk_user_id") == clerk_user_id:
            return serialize_doc(d)
    return None

async def delete_study_note(db, note_id: str, clerk_user_id: str) -> bool:
    """Delete a study note by ID."""
    if db.is_online:
        col = db.get_collection("study_notes")
        try:
            res = await col.delete_one({"_id": ObjectId(note_id), "clerk_user_id": clerk_user_id})
            return res.deleted_count > 0
        except Exception:
            return False
            
    notes = _DEMO_DB.get("study_notes", [])
    before_len = len(notes)
    _DEMO_DB["study_notes"] = [n for n in notes if not (str(n.get("_id")) == note_id and n.get("clerk_user_id") == clerk_user_id)]
    return len(_DEMO_DB["study_notes"]) < before_len


# --- Socratic AI Tutor CRUD ---

async def create_tutor_session(db, session: TutorSession) -> Dict[str, Any]:
    """Create a new Socratic tutor session."""
    doc = session.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    
    if db.is_online:
        col = db.get_collection("tutor_sessions")
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return serialize_doc(doc)
        
    doc["_id"] = ObjectId()
    _DEMO_DB["tutor_sessions"].append(doc)
    return serialize_doc(doc)

async def get_tutor_sessions(db, clerk_user_id: str, concept_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all tutor sessions for the learner."""
    if db.is_online:
        col = db.get_collection("tutor_sessions")
        query: Dict[str, Any] = {"clerk_user_id": clerk_user_id}
        if concept_id:
            query["concept_id"] = concept_id
        cursor = col.find(query).sort("updated_at", -1)
        sessions = await cursor.to_list(length=50)
        return serialize_docs(sessions)
        
    results = [
        s for s in _DEMO_DB.get("tutor_sessions", [])
        if s.get("clerk_user_id") == clerk_user_id
        and (not concept_id or s.get("concept_id") == concept_id)
    ]
    results.sort(key=lambda x: x.get("updated_at", datetime.min), reverse=True)
    return serialize_docs(results)

async def get_tutor_session(db, session_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single tutor session by ID."""
    if db.is_online:
        col = db.get_collection("tutor_sessions")
        try:
            doc = await col.find_one({"_id": ObjectId(session_id), "clerk_user_id": clerk_user_id})
            return serialize_doc(doc)
        except Exception:
            return None
            
    for s in _DEMO_DB.get("tutor_sessions", []):
        if str(s.get("_id")) == session_id and s.get("clerk_user_id") == clerk_user_id:
            return serialize_doc(s)
    return None

async def append_tutor_message(db, session_id: str, clerk_user_id: str, message: TutorChatMessage) -> Optional[Dict[str, Any]]:
    """Append a user or assistant message to an active tutoring session."""
    msg_dict = message.model_dump()
    now = datetime.utcnow()
    
    if db.is_online:
        col = db.get_collection("tutor_sessions")
        try:
            res = await col.find_one_and_update(
                {"_id": ObjectId(session_id), "clerk_user_id": clerk_user_id},
                {"$push": {"messages": msg_dict}, "$set": {"updated_at": now}},
                return_document=True
            )
            return serialize_doc(res)
        except Exception as e:
            logger.error(f"Error appending tutor message: {e}")
            return None
            
    for s in _DEMO_DB.get("tutor_sessions", []):
        if str(s.get("_id")) == session_id and s.get("clerk_user_id") == clerk_user_id:
            s.setdefault("messages", []).append(msg_dict)
            s["updated_at"] = now
            return serialize_doc(s)
    return None

async def delete_tutor_session(db, session_id: str, clerk_user_id: str) -> bool:
    """Delete a tutor conversation session."""
    if db.is_online:
        col = db.get_collection("tutor_sessions")
        try:
            res = await col.delete_one({"_id": ObjectId(session_id), "clerk_user_id": clerk_user_id})
            return res.deleted_count > 0
        except Exception:
            return False
            
    sessions = _DEMO_DB.get("tutor_sessions", [])
    before_len = len(sessions)
    _DEMO_DB["tutor_sessions"] = [s for s in sessions if not (str(s.get("_id")) == session_id and s.get("clerk_user_id") == clerk_user_id)]
    return len(_DEMO_DB["tutor_sessions"]) < before_len


# --- Multi-Speaker Podcast Overviews CRUD ---

async def create_podcast(db, podcast: PodcastOverview) -> Dict[str, Any]:
    """Save an AI-synthesized two-host audio podcast overview."""
    doc = podcast.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    
    if db.is_online:
        col = db.get_collection("podcasts")
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return serialize_doc(doc)
        
    doc["_id"] = ObjectId()
    _DEMO_DB["podcasts"].append(doc)
    return serialize_doc(doc)

async def get_podcasts(db, clerk_user_id: str, material_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all synthesized audio podcasts for a learner."""
    if db.is_online:
        col = db.get_collection("podcasts")
        query: Dict[str, Any] = {"clerk_user_id": clerk_user_id}
        if material_id:
            query["material_id"] = material_id
        cursor = col.find(query).sort("created_at", -1)
        podcasts = await cursor.to_list(length=50)
        return serialize_docs(podcasts)
        
    results = [
        p for p in _DEMO_DB.get("podcasts", [])
        if p.get("clerk_user_id") == clerk_user_id
        and (not material_id or p.get("material_id") == material_id)
    ]
    results.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    return serialize_docs(results)

async def get_podcast(db, podcast_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single audio podcast episode by ID."""
    if db.is_online:
        col = db.get_collection("podcasts")
        try:
            doc = await col.find_one({"_id": ObjectId(podcast_id), "clerk_user_id": clerk_user_id})
            return serialize_doc(doc)
        except Exception:
            return None
            
    for p in _DEMO_DB.get("podcasts", []):
        if str(p.get("_id")) == podcast_id and p.get("clerk_user_id") == clerk_user_id:
            return serialize_doc(p)
    return None

async def delete_podcast(db, podcast_id: str, clerk_user_id: str) -> bool:
    """Delete a synthesized podcast episode."""
    if db.is_online:
        col = db.get_collection("podcasts")
        try:
            res = await col.delete_one({"_id": ObjectId(podcast_id), "clerk_user_id": clerk_user_id})
            return res.deleted_count > 0
        except Exception:
            return False
            
    before = len(_DEMO_DB.get("podcasts", []))
    _DEMO_DB["podcasts"] = [
        p for p in _DEMO_DB.get("podcasts", [])
        if not (str(p.get("_id")) == podcast_id and p.get("clerk_user_id") == clerk_user_id)
    ]
    return len(_DEMO_DB.get("podcasts", [])) < before


# ─── Goals CRUD ──────────────────────────────────────────────────────────────

async def create_goal(db: DatabaseManager, goal) -> Dict[str, Any]:
    doc = goal.model_dump()
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    
    if db.is_online:
        col = db.get_collection("goals")
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return serialize_doc(doc)
        
    doc["_id"] = ObjectId()
    if "goals" not in _DEMO_DB:
        _DEMO_DB["goals"] = []
    _DEMO_DB["goals"].append(doc)
    return serialize_doc(doc)

async def get_goals(db: DatabaseManager, clerk_user_id: str) -> List[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("goals")
        cursor = col.find({"clerk_user_id": clerk_user_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=100)
        return serialize_docs(docs)
        
    results = [g for g in _DEMO_DB.get("goals", []) if g.get("clerk_user_id") == clerk_user_id]
    results.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)
    return serialize_docs(results)

async def get_goal(db: DatabaseManager, goal_id: str, clerk_user_id: str) -> Optional[Dict[str, Any]]:
    if db.is_online:
        col = db.get_collection("goals")
        try:
            doc = await col.find_one({"_id": ObjectId(goal_id), "clerk_user_id": clerk_user_id})
            return serialize_doc(doc)
        except Exception:
            return None
            
    for g in _DEMO_DB.get("goals", []):
        if str(g.get("_id")) == goal_id and g.get("clerk_user_id") == clerk_user_id:
            return serialize_doc(g)
    return None

async def update_goal(db: DatabaseManager, goal_id: str, clerk_user_id: str, update_fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    update_fields.pop("_id", None)
    update_fields.pop("clerk_user_id", None)
    update_fields["updated_at"] = datetime.utcnow()
    
    if db.is_online:
        col = db.get_collection("goals")
        try:
            res = await col.update_one(
                {"_id": ObjectId(goal_id), "clerk_user_id": clerk_user_id},
                {"$set": update_fields}
            )
            if res.matched_count > 0:
                return await get_goal(db, goal_id, clerk_user_id)
            return None
        except Exception:
            return None
            
    for g in _DEMO_DB.get("goals", []):
        if str(g.get("_id")) == goal_id and g.get("clerk_user_id") == clerk_user_id:
            g.update(update_fields)
            return serialize_doc(g)
    return None

async def delete_goal(db: DatabaseManager, goal_id: str, clerk_user_id: str) -> bool:
    if db.is_online:
        col = db.get_collection("goals")
        try:
            res = await col.delete_one({"_id": ObjectId(goal_id), "clerk_user_id": clerk_user_id})
            return res.deleted_count > 0
        except Exception:
            return False
            
    before = len(_DEMO_DB.get("goals", []))
    _DEMO_DB["goals"] = [
        g for g in _DEMO_DB.get("goals", [])
        if not (str(g.get("_id")) == goal_id and g.get("clerk_user_id") == clerk_user_id)
    ]
    return len(_DEMO_DB.get("goals", [])) < before


# ─── Learning Diagnosis CRUD (Phase 27) ──────────────────────────────────────

async def create_diagnosis(db: DatabaseManager, diagnosis) -> Dict[str, Any]:
    doc = diagnosis.model_dump()
    doc["timestamp"] = doc.get("timestamp") or datetime.utcnow()
    
    if db.is_online:
        col = db.get_collection("learning_diagnoses")
        res = await col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return serialize_doc(doc)
        
    doc["_id"] = ObjectId()
    if "learning_diagnoses" not in _DEMO_DB:
        _DEMO_DB["learning_diagnoses"] = []
    _DEMO_DB["learning_diagnoses"].append(doc)
    return serialize_doc(doc)

async def get_diagnoses(db: DatabaseManager, clerk_user_id: str, concept_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {"clerk_user_id": clerk_user_id}
    if concept_id:
        query["concept_id"] = concept_id
        
    if db.is_online:
        col = db.get_collection("learning_diagnoses")
        cursor = col.find(query).sort("timestamp", -1)
        docs = await cursor.to_list(length=200)
        return serialize_docs(docs)
        
    results = [
        d for d in _DEMO_DB.get("learning_diagnoses", [])
        if d.get("clerk_user_id") == clerk_user_id
        and (not concept_id or d.get("concept_id") == concept_id or d.get("target_concept") == concept_id)
    ]
    results.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
    return serialize_docs(results)

async def create_material_chunks(db: DatabaseManager, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not chunks:
        return []
    if db.is_online:
        col = db.get_collection("material_chunks")
        res = await col.insert_many(chunks)
        cursor = col.find({"_id": {"$in": res.inserted_ids}})
        return serialize_docs(await cursor.to_list(length=len(res.inserted_ids)))
    else:
        if "material_chunks" not in _DEMO_DB:
            _DEMO_DB["material_chunks"] = []
        inserted = []
        for c in chunks:
            if "_id" not in c:
                c["_id"] = ObjectId()
            _DEMO_DB["material_chunks"].append(c)
            inserted.append(serialize_doc(c))
        return inserted

async def get_material_chunks(db: DatabaseManager, material_id: str, clerk_user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {"material_id": str(material_id)}
    if clerk_user_id:
        query["clerk_user_id"] = clerk_user_id

    if db.is_online:
        col = db.get_collection("material_chunks")
        cursor = col.find(query).sort("chunk_index", 1)
        return serialize_docs(await cursor.to_list(length=500))
    else:
        if "material_chunks" not in _DEMO_DB:
            _DEMO_DB["material_chunks"] = []
        chunks = [
            c for c in _DEMO_DB["material_chunks"] 
            if str(c.get("material_id")) == str(material_id)
            and (not clerk_user_id or c.get("clerk_user_id") == clerk_user_id)
        ]
        chunks.sort(key=lambda x: x.get("chunk_index", 0))
        return serialize_docs(chunks)

