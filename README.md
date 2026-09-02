# MK-Path: Multimodal Knowledge-Graph Framework for Industry-Aligned Adaptive Learning

MK-Path is an AI-powered adaptive EdTech platform that ingests multimodal study materials, extracts core concepts, maps their relationships inside a unified knowledge graph, and schedules personalized study pathways. The system schedules confidence-corrected assessments using a rule-based Spaced Repetition engine and awards XP points and level milestones to gamify the learning progression.

---

## 1. Overview

MK-Path orchestrates an end-to-end adaptive tutoring cycle through the following stages:

```
Study Material (PDF Ingestion)
      ↓
Content Extraction (PyMuPDF Text Miner)
      ↓
AI Concept Extraction (Gemini / Groq / Local Fallback)
      ↓
Knowledge Graph (React Flow Visualization with Mastery Glowing Nodes)
      ↓
Adaptive Assessment (Confidence & Time Corrected MCQs Quiz)
      ↓
Mastery Analysis (4-Term Score Calculation & Spaced Repetition Intervals)
      ↓
Personalized Study Path (Prioritized Topic Sequences with Prerequisite Locking)
      ↓
Recommended Resources ( Curated Catalogue Aligned with Weak Concepts)
      ↓
Gamification (XP Logs, Level Ranks, and Achievements)
```

---

## 2. Key Features

### Implemented (MVP Complete)
*   **Real-time Authentication**: Email/Password and Google Social authentication powered by Clerk (`@clerk/react`). Protected frontend routes and JWT RS256 token validation on FastAPI requests.
*   **Multimodal Material Ingestion**: Unified ingestion interface supporting PDFs, plain TXT files, scanned images/OCR, audio transcriptions (MP3, WAV, M4A), and video audio extraction (MP4, AVI, WEBM) up to 25MB. Dynamically redirects scanned PDFs to OCR and transcribes audiovisual logs using Pydantic-validated models.
*   **AI Concept Mining**: Dual-provider concept mapping (Gemini JSON mode -> Groq `llama-3.3-70b-versatile` -> local heuristic fallback) that identifies concept difficulty, prerequisites, and relevance weightings.
*   **RAG (Retrieval-Augmented Generation) Pipeline**: Ingested materials are chunked (500-word blocks), embedded using Gemini `text-embedding-004`, and queried using cosine similarity to ground the AI with specific context, eliminating hallucinations.
*   **Context-Aware Personalization**: AI prompts strictly utilize user metadata (learning goals, target role, preferred difficulty) from `UserPreferences` to dynamically adjust generated assessments and extracted concepts.
*   **Interactive Knowledge Graph**: React Flow canvas with custom glowing node rings representing mastery levels, zoom/pan viewport controls, and detail sliding drawers.
*   **Adaptive Assessment Quiz**: Context-grounded assessment generator (Gemini -> Groq -> Local Distractors) that creates targeted MCQs using the user's uploaded material.
*   **Confidence-Corrected Mastery**: Computes rolling 4-term mastery scores:
    `Mastery = 0.50 * Accuracy + 0.20 * Confidence + 0.15 * Response Speed + 0.15 * Previous Mastery`
*   **Personalized Study Path Timeline**: Prioritizes concept sequences by low mastery, exam weight, industry weight, and urgency. Automatically locks target concepts if their prerequisite scores are under 70%.
*   **Curated Resource Recommendations**: Dynamic catalog matching documentation and video tutorials matching weak concepts.
*   **Gamification**: XP points trigger level upgrades (Beginner, Learner, Explorer, Skilled, Master) and unlock achievements.
*   **Speech Recognition Accessibility**: Web Speech API floating panel supporting voice synthesis and microphone commands ("Start quiz", "Show study path", "Read question").
*   **Controlled Presentation Seeding**: "Seed Demo Dataset" button loads mock data scoped strictly to the current Clerk ID to enable immediate platform review.

### Planned (Post-MVP)
*   **Multimodal Audio Ingestion**: Voice and lecture transcription loaders.
*   **Collaborative Graph Filtering**: Recommending study paths based on peer performance cohorts.

---

## 3. System Architecture

The following block diagram represents the application components and data flow:

