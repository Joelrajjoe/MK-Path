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
| **POST** | `/api/resources/{id}/click` | Clerk Required | Track resource link click-through events |
| **GET** | `/api/resources/recommend` | Clerk Required | Retrieve trust-weighted resource recommendations |
| **GET** | `/api/resources/recommend/evaluate` | Clerk Required | Compare Baseline vs Trust-Aware recommenders in shadow mode |
| **POST** | `/api/resources/recommend/promote` | Clerk Required | Promote selected resource recommender to active production |
| **GET** | `/api/gamification/audit` | Clerk Required | Verify and reproduce user XP score from events history |