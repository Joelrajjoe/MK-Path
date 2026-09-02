# MK-Path MVP Scope

This document outlines the core scope for the Minimum Viable Product (MVP) of **MK-Path**. The goal is to deliver a stable, working prototype demonstrating the end-to-end user journey within a 2-day timeline.

## Core Features (In-Scope)

### A. Material Ingestion
*   **PDF Upload & Text Extraction:** Ingest study materials using `PyMuPDF` for local text extraction.
*   **Material Metadata:** Capture material title, file size, extraction timestamp, and owner.
*   **Text Preview & Status:** Frontend components for previewing extracted text and showing ingestion progress.

### B. AI Knowledge Extraction
*   **Concept Extraction:** Extract key concepts, descriptions, difficulty (`basic`, `intermediate`, `advanced`), and prerequisites.
*   **Dual-Relevance Scoring:** Assign Exam-Relevance (0-100) and Industry-Relevance (0-100) scores to each concept.
*   **Relationship Identification:** Map concept relationships (e.g., prerequisite of, builds upon).
*   **Structured Output:** Strictly validated JSON mapping.

### C. Interactive Knowledge Graph
*   **Visualization:** Graph visualization of concept nodes and relationships using `React Flow`.
*   **Interactivity:** Clickable nodes to view concept details, relevance scores, and current mastery.
*   **Mastery Heatmap:** Color-code nodes based on current mastery level (Weak, Learning, Proficient, Mastered).

### D. Adaptive Assessment
*   **Quiz Engine:** Dynamic generation of 5-10 multiple-choice questions.
*   **Adaptive Difficulty:** Adjust question difficulty based on prior answers.
*   **Behavioral Tracking:** Capture response time (seconds) and learner confidence (1-5 scale) for each question.
*   **Instant Feedback:** Provide explanations immediately following question submission.

### E. Mastery Model
*   **Explainable Formula:**
    $$Mastery = 0.50 \times Accuracy + 0.20 \times Confidence + 0.15 \times Response Speed + 0.15 \times Previous Mastery$$
*   **Mastery Categories:**
    *   `0-39`: Weak
    *   `40-69`: Learning
    *   `70-84`: Proficient
    *   `85-100`: Mastered
*   **Forgetting Factor:** Basic time-decay factor that reduces mastery score based on days since the last review.

### F. Adaptive Study Path
*   **Weak Concept Detection:** Highlight concepts under 40% mastery.
*   **Prioritization Engine:** Recommendation queue ordered by low mastery, high relevance (exam/industry), prerequisite hierarchy, and review urgency.

### G. Recommended Resources
*   **Metadata:** Recommend external learning items featuring title, type, URL, and a trust score.
*   **Association:** Link each resource explicitly to a weak or target concept.

### H. Gamification
*   **XP System:** Award points for meaningful actions:
    *   Quiz Completed: `+10 XP`
    *   Correct Answer: `+5 XP`
    *   Weak Concept Improved: `+20 XP`
    *   Mastery Level $\ge$ 85: `+25 XP`
*   **Levels:**
    *   `0-100`: Beginner
    *   `101-250`: Learner
    *   `251-500`: Explorer
    *   `501-1000`: Skilled
    *   `1000+`: Master

### I. Learner Dashboard
*   **Overview:** Display overall XP, Level, Mastery Distribution, and Weak Concepts.
*   **Study Path Panel:** Present the next priority concepts and resource cards.
*   **Next Reviews:** Schedule upcoming spaced-repetition reviews.
*   **Graph Preview:** Embedded minimap of the knowledge graph.

### J. Accessibility MVP
*   **Structure:** Semantic HTML tags, keyboard navigation, and aria-labels.
*   **Speech Services:** Integrated browser-native Text-to-Speech (Web Speech Synthesis API) and basic Web Speech Voice Commands.

### K. Demo Mode (Fallback)
*   **Offline Capability:** Fully functional mock services using predefined machine learning datasets when MongoDB Atlas or AI providers are offline.

---

## Out-of-Scope (Excluded from MVP)
*   Production-grade Reinforcement Learning (RL) or neural path optimizers.
*   Custom LLM/Transformer training or fine-tuning.
*   Lecture-video analysis or real-time audio/video processing.
*   Collaborative filtering or recommendation engines.
*   Neo4j graph database integration.
*   Mobile apps, microservices, Kubernetes, or complex multi-tenant cloud setups.
