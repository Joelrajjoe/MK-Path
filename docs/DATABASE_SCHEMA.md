# MK-Path Database Schema

This document details the MongoDB collections and schemas for **MK-Path**. All collections are designed for MongoDB Atlas, are created lazily at runtime, and map user-owned records to the authenticated user using their Clerk ID (`clerk_user_id`). No password-based authentication table or mock user accounts exist.

---

## Collections

### 1. `user_profiles`
Tracks profile details and preferences for authenticated Clerk users.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed, Unique)",
  "email": "String",
  "display_name": "String",
  "avatar_url": "String",
  "active_planner_model": "String ('baseline' | 'graph_aware' | 'rl')",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 2. `materials`
Stores uploaded PDF and multimodal materials, extracted text, and pipeline lifecycle status.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "title": "String",
  "file_name": "String",
  "content_type": "String",
  "raw_text": "String",
  "status": "String ('UPLOADED' | 'EXTRACTING' | 'EXTRACTED' | 'CHUNKING' | 'EMBEDDING' | 'READY' | 'PARTIAL' | 'FAILED')",
  "source_type": "String ('pdf' | 'txt' | 'image' | 'audio' | 'video')",
  "page_count": "Integer (Optional)",
  "duration": "Double (Optional)",
  "error_message": "String (Optional)",
  "created_at": "ISODate"
}
```

### 2b. `material_chunks` (Canonical RAG Chunks)
Stores canonical chunks and semantic embeddings for source grounding.
```json
{
  "_id": "ObjectId",
  "chunk_id": "String (Indexed, Unique)",
  "material_id": "ObjectId (Indexed)",
  "clerk_user_id": "String (Indexed)",
  "sequence": "Integer",
  "text": "String",
  "page": "Integer (Optional)",
  "section": "String (Optional)",
  "source_type": "String",
  "content_hash": "String (SHA-256)",
  "embedding_model": "String ('models/gemini-embedding-001')",
  "embedding": "Array of Doubles (768-dim)",
  "embedding_status": "String ('completed' | 'failed' | 'fallback')",
  "created_at": "ISODate"
}
```

### 3. `concepts`
Stores AI-extracted concepts linked to materials.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "material_id": "ObjectId (Indexed)",
  "name": "String (Indexed)",
  "description": "String",
  "exam_relevance": "Integer (0-100)",
  "industry_relevance": "Integer (0-100)",
  "difficulty": "String ('basic' | 'intermediate' | 'advanced')",
  "prerequisites": "Array of Strings (concept names)",
  "created_at": "ISODate"
}
```

### 4. `relationships`
Stores graph edges connecting concepts.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "source_concept_name": "String",
  "target_concept_name": "String",
  "relationship_type": "String",
  "created_at": "ISODate"
}
```

### 5. `questions`
Stores multiple-choice questions generated from extracted concepts.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "concept_id": "ObjectId (Indexed)",
  "concept_name": "String",
  "question_text": "String",
  "options": "Array of Strings",
  "correct_option_index": "Integer (0-3)",
  "difficulty": "String ('basic' | 'intermediate' | 'advanced')",
  "explanation": "String"
}
```

### 6. `attempts`
Records user answers, confidence, response times, and evaluation results.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "concept_id": "ObjectId",
  "question_id": "ObjectId",
  "selected_option_index": "Integer",
  "is_correct": "Boolean",
  "confidence": "Integer (1-5)",
  "response_time_seconds": "Double",
  "created_at": "ISODate"
}
```

### 7. `mastery`
Stores user concept-mastery calculations and progress categorization.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "concept_id": "ObjectId (Indexed)",
  "concept_name": "String",
  "mastery_score": "Double (0.0-100.0)",
  "category": "String ('Weak' | 'Learning' | 'Proficient' | 'Mastered')",
  "last_reviewed_at": "ISODate",
  "next_review": "ISODate",
  "updated_at": "ISODate",
  "accuracy_rolling": "Double",
  "confidence_rolling": "Double",
  "speed_rolling": "Double",
  
  "baseline_mastery": "Double (Shadow)",
  "knowledge_tracing_mastery": "Double (Shadow)",
  "kt_uncertainty": "Double (Shadow)",
  "kt_mastery_probability": "Double (Shadow)",
  "active_mastery_model": "String ('baseline' | 'knowledge_tracing')"
}
```

### 8. `study_paths`
Stores recommended learning queues for each user.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "ordered_concepts": [
    {
      "concept_id": "ObjectId",
      "concept_name": "String",
      "priority_score": "Double",
      "reason": "String"
    }
  ],
  "updated_at": "ISODate"
}
```

### 9. `resources`
Stores trust-weighted learning resource recommendations. (Shared/Global)
```json
{
  "_id": "ObjectId",
  "concept_name": "String (Indexed)",
  "title": "String",
  "type": "String ('article' | 'video' | 'documentation')",
  "url": "String",
  "trust_score": "Integer (0-100)",
  "created_at": "ISODate"
}
```

### 10. `gamification`
Keeps track of levels and experience points earned by learners.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed, Unique)",
  "xp": "Integer",
  "level": "Integer",
  "level_name": "String ('Beginner' | 'Learner' | 'Explorer' | 'Skilled' | 'Master')",
  "achievements": "Array of Strings",
  "updated_at": "ISODate"
}
```