```mermaid
graph TD
    Client["React / Vite App (Tailwind CSS v4)"]
    Auth["Clerk JS SDK (Frontend Authentication)"]
    Gateway["FastAPI API Server"]
    Verify["JWKS Local Token Decoder"]
    Service["Concept & MCQ Generator Service"]
    PyMuPDF["PyMuPDF Document Parser"]
    Atlas["MongoDB Atlas Cloud Database"]
    AI["Google Gemini / Groq APIs"]

    Client -->|1. Sign Up / Sign In| Auth
    Client -->|2. Send Authorized HTTP Requests| Gateway
    Gateway -->|3. Decrypt RS256 JWT Session| Verify
    Gateway -->|4. Parse Ingested PDF bytes| PyMuPDF
    Gateway -->|5. Extract Concepts / MCQs| Service
    Service -->|6. Call AI Endpoints (Fallback Sequence)| AI
    Gateway -->|7. Persist User-Scoped Collections| Atlas
```

---

## 4. Technology Stack

| Component | Technology | Version / Specific Library |
| :--- | :--- | :--- |
| **Frontend Core** | React | `^19.2.8` |
| **Build Tooling** | Vite | `^8.2.2` |
| **Authentication** | Clerk React JS SDK | `^6.14.7` |
| **Styling** | Tailwind CSS v4 | `^4.3.3` |
| **Backend Core** | FastAPI | `0.110.0` |
| **ASGI Web Server** | Uvicorn | `0.28.0` |
| **Database** | MongoDB Atlas | Cloud-hosted instance |
| **Database Driver** | Motor (Async PyMongo) | `3.3.2` |
| **AI Models** | Gemini API (`gemini-2.5-flash-latest`, `text-embedding-004`) / Groq (`llama-3.3-70b-versatile`) | Cloud endpoints |
| **Document Processing** | PyMuPDF | `1.23.26` |
| **Graph Visualization**| React Flow (`@xyflow/react`) | `^12.11.5` |
| **Icons** | Lucide React | `^1.34.0` |
| **Python Tooling** | Python | `3.10.x` or higher |

---

## 5. Project Structure

```
MKLP/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   └── ai.py           # AI generation & fallback heuristics
│   │   ├── auth.py             # Clerk token decoder
│   │   ├── config.py           # Settings loader
│   │   ├── crud.py             # User-scoped database commands
│   │   ├── database.py         # Mongo Motor initialization
│   │   ├── main.py             # FastAPI entry point & endpoints
│   │   └── models.py           # Pydantic schemas
│   └── requirements.txt        # Python libraries list
├── docs/                       # Project control documentation
├── frontend/
│   ├── src/
│   │   ├── components/         # Navigation & shells
│   │   ├── pages/              # Dashboard, Graph, Materials, Assessment
│   │   ├── App.jsx             # React router configuration
│   │   ├── main.jsx            # Clerk provider shell
│   │   └── index.css           # Tailwind v4 configuration
│   └── package.json            # Node script commands
├── .env.example                # Shared environment variable keys
├── .gitignore                  # Build/environment ignore rules
└── README.md                   # Project documentation
```

---

## 6. Prerequisites

Ensure you have the following installed locally:
1.  **Node.js**: `v20.x` or higher recommended.
2.  **npm**: `v10.x` or higher.
3.  **Python**: `v3.10.x` or higher.
4.  **Clerk Account**: To acquire Clerk publishable and secret keys.
5.  **MongoDB Atlas Account**: Database is cloud-hosted only. Local MongoDB or Docker containers are not required.

---

## 7. Environment Variables

Create a `.env` file in the root workspace folder matching the keys defined in `.env.example`:

```bash
# Frontend Publishable Key (Read by Clerk React SDK)
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...

# Backend Clerk secret validation key
CLERK_SECRET_KEY=sk_test_...

# MongoDB Atlas connection details
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=mk_path

# AI API keys
GEMINI_API_KEY=AIzaSy...     # (Supports multiple comma-separated keys for retries)
GROQ_API_KEY=gsk_...
```

---

## 8. Installation

Clone the workspace repository:
```bash
git clone <repository-url>
cd MKLP
```

