# MK-PATH DEVELOPMENT RULES

## DATABASE RULES
1. MongoDB Atlas is the only database.
2. Do not install local MongoDB.
3. Do not use Docker MongoDB.
4. Do not introduce PostgreSQL.
5. Do not introduce SQLite.
6. Do not introduce Neo4j.
7. Read connection string only from .env.
8. Use async MongoDB access.
9. All collections must be created lazily.
10. Handle Atlas connection failures gracefully.
11. Application must still work in Demo Mode when Atlas is unavailable.

## DEVELOPMENT & ARCHITECTURE RULES
1. Inspect before modifying.
2. Never rewrite the entire project for a small feature.
3. Reuse existing components.
4. Do not duplicate API clients or services.
5. Do not add dependencies without necessity.
6. Do not change the chosen technology stack (FastAPI backend, React/Vite frontend).
7. Use .env for credentials. Do not expose secrets or check them into source control.
8. All AI operations and database access must happen through the FastAPI backend. The frontend must never directly access MongoDB or server secrets.
9. Clerk is the exclusive authentication provider. No password-based users collection or mock authentication. All application data belongs to real authenticated users.
10. Validate AI output (structured JSON) before database insertion.
11. XP must represent meaningful learning (e.g., quiz completed, correct answers, weak concept improvement).
12. Keep generated explanations concise.
13. Prefer editing targeted sections instead of recreating entire files.