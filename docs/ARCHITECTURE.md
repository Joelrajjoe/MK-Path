# MK-Path System Architecture

The following block diagram outlines the component tiers, data flow, and active service integrations:

```mermaid
flowchart TD
    subgraph Clients ["Client Applications"]
        Web["React / Vite Web Client"]
        Mobile["React Native / Expo Mobile Client"]
    end

    subgraph Backend ["FastAPI Backend Tiers"]
        Router["APIs Routing & Controller Gateway"]
        Auth["JWKS Session Validator (Clerk Identity)"]
        
        subgraph Services ["Backend Intelligence Layer"]
            Ingest["Multimodal Content Extractor Interface"]
            KT["Bayesian Knowledge Tracing Engine"]
            Plan["Multi-Objective Study Path Planner"]
            Rec["Trust-Aware Resource Recommender"]
            Game["Configurable Gamification Reward Engine"]
        end
    end

    subgraph Data ["Database & Storage Layer"]
        MongoDB["MongoDB Atlas (User Scoped Collections)"]
        Neo4j["Neo4j Graph Database (Prerequisite Maps)"]
    end

    %% Client Interactions
    Web -->|HTTP Requests| Router
    Mobile -->|HTTP Requests| Router
    Router -->|JWKS RS256 Verification| Auth

    %% Route Handlers to Services
    Router --> Ingest
    Router --> KT
    Router --> Plan
    Router --> Rec
    Router --> Game

    %% Database integrations
    Ingest -->|Persist Material Text| MongoDB
    KT -->|Upsert Rolling Mastery| MongoDB
    Plan -->|Query Prerequisites| Neo4j
    Plan -->|BFS Fallback Path Traversal| MongoDB
    Rec -->|Fetch catalog & feedback| MongoDB
    Game -->|Audit events history| MongoDB
```

---

## 1. Modular Services Integration
*   **Ingestion Extractor Interface**: Contains `PDFExtractor` (PyMuPDF), `TextExtractor`, `OCRExtractor` (OCR scanned text), `AudioExtractor` (transcribing logs), and `VideoExtractor`.
*   **Knowledge Tracing Service**: Executes dynamic BKT updates adjusting slip and guess parameters on quiz submissions, operating concurrently in Shadow Mode.
*   **Graph Intelligence Service**: Performs Neo4j Bolt graph traversal, with offline-ready local Graph BFS algorithm backups.
*   **Study Planner Service**: Compares heuristic weights against Graph-Aware nodes and tabular Q-learning RL policy runs.
*   **Recommender Service**: Blends curated authority trust, average community rating feedback, age freshness, difficulty fits, and completion penalties.
*   **Gamification Service**: Centralizes XP constants and audits learner event logs.