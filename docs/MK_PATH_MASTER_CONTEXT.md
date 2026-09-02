MK-PATH — MASTER DEVELOPMENT INSTRUCTION

You are the lead software architect and senior full-stack developer for my capstone project.

PROJECT:
MK-Path: A Multimodal Knowledge-Graph Framework for Industry-Aligned Adaptive Learning with Behaviorally-Coupled Gamification.

DOMAIN:
EdTech + Artificial Intelligence

REFERENCE:
The project proposal defines the system around:
- multimodal study-material ingestion
- concept extraction
- unified knowledge graph
- dual Exam-Relevance and Industry-Relevance scoring
- confidence-corrected learner mastery
- adaptive learning path planning
- trust-weighted resource recommendation
- behaviorally-coupled gamification
- accessibility through voice/screen-reader support

The goal now is NOT to build the complete research system.

The goal is to build a stable, working MVP within approximately 2 days that demonstrates the core research idea end-to-end.

==================================================
1. CORE MVP USER JOURNEY
==================================================

The complete MVP flow must be:

Student
→ Upload PDF study material
→ Extract text
→ Extract concepts using AI
→ Identify concept relationships
→ Assign Exam-Relevance score
→ Assign Industry-Relevance score
→ Store concepts in MongoDB
→ Display unified knowledge graph
→ Generate/adapt quiz
→ Capture answer + confidence + response time
→ Calculate mastery
→ Identify weak concepts
→ Generate personalized study path
→ Recommend learning resources
→ Award skill-based XP
→ Update learner dashboard
→ Schedule concept review

This complete flow is the primary acceptance criterion.

==================================================
2. MVP FEATURES
==================================================

MUST IMPLEMENT:

A. Material ingestion
- PDF upload
- PDF text extraction
- material metadata
- extracted-text preview
- processing status

B. AI knowledge extraction
- concept extraction
- concept description
- concept relationships
- Exam-Relevance score 0-100
- Industry-Relevance score 0-100
- difficulty
- prerequisites

C. Knowledge graph
- interactive concept nodes
- relationships/edges
- concept details
- relevance scores
- mastery visualization

D. Assessment
- 5-10 questions per assessment
- multiple-choice questions
- difficulty levels
- adaptive difficulty
- answer recording
- confidence 1-5
- response-time recording
- explanation after submission

E. Mastery
- accuracy
- confidence
- response speed
- previous mastery
- forgetting/retention factor
- mastery score
- mastery category

F. Adaptive study path
- weak concept detection
- relevance-aware prioritization
- prerequisite awareness
- review urgency
- ordered recommendations

G. Resources
- recommended resources
- concept association
- source
- type
- URL
- trust score

H. Gamification
- XP
- levels
- skill-improvement XP
- achievements/progress

I. Dashboard
- overall progress
- mastery
- weak concepts
- exam relevance
- industry relevance
- knowledge graph preview
- study path
- XP/level
- upcoming reviews

J. Accessibility MVP
- semantic HTML
- keyboard navigation
- accessible controls
- browser text-to-speech
- basic Web Speech API voice commands where supported

K. DEMO MODE
The system MUST have a working fallback/demo mode.

The application must remain demonstrable if:
- AI is unavailable
- internet is unavailable
- external resource access fails
- live processing fails

Demo mode must contain realistic Machine Learning sample data.

==================================================
3. FEATURES EXCLUDED FROM THE 2-DAY MVP
==================================================

DO NOT IMPLEMENT:

- production-grade reinforcement learning
- actual RL path optimization
- custom LLM training
- custom transformer training
- large-scale model training
- full lecture-video understanding
- real-time video processing
- production collaborative filtering
- Neo4j
- mobile application
- microservices
- Kubernetes
- complex authentication
- multi-tenant architecture
- production cloud infrastructure
- complex web crawling
- real-time collaboration

If a feature is not required for the core demo, do not add it.

==================================================
4. TECHNOLOGY STACK
==================================================

FRONTEND:
- React
- Vite
- Tailwind CSS
- React Router
- React Flow
- Recharts

BACKEND:
- Python
- FastAPI
- Pydantic

DATABASE:
- MongoDB
- MongoDB Atlas free tier or local MongoDB

DOCUMENT PROCESSING:
- PyMuPDF

OCR:
- Tesseract only if time permits

AI:
- Prefer local/free/open-source model
- AI provider must be abstracted
- Do not hard-code provider credentials

VOICE:
- Browser Web Speech API
- Browser SpeechSynthesis

VERSION CONTROL:
- Git
- GitHub

==================================================
5. ARCHITECTURE
==================================================

Use:

React Frontend
      ↓
FastAPI REST API
      ↓
Application/Service Layer
      ↓
MongoDB
      ↓
AI / Document Processing Services

The frontend must NEVER directly access:
- MongoDB
- AI provider credentials
- server-side secrets

