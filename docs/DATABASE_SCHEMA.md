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
Stores uploaded PDF materials, extracted text, and processing status.
```json
{
  "_id": "ObjectId",
  "clerk_user_id": "String (Indexed)",
  "title": "String",
  "file_name": "String",
  "content_type": "String",
  "raw_text": "String",
  "status": "String ('processing' | 'processed' | 'failed')",
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
