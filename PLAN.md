# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

sqlite-persistence

## Roadmap

### restructure-and-ci — Restructure to required layout with CI and proper auth

Status: done

Acceptance:
- Code reorganized into backend/app/ with api/, services/, models/, core/
- Frontend has Dockerfile and package-lock.json
- compose.yaml with Keycloak, PostgreSQL, and persistent volumes
- CI workflow running backend/frontend tests and Docker builds
- Portfolio.json at root with correct metadata
- pyproject.toml with author metadata
- CHANGELOG.md with actual changes
- OIDC/Keycloak auth foundation (backend validation, frontend PKCE client)
- SQLite persistent storage foundation

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/api/routes.py`, `backend/app/services/orchestrator/engine.py`, `backend/app/services/transforms/llm.py`, `backend/Dockerfile`, `frontend/Dockerfile`, `compose.yaml`, `.github/workflows/ci.yml`, `portfolio.json`, `pyproject.toml`, `CHANGELOG.md`

Tests: `backend/tests/test_core.py (13 tests)`, `frontend/src/pages/Quality.test.tsx (6 tests)`

### sqlite-persistence — SQLite persistent storage for pipelines and jobs

Status: in_progress

Acceptance:
- Pipelines and jobs persisted to SQLite database
- Survives container restarts
- Alembic migrations for schema management

### oidc-keycloak-auth — Real OIDC/Keycloak authentication

Status: planned

Acceptance:
- Authorization code flow with PKCE
- Keycloak realm import configuration
- Backend token validation with issuer/audience check
- Frontend SPA PKCE client with in-memory tokens
- Logout with Keycloak end-session endpoint

### complete-test-suite — Complete test suite (12 backend, 3 frontend)

Status: planned

Acceptance:
- 12+ meaningful backend pytest tests covering domain logic, auth, persistence
- 3+ frontend vitest tests for user-visible behavior
- Tests mock external providers, no real credentials