### 11. `learner_events`
Tracks granular behavioral actions performed by learners.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "event_type": "String (Indexed)",
  "timestamp": "ISODate (Indexed)",
  "session_id": "String (Optional)",
  "material_id": "ObjectId (Optional)",
  "concept_id": "ObjectId (Optional)",
  "question_id": "ObjectId (Optional)",
  "resource_id": "ObjectId (Optional)",
  "metadata": "Object"
}
```

### 12. `resource_feedback`
Tracks individual learner reviews, helpfulness votes, and completion milestones.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "resource_id": "ObjectId (Indexed)",
  "rating": "Integer (1-5, Optional)",
  "helpful": "Boolean (Optional)",
  "completed": "Boolean",
  "updated_at": "ISODate"
}
```

### 13. `user_preferences`
Tracks learner extended profile preferences, target roles, exams, and daily study targets.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed, Unique)",
  "display_name": "String (Optional)",
  "preferred_name": "String (Optional)",
  "learning_goal": "String (Optional)",
  "target_role": "String (Optional)",
  "target_exam": "String (Optional)",
  "current_level": "String ('Beginner' | 'Intermediate' | 'Advanced' | 'Expert')",
  "preferred_difficulty": "String ('basic' | 'intermediate' | 'advanced')",
  "daily_study_target_minutes": "Integer (5-480)",
  "preferred_session_duration_minutes": "Integer (5-120)",
  "deadline": "ISODate (Optional)",
  "updated_at": "ISODate"
}
```

### 14. `goals`
Persistent goal-to-skill state model storing benchmark targets, required skills, and readiness mappings.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "title": "String (e.g. 'Data Analyst')",
  "description": "String (Optional)",
  "target_role": "String (Optional)",
  "target_exam": "String (Optional)",
  "target_date": "ISODate (Optional)",
  "required_skills": [
    {
      "name": "String",
      "required_level": "Double (0.0-100.0)",
      "source": "String ('learner_defined' | 'verified_system_mapping' | 'ai_suggested')",
      "weight": "Double (0.1-5.0)"
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 15. `assignments`
Lifecycle assignments supporting drafts, submissions, automatic grading, and XP impact.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "title": "String",
  "description": "String",
  "concept_ids": "Array of ObjectIds",
  "material_id": "ObjectId (Optional)",
  "difficulty": "String ('basic' | 'intermediate' | 'advanced')",
  "status": "String ('DRAFT' | 'IN_PROGRESS' | 'SUBMITTED' | 'EVALUATED')",
  "questions": "Array of Question Objects",
  "answers": "Object",
  "score": "Double (0.0-100.0, Optional)",
  "feedback": "String (Optional)",
  "xp_awarded": "Integer (Optional)",
  "created_at": "ISODate",
  "submitted_at": "ISODate (Optional)"
}
```

### 16. `podcasts`
NotebookLM-style two-host AI conversational podcasts with multi-speaker dialogue scripts.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "material_id": "ObjectId (Optional)",
  "material_title": "String",
  "concept_ids": "Array of ObjectIds",
  "title": "String",
  "summary": "String",
  "episode_duration_est_minutes": "Double",
  "hosts": "Array of Strings",
  "script": [
    {
      "speaker": "String ('Alex' | 'Sam')",
      "text": "String",
      "emotion": "String",
      "pitch": "Double",
      "rate": "Double"
    }
  ],
  "created_at": "ISODate"
}
```

### 17. `tutor_sessions`
Interactive Socratic tutoring chat sessions grounded in course materials.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "concept_id": "ObjectId (Optional)",
  "concept_name": "String",
  "messages": [
    {
      "role": "String ('user' | 'assistant' | 'system')",
      "content": "String",
      "timestamp": "ISODate"
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### 18. `flashcards`
AI-generated conceptual flashcards scheduled using the SM-2 Spaced Repetition algorithm.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "concept_id": "ObjectId (Optional)",
  "material_id": "ObjectId (Optional)",
  "front": "String",
  "back": "String",
  "explanation": "String (Optional)",
  "interval_days": "Integer",
  "ease_factor": "Double",
  "repetitions": "Integer",
  "next_review": "ISODate (Indexed)",
  "created_at": "ISODate"
}
```

### 19. `study_notes`
Comprehensive study notes, summaries, key takeaways, and mind map trees.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "material_id": "ObjectId (Optional)",
  "concept_id": "ObjectId (Optional)",
  "title": "String",
  "summary": "String",
  "key_points": "Array of Strings",
  "detailed_content": "String (Markdown)",
  "mind_map_tree": "Object",
  "created_at": "ISODate"
}
```

