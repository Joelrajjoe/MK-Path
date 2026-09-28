# MK-Path API Specification

All protected endpoints require an authenticated user session validated via the `Authorization: Bearer <clerk_session_token>` header.

---

## Endpoint Index

| Method | Endpoint | Authentication | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/health` | None (Public) | API health check & connectivity status |
| **POST** | `/api/materials/upload` | Clerk Required | Upload study material & extract raw text |
| **GET** | `/api/materials` | Clerk Required | Retrieve list of materials uploaded by current user |
| **GET** | `/api/materials/{id}` | Clerk Required | Retrieve specific material detail and raw text preview |
| **POST** | `/api/materials/{id}/extract-concepts` | Clerk Required | Trigger AI concept and relationship extraction |
| **GET** | `/api/concepts` | Clerk Required | Get all concepts extracted for the current user |
| **GET** | `/api/concepts/{id}` | Clerk Required | Get details of a specific concept |
| **GET** | `/api/graph` | Clerk Required | Get the nodes and edges for the user's knowledge graph |
| **GET** | `/api/assessment` | Clerk Required | Retrieve a list of MCQs |
| **POST** | `/api/assessment/submit` | Clerk Required | Submit quiz answers, confidence level, and response times |
| **GET** | `/api/mastery` | Clerk Required | Get overall and per-concept mastery metrics |
| **GET** | `/api/study-path` | Clerk Required | Retrieve the current ordered learning path recommendation |
| **GET** | `/api/resources` | Clerk Required | Retrieve trust-weighted learning resources for weak areas |
| **GET** | `/api/gamification` | Clerk Required | Retrieve current XP, level, and earned achievements |
| **POST** | `/api/events` | Clerk Required | Log granular learner behavioral events |
| **GET** | `/api/events/analytics` | Clerk Required | Retrieve aggregated attempts, correctness, confidence and response trends |
| **GET** | `/api/graph/path` | Clerk Required | Calculate shortest prerequisite path between two concepts |
| **GET** | `/api/graph/neighborhood` | Clerk Required | Get concept neighborhood directly connected concepts |
| **GET** | `/api/graph/centrality` | Clerk Required | Get centrality degree rankings |
| **GET** | `/api/graph/prerequisites` | Clerk Required | Retrieve list of direct prerequisite concept names |
| **GET** | `/api/kt/evaluate` | Clerk Required | Evaluate and compare baseline vs BKT model prediction metrics |
| **POST** | `/api/kt/promote` | Clerk Required | Promote Bayesian Knowledge Tracing (BKT) to production |
| **GET** | `/api/assessment/adaptive` | Clerk Required | Query state-aware adaptive next question selection |
| **GET** | `/api/planner/evaluate` | Clerk Required | Compare Baseline, Graph-Aware and RL planners in simulation |
| **POST** | `/api/planner/promote` | Clerk Required | Promote selected study path planner model to active production |
| **POST** | `/api/resources/{id}/feedback` | Clerk Required | Submit helpful/not helpful rating and score feedback |
| **POST** | `/api/resources/{id}/complete` | Clerk Required | Record learner resource completion |
| **GET** | `/api/user/profile` | Clerk Required | Retrieve full user profile enriched with preferences & level |
| **GET** | `/api/user/preferences` | Clerk Required | Retrieve learner profile and study target preferences |
| **PUT** | `/api/user/preferences` | Clerk Required | Upsert learner goals, role, exam, difficulty, and study targets |
| **PATCH** | `/api/materials/{id}` | Clerk Required | Rename or update study material metadata |
| **POST** | `/api/materials/{id}/reprocess` | Clerk Required | Re-run chunking and vector embedding generation for material |
| **DELETE** | `/api/materials/{id}` | Clerk Required | Delete material and cascade delete derived concepts/questions |
| **POST** | `/api/concepts` | Clerk Required | Create user-defined educational concept |
| **PATCH** | `/api/concepts/{id}` | Clerk Required | Edit concept details, relevance weights, and prerequisites |
| **DELETE** | `/api/concepts/{id}` | Clerk Required | Delete concept and cascade delete questions/attempts |
| **POST** | `/api/concepts/merge` | Clerk Required | Merge duplicate concepts and repoint dependent questions/attempts |
| **GET** | `/api/search` | Clerk Required | Global search across materials, concepts, questions, assignments, resources, study paths, activity |
| **POST** | `/api/data/clear` | Clerk Required | Safe category data reset (never touches Clerk account) |
| **POST** | `/api/goals` | Clerk Required | Create persistent learning goal with target skills and benchmarks |
| **GET** | `/api/goals` | Clerk Required | List all goals belonging to the authenticated learner |
| **GET** | `/api/goals/{id}` | Clerk Required | Retrieve detailed goal metadata and skill benchmark requirements |
| **PATCH** | `/api/goals/{id}` | Clerk Required | Update goal benchmarks, target role/exam, or required skills |
| **DELETE** | `/api/goals/{id}` | Clerk Required | Delete learning goal owned by learner |
| **POST** | `/api/goals/{id}/skill-gaps` | Clerk Required | Goal-to-skill gap intelligence analysis with prerequisite blocking and readiness |
| **GET** | `/api/diagnosis` | Clerk Required | Retrieve deterministic misconception and prerequisite diagnoses |
| **POST** | `/api/diagnosis/evaluate` | Clerk Required | Run real-time diagnostic evaluation across learner attempt histories |
| **POST** | `/api/simulator/what-if` | Clerk Required | Run isolated counterfactual learner state simulations without altering production DB |
| **GET** | `/api/next-best-action` | Clerk Required | Deterministic, explainable next-best-learning-action recommendation engine |
| **GET** | `/api/mastery/evidence/{concept_id}` | Clerk Required | Multi-source mastery evidence chain with BKT uncertainty and confidence |
| **GET** | `/api/assignments` | Clerk Required | List assignments belonging to authenticated user |
| **POST** | `/api/assignments/generate` | Clerk Required | Generate conceptual AI assignment from curriculum concepts |
| **GET** | `/api/assignments/{id}` | Clerk Required | Retrieve specific assignment details and questions |
| **POST** | `/api/assignments/{id}/save-draft` | Clerk Required | Autosave assignment answer state |
| **POST** | `/api/assignments/{id}/submit` | Clerk Required | Submit assignment, evaluate answers, compute mastery impact & award XP |
| **DELETE** | `/api/assignments/{id}` | Clerk Required | Delete specific assignment |
| **DELETE** | `/api/assignments/all` | Clerk Required | Bulk delete all assignments for current user |
| **GET** | `/api/dashboard/summary` | Clerk Required | Unified learner intelligence dashboard control center data |
| **GET** | `/api/podcasts` | Clerk Required | List generated audio podcast episodes |
| **GET** | `/api/podcasts/{id}` | Clerk Required | Retrieve single podcast episode script and speech config |
| **POST** | `/api/podcasts/generate` | Clerk Required | Synthesize dynamic two-host NotebookLM-inspired audio podcast episode |
| **DELETE** | `/api/podcasts/{id}` | Clerk Required | Delete single podcast episode |
| **DELETE** | `/api/podcasts/all` | Clerk Required | Bulk delete all podcasts for current user |
| **GET** | `/api/tutor/sessions` | Clerk Required | Retrieve AI Socratic tutor conversation sessions |
| **POST** | `/api/tutor/chat` | Clerk Required | Send message to AI Socratic concept guide |
| **DELETE** | `/api/tutor/sessions/{id}` | Clerk Required | Delete single tutor chat session |
| **DELETE** | `/api/tutor/sessions/all` | Clerk Required | Bulk delete all tutor chat sessions |
| **GET** | `/api/flashcards` | Clerk Required | List active flashcard decks and spaced-repetition schedules |
| **GET** | `/api/flashcards/due` | Clerk Required | Retrieve flashcards due for immediate spaced repetition review |
| **POST** | `/api/flashcards/generate` | Clerk Required | Synthesize AI flashcards grounded in study materials |
| **POST** | `/api/flashcards/{id}/review` | Clerk Required | Record flashcard recall rating (1-5) and update SM-2 interval |
| **DELETE** | `/api/flashcards/{id}` | Clerk Required | Delete single flashcard |
| **DELETE** | `/api/flashcards/all` | Clerk Required | Bulk delete all flashcards for current user |
| **GET** | `/api/study-notes` | Clerk Required | Retrieve generated comprehensive study notes and mind map trees |
| **POST** | `/api/study-notes/generate` | Clerk Required | Generate structured study notes and visual hierarchical mind maps |
| **DELETE** | `/api/study-notes/{id}` | Clerk Required | Delete single study note |
| **DELETE** | `/api/study-notes/all` | Clerk Required | Bulk delete all study notes for current user |
| **DELETE** | `/api/concepts/all` | Clerk Required | Bulk delete all extracted concepts and linked records |