### Frontend Dependencies:
```bash
cd frontend
npm install
```

### Backend Dependencies:
It is recommended to run the backend inside a virtual environment:
```bash
cd backend
python -m venv .venv
# Activate in Windows PowerShell:
.venv\Scripts\Activate.ps1
# Install requirements:
pip install -r requirements.txt
```

---

## 9. Running the Project

The application requires running the backend API and frontend dev servers concurrently.

### Terminal 1 — Backend FastAPI
```bash
cd backend
# Make sure virtual environment is active
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
*Expected output*: `Uvicorn running on http://127.0.0.1:8000`

### Terminal 2 — Frontend Vite React
```bash
cd frontend
npm run dev
```
*Expected output*: `Local: http://localhost:5173/`

### Terminal 3 — Mobile Client (React Native / Expo)
```bash
cd mobile
npm install
npm start
```
*Expected output*: Expo Developer Tools running on `http://localhost:19000/` or console QR code scan.

---

## 10. First-Time Setup Checklist

1.  **Environment Setup**: Copy `.env.example` to `.env` in the workspace root and fill in Clerk keys, MongoDB Atlas connection strings, and AI keys.
2.  **Install Packages**: Run `npm install` in `frontend/` and `pip install -r requirements.txt` inside your backend virtual environment.
3.  **Launch Servers**: Start backend (port 8000) and frontend (port 5173) services.
4.  **Register Clerk Account**: Navigate to `http://localhost:5173/` and sign up to create a real user session.
5.  **Seed Presentation Data**: Click the **Seed Demo Dataset** button on the dashboard to populate the database with mock concepts and attempts instantly for review.

---

## 11. Authentication Architecture

Passwords and password hashes are never stored in MongoDB. The system relies entirely on Clerk for authentication:
*   **Frontend**: Clerk JS SDK manages the session token.
*   **Token Verification**: For every protected endpoint, the client sends an `Authorization: Bearer <token>` header. The backend local decoder (`backend/app/auth.py`) checks the token's RS256 signature against Clerk's cached public JWKS keys.
*   **User Scoping**: Once validated, the `clerk_user_id` is extracted and used as the unique partition key for all database operations.

---

## 12. Database Schema

MK-Path uses a single MongoDB Atlas database. Collections are strictly user-scoped via `clerk_user_id`:

*   `user_profiles`: Clerk profile metadata (display name, email, avatar).
*   `materials`: PDF upload logs and extracted plain text.
*   `concepts`: Concepts extracted from materials (`material_id`, name, exam/industry weights, prereqs list).
*   `relationships`: Conceptual links (`source_concept_name`, `target_concept_name`, type).
*   `questions`: Sanitized MCQs associated with concepts.
*   `attempts`: Quiz attempt logs (selected answer index, correctness, time spent, confidence level).
*   `mastery`: Concept-specific rolling mastery scores, next review date, and categorization states.
*   `study_paths`: Current prioritized learning timeline.
*   `gamification`: Accumulated XP points, user level rank, and list of unlocked achievements.

---

## 13. API Specification

