# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-13

### Added
- Initial project structure with FastAPI backend and React/TypeScript frontend
- Visual DAG pipeline builder with drag-and-drop node/edge editing
- Pipeline CRUD: create, list, validate (topological sort), execute
- Job scheduler with parallel execution groups, retry with exponential backoff
- LLM-powered schema inference (OpenAI-compatible, Anthropic, Gemini, Ollama)
- Local fallback schema inference and anomaly detection without LLM keys
- Data quality scoring: completeness, accuracy, consistency, timeliness
- Multi-cloud connectors: AWS S3, Google Cloud Storage, BigQuery, PostgreSQL
- Real-time log viewer with level filtering and search
- OIDC/Keycloak authentication with PKCE (authorization code flow)
- Role-based access: admin, data_engineer, analyst
- Docker Compose with Keycloak, PostgreSQL, backend, frontend, nginx
- CI/CD pipeline: backend pytest, frontend TypeScript/Vitest, Docker builds
- Comprehensive test suite (13 backend tests, 6 frontend tests)

### Changed
- Restructured codebase to required `backend/app/` layout with `api/`, `services/`, `models/`, `core/`
- Migrated from mock auth to Keycloak OIDC with realm import
- Added SQLite persistence layer foundation for pipelines and jobs

### Security
- JWT tokens with HS256 signing, configurable expiry
- PKCE enforcement for SPA clients
- Rate limiting middleware (60 req/min default)
- Non-root Docker users, healthchecks
- No hardcoded secrets; all credentials via environment variables

## [Unreleased]

### Planned
- Full SQLite persistence with Alembic migrations
- Complete Keycloak integration tests
- SAML identity broker documentation
- Pipeline template marketplace
- Webhook notifications for job events