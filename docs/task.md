# Tasks - Learner Event Log, Graph Layer, BKT, and Adaptive Quiz

## Phase 13: Learner Event and Behavior Data Foundation
- [x] Add `LearnerEvent` Pydantic model in `backend/app/models.py`
- [x] Extend `Mastery` model in `backend/app/models.py`
- [x] Implement `create_learner_event` and `get_learner_events` in `backend/app/crud.py`
- [x] Implement event analytics aggregations in `backend/app/crud.py`

## Phase 14: Neo4j Graph Intelligence Layer
- [x] Create `backend/app/services/neo4j_service.py` with fallback drivers
- [x] Implement concept/relationship synchronization hooks in `Neo4jService`
- [x] Implement graph traversals (prerequisites, shortest paths, centrality) in `Neo4jService`

## Phase 15: Bayesian Knowledge Tracing (BKT)
- [x] Create BKT model update algorithms in `backend/app/services/kt_service.py`
- [x] Implement BKT Shadow Mode updates on assessment submissions
- [x] Implement BKT evaluation API (Brier score / Accuracy) and data-driven promotion route

## Phase 16: Adaptive Quiz Policy
- [x] Create question selection policy in `backend/app/services/adaptive_policy.py`
- [x] Implement dynamic difficulty adaptation and information-gain concept search
- [x] Expose API endpoints in `backend/app/main.py` and connect frontend dashboard event triggers

## Phase 17: Graph-Aware Intelligent Study Path Planner
- [x] Create base `StudyPathPlanner` abstractions in `backend/app/services/planner.py`
- [x] Implement `BaselinePlanner` and `GraphAwarePlanner` with prerequisite mastery locks
- [x] Add explainability reasons to all recommended concept items

## Phase 18: Reinforcement Learning Study-Path Planner
- [x] Create simulated learner environment `LearnerSimulationEnv` modeling mastery vectors and forgetting
- [x] Implement tabular Q-learning model `RLStudyPathPlanner` trained on simulated environment
- [x] Expose evaluation `/api/planner/evaluate` and promotion `/api/planner/promote` endpoints in `main.py`

## Verification
- [x] Write integration test verification script `backend/app/services/test_analytics_and_intelligence.py`
- [x] Run test scripts and start backend/frontend servers
- [x] Update status documents and documentation stacks