| Method | Endpoint | Authentication | Purpose / Description |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/health` | Public | System status and MongoDB online/offline connectivity check. |
| **GET** | `/api/me` | Clerk Token | Retrieves authenticated Clerk user details. |
| **GET** | `/api/user/profile` | Clerk Token | Lazily registers or updates user profile metadata in MongoDB. |
| **POST**| `/api/materials/upload` | Clerk Token | Accepts PDF, extracts text via PyMuPDF, and returns material details. |
| **GET** | `/api/materials` | Clerk Token | Retrieves list of materials owned by the active user. |
| **GET** | `/api/materials/{material_id}`| Clerk Token | Fetches detail and text preview of a specific material. |
| **POST**| `/api/materials/{material_id}/extract-concepts` | Clerk Token | Triggers AI concept and relationship extraction. |
| **GET** | `/api/concepts` | Clerk Token | Retrieves all concepts mapped for the user. |
| **GET** | `/api/concepts/{concept_id}`| Clerk Token | Fetches specific details of a concept. |
| **GET** | `/api/graph` | Clerk Token | Returns React Flow nodes and edges arranged in column grids. |
| **GET** | `/api/assessment` | Clerk Token | Retrieves all assessment questions generated for the user. |
| **POST**| `/api/assessment/generate` | Clerk Token | Generates new concept-focused MCQs, returning sanitized copies. |
| **POST**| `/api/assessment/submit` | Clerk Token | Submits attempts, calculates mastery scores, and logs gamification XP. |
| **GET** | `/api/mastery` | Clerk Token | Retrieves overall and per-concept mastery levels. |
| **GET** | `/api/study-path` | Clerk Token | Computes prioritized timeline pathing recommendations. |
| **GET** | `/api/resources` | Clerk Token | Filters external learning links matching weak concept areas. |
| **GET** | `/api/gamification` | Clerk Token | Returns user XP, level, and unlocked achievements. |
| **GET** | `/api/dashboard/stats` | Clerk Token | Gathers rolling stats, streak days, and due sessions for dashboard widgets. |
| **POST**| `/api/demo/load` | Clerk Token | Seeds default ML curriculum data scoped under current Clerk ID. |

*Mismatches with API_SPEC.md*: The actual implementation introduces `/api/dashboard/stats` and `/api/demo/load` to improve UI performance and presentation reliability. It replaces generic material ID routes with `{material_id}` naming parameters.

---

## 14. Development Workflow

Useful development commands:
*   **Start Frontend Dev Server**: `npm run dev` (inside `frontend/` folder)
*   **Compile Production Bundle**: `npm run build` (inside `frontend/` folder)
*   **Run Frontend Linter**: `npm run lint` (uses `oxlint` for fast inspections)
*   **Start Backend API**: `python -m uvicorn app.main:app --reload` (inside `backend/` folder)

---

## 15. Troubleshooting

*   **FastAPI returns 401 Unauthorized**:
    *   *Cause*: Token is missing or invalid.
    *   *Solution*: Check that your browser cookie contains a valid Clerk session. Ensure `VITE_CLERK_PUBLISHABLE_KEY` is set correctly on the frontend and matching keys are defined in the backend.
*   **MongoDB Atlas Connection Failure**:
    *   *Cause*: IP Address not whitelisted on Atlas dashboard or incorrect connection URI.
    *   *Solution*: Make sure Network Access is set to allow `0.0.0.0/0` (or your local IP) in the MongoDB Atlas console. Verify the password in `MONGODB_URI` does not contain unencoded special characters.
*   **AI API calls fail or timeout**:
    *   *Cause*: API rate limits or invalid key.
    *   *Solution*: Verify `GEMINI_API_KEY` is valid. If rate-limited, supply a comma-separated sequence of keys to enable rotation retries.
*   **CORS errors on frontend fetch**:
    *   *Cause*: FastAPI backend running on a different port than configured CORS origins.
    *   *Solution*: FastAPI CORS configuration allows all local loopback routes (`http://localhost:5173`, `http://127.0.0.1:5173`). Launch the frontend Vite server using `npm run dev` to ensure it is hosted on port 5173.

---

## 16. Security Notes

*   **Secrets Safety**: Never commit your `.env` file to version control. Key validation checks are performed on the server-side, and MongoDB URI details are completely invisible to the client.
*   **Server-Side Ownership Enforcement**: User scopes are determined directly from the decoded JWT token properties (`clerk_user_id`). The system ignores user ID declarations provided in HTTP request bodies or query headers to prevent account hijacking.

---

## 17. Current MVP Status

As recorded in `docs/MVP_STATUS.md`: **MVP COMPLETE**.
All core ingestion pipelines, AI concept extraction fallback routines, unified graphs, assessments, study paths, spaced repetition decays, and gamification ranks are fully implemented, verified, and active.

---

## 18. Quick Start

Start the application immediately using the following commands:

```bash
# 1. Clone the project
git clone <repository-url>
cd MKLP

# 2. Configure environment variables
# Copy .env.example to .env and configure Clerk/Atlas keys

# 3. Install frontend libraries & start Vite dev server
cd frontend
npm install
npm run dev &

# 4. Install backend dependencies & start FastAPI dev server
cd ../backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
