import logging
from datetime import datetime
from bson import ObjectId
from typing import List, Optional, Dict, Any
from .models import UserProfile, Material, Concept, Relationship, Question, Attempt, Mastery, StudyPath, Resource, Gamification, LearnerEvent, ResourceFeedback, MaterialChunk, UserActivity
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

async def delete_material(db: DatabaseManager, material_id: str, clerk_user_id: str) -> bool:
    try:
        obj_id = ObjectId(material_id)
    except Exception:
        return False

    if db.is_online:
        col = db.get_collection("materials")
        # Enforce clerk_user_id scoping on delete
        res = await col.delete_one({"_id": obj_id, "clerk_user_id": clerk_user_id})
        return res.deleted_count > 0
    else:
        return _demo_delete("materials", material_id, clerk_user_id)


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
    """Delete a material and cascade-delete all derived data (concepts, relationships, questions, attempts, mastery)."""
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
        # Cascade delete
        await db.get_collection("questions").delete_many({"concept_id": {"$in": concept_ids}, "clerk_user_id": clerk_user_id})
        await db.get_collection("attempts").delete_many({"concept_id": {"$in": concept_ids}, "clerk_user_id": clerk_user_id})
        await db.get_collection("mastery").delete_many({"concept_id": {"$in": concept_ids}, "clerk_user_id": clerk_user_id})
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
    for col in ["questions", "attempts", "mastery"]:
        _DEMO_DB[col] = [d for d in _DEMO_DB.get(col, []) if d.get("concept_id") not in concept_ids]
    _DEMO_DB["relationships"] = [d for d in _DEMO_DB.get("relationships", []) if d.get("material_id") != material_id]
    _DEMO_DB["concepts"] = [d for d in _DEMO_DB.get("concepts", []) if d.get("material_id") != material_id]
    _DEMO_DB["materials"] = [d for d in _DEMO_DB.get("materials", []) if str(d.get("_id")) != material_id]
    return True


# ─── Concept Delete (Cascade) ─────────────────────────────────────────────────

async def delete_concept(db, concept_id: str, clerk_user_id: str) -> bool:
    """Delete a concept and cascade-delete questions, attempts, and mastery for it."""
    if db.is_online:
        col_con = db.get_collection("concepts")
        con = await col_con.find_one({"_id": ObjectId(concept_id), "clerk_user_id": clerk_user_id})
        if not con:
            return False
        concept_name = con.get("name", "")
        await db.get_collection("questions").delete_many({"concept_id": concept_id, "clerk_user_id": clerk_user_id})
        await db.get_collection("attempts").delete_many({"concept_id": concept_id, "clerk_user_id": clerk_user_id})
        await db.get_collection("mastery").delete_many({"concept_id": concept_id, "clerk_user_id": clerk_user_id})
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
    for col in ["questions", "attempts", "mastery"]:
        _DEMO_DB[col] = [d for d in _DEMO_DB.get(col, []) if d.get("concept_id") != concept_id]
    _DEMO_DB["concepts"] = [d for d in _DEMO_DB.get("concepts", []) if str(d.get("_id")) != concept_id]
    return True


# ─── Data Clearing ────────────────────────────────────────────────────────────

async def clear_user_data(db, clerk_user_id: str, category: str) -> Dict[str, Any]:
    """
    Clear a category of authenticated user data.
    category: 'assessments' | 'gamification' | 'materials' | 'concepts' | 'study_paths' | 'resources' | 'all'
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
            await _del("concepts")
            await _del("relationships")
            await _del("questions")
            await _del("attempts")
            await _del("mastery")
            await _del("study_paths")
        if category in ("concepts", "all"):
            await _del("concepts")
            await _del("relationships")
            await _del("questions")
            await _del("mastery")
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
        for col in ["materials", "concepts", "relationships", "questions", "attempts", "mastery", "study_paths"]:
            _DEMO_DB[col] = [d for d in _DEMO_DB.get(col, []) if d.get("clerk_user_id") != clerk_user_id]
        cleared.append("all learning data cleared")
    return {"cleared": cleared}


# ─── Global Search ────────────────────────────────────────────────────────────

async def search_user_data(db, clerk_user_id: str, query: str) -> Dict[str, Any]:
    """Search across the authenticated user's materials, concepts, questions, and assignments."""
    q = query.lower().strip()
    results = {"materials": [], "concepts": [], "questions": [], "assignments": []}

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
    for c in chunks_data:
        c["material_id"] = material_id
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
        docs = await col.find({"material_id": material_id}).to_list(None)
        return serialize_docs(docs)
    return serialize_docs([d for d in _DEMO_DB.get("material_chunks", []) if str(d.get("material_id")) == material_id])

async def TEMPORARY_VECTOR_SEARCH_FALLBACK(db, clerk_user_id: str, query_embedding: List[float], top_k: int = 5, min_similarity: float = 0.5) -> List[Dict[str, Any]]:
    """In-memory cosine similarity retrieval for RAG chunks, enforcing strict user ownership."""
    if not query_embedding:
        return []
        
    all_chunks = []
    if db.is_online:
        col = db.get_collection("material_chunks")
        all_chunks = await col.find({"clerk_user_id": clerk_user_id}).to_list(None)
    else:
        all_chunks = [d for d in _DEMO_DB.get("material_chunks", []) if d.get("clerk_user_id") == clerk_user_id]
    
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
            chunk["similarity_score"] = score
            scored_chunks.append((score, chunk))
    
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