All AI operations must happen through FastAPI.

MongoDB is the source of truth for application data.

==================================================
6. MONGODB COLLECTIONS
==================================================

Use these collections:

users
materials
concepts
relationships
questions
attempts
mastery
study_paths
resources
gamification

Keep schemas simple.

Do not introduce unnecessary database abstraction.

==================================================
7. AI CONTRACT
==================================================

AI output MUST be structured JSON.

Never directly store uncontrolled LLM text as application state.

Validate AI output before storing it.

Concept extraction must return:

{
  "concepts": [
    {
      "name": "...",
      "description": "...",
      "exam_relevance": 0,
      "industry_relevance": 0,
      "difficulty": "basic|intermediate|advanced",
      "prerequisites": []
    }
  ],
  "relationships": [
    {
      "source": "...",
      "target": "...",
      "relationship_type": "..."
    }
  ]
}

Question generation must also return validated JSON.

==================================================
8. MASTERY MODEL
==================================================

Use an explainable MVP formula:

Mastery =
0.50 × Accuracy
+ 0.20 × Confidence
+ 0.15 × Response Speed
+ 0.15 × Previous Mastery

Normalize inputs to 0-100.

Categories:

0-39   = Weak
40-69  = Learning
70-84  = Proficient
85-100 = Mastered

Add a simple forgetting/retention factor based on time since review.

Do not claim this is a scientifically validated final model.

It is the MVP implementation of the proposed confidence-corrected mastery concept.

==================================================
9. ADAPTIVE LEARNING LOGIC
==================================================

For MVP use an explainable rule-based policy.

IF mastery < 40:
    recommend prerequisite/basic learning

IF mastery 40-69:
    recommend intermediate practice

IF mastery 70-84:
    recommend advanced/application practice

IF mastery >= 85:
    mark mastered and move to the next priority concept

Priority should consider:

- low mastery
- Exam-Relevance
- Industry-Relevance
- prerequisites
- review urgency

DO NOT implement reinforcement learning.

==================================================
10. GAMIFICATION
==================================================

XP must represent meaningful learning.

Example:

quiz completed = +10 XP
correct answer = +5 XP
weak concept improvement = +20 XP
mastery >= 85 = +25 XP

Levels:

0-100 = Beginner
101-250 = Learner
251-500 = Explorer
501-1000 = Skilled
1000+ = Master

Do not award XP simply for opening pages.

==================================================
11. FREE-FIRST PRINCIPLE
==================================================

The working demo should require no paid API.

Prefer:
- local models
- open-source libraries
- browser APIs
- MongoDB free tier
- local development

If an external service is optional, implement a fallback.

==================================================
12. TOKEN / AGENT MANAGEMENT
==================================================

THIS IS CRITICAL.

Before modifying code:
1. Inspect the repository.
2. Inspect existing architecture.
3. Inspect the current phase status.
4. Reuse existing code.

DO NOT:
- rewrite the whole project
- recreate existing components
- recreate existing API clients
- recreate database services
- add unnecessary libraries
- refactor unrelated code
- change the technology stack
- repeat large amounts of code
- generate unnecessary documentation

Make targeted changes only.

Do not start future phases automatically.

At the end of every phase report only:

1. Files changed
2. Features completed
3. Tests/checks performed
4. Current known issue
5. Next phase

==================================================
13. DEVELOPMENT CONTROL FILES
==================================================

Maintain:

docs/MK_PATH_MASTER_CONTEXT.md
docs/MVP_SCOPE.md
docs/ARCHITECTURE.md
docs/DATABASE_SCHEMA.md
docs/API_SPEC.md
docs/AI_OUTPUT_SCHEMA.md
docs/ANTIGRAVITY_RULES.md
docs/MVP_STATUS.md

MVP_STATUS.md must be updated after every completed phase.

==================================================
14. GIT SAFETY
==================================================

Do not delete working functionality.

Do not perform destructive migrations without explicit instruction.

Preserve backwards compatibility wherever practical.

Keep .env out of Git.

==================================================
15. DEFINITION OF DONE
==================================================

The MVP is complete only when a reviewer can perform:

1. Upload PDF
2. Extract content
3. Generate concepts
4. View relevance scores
5. View knowledge graph
6. Take adaptive quiz
7. Submit confidence
8. Capture response time
9. Calculate mastery
10. Identify weak concepts
11. Receive study path
12. Receive resources
13. Gain XP
14. See dashboard update
15. See next review recommendation

AND:

"Load Demo Data"

must allow the entire experience to work without relying on live AI.

==================================================
16. CURRENT INSTRUCTION
==================================================

Do not implement anything yet.

First inspect the repository and environment.

Read all project control documents if they exist.

Return a concise readiness report.

Do not install dependencies.
Do not modify code.
Do not create new features.

Wait for the next phase instruction.
