# AI Data Pipeline Orchestrator

Enterprise-grade data pipeline platform with a visual DAG builder, LLM-powered schema inference, data quality scoring, anomaly detection, and multi-cloud connector support.

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                          React Frontend                             │
│  ┌──────────────────┐  ┌──────────────┐  ┌─────────────┐           │
│  │  Pipeline Builder │  │   Pipelines  │  │    Jobs     │           │
│  │  (DAG drag-drop)  │  │  list/status │  │  history    │           │
│  └──────────────────┘  └──────────────┘  └─────────────┘           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐       │
│  │   Quality    │  │    Logs      │  │  DAGViewer Component │       │
│  │  score gauges │  │  log viewer  │  │  JobStatus/Score     │       │
│  └──────────────┘  └──────────────┘  └─────────────────────┘       │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ REST /api/*
┌──────────────────────────────▼─────────────────────────────────────┐
│                        FastAPI Backend                              │
│  ┌────────┐  ┌─────────────┐  ┌──────────────────────────────────┐  │
│  │  Auth   │  │ Middleware  │  │              Routes              │  │
│  │ OAuth2  │  │ Logging     │  │  /pipelines /jobs /quality /logs │  │
│  │ API Key │  │ Rate Limit  │  │  /connectors /schema /health     │  │
│  └────────┘  │ CORS        │  └──────────────────────────────────┘  │
│              └─────────────┘                                       │
│  ┌──────────────────────┐  ┌────────────────────────────────────┐  │
│  │   Orchestrator        │  │        Transforms                  │  │
│  │  Engine (DAG walker)  │  │  Clean / Validate / Enrich         │  │
│  │  Scheduler (retry)    │  │  (LLM schema inference)            │  │
│  │  Pipeline (DAG model) │  └────────────────────────────────────┘  │
│  └──────────────────────┘  ┌────────────────────────────────────┐  │
│  ┌──────────────────────┐  │        Connectors                  │  │
│  │      Monitoring        │  │  S3 / GCS / BigQuery / Postgres    │  │
│  │  Metrics / Alerts     │  └────────────────────────────────────┘  │
│  │  Quality / LLM        │  ┌────────────────────────────────────┐  │
│  └──────────────────────┘  │        LLM Integration             │  │
│                            │  Schema inference / Anomaly detect  │  │
│                            └────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/ALANDVO/ai-data-pipeline-alan-vo.git
cd ai-data-pipeline-alan-vo
cp .env.example .env
docker compose up -d
# Open http://localhost:8000
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | OAuth2 or email login |
| `GET` | `/api/auth/me` | Get current user |
| `GET` | `/api/auth/api-keys` | List API keys |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/pipelines` | List pipelines |
| `POST` | `/api/pipelines` | Create pipeline (DAG) |
| `GET` | `/api/pipelines/{id}` | Get pipeline details |
| `POST` | `/api/pipelines/{id}/validate` | Validate DAG (topological sort) |
| `POST` | `/api/pipelines/{id}/run` | Trigger pipeline execution |
| `GET` | `/api/jobs` | Job execution history |
| `GET` | `/api/jobs/{id}` | Job status & task results |
| `POST` | `/api/jobs/{id}/retry` | Retry failed job |
| `GET` | `/api/quality` | Data quality scores |
| `GET` | `/api/logs` | Pipeline log stream |
| `POST` | `/api/schema/infer` | LLM-powered schema inference |
| `GET` | `/api/connectors` | List configured connectors |
| `POST` | `/api/anomaly/detect` | Anomaly detection with LLM |

## SSO Setup

### OAuth2
1. Register your app with the OAuth provider (Google, Okta, etc.)
2. Set `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET` in `.env`
3. Set `OAUTH_REDIRECT_URI` to `https://yourdomain.com/api/auth/callback`
4. Users sign in via the frontend "Sign in with SSO" button

### API Keys
1. Log in via OAuth2
2. Navigate to the Settings panel
3. Generate an API key via `POST /api/auth/api-keys`
4. Use the key in the `X-API-Key` header for programmatic access

## Tech Stack

Python 3.11, FastAPI, OAuth2, React 18, TypeScript, Vite, Docker

## License

MIT — see [LICENSE](LICENSE)

---

**Built by [Alan Vo](https://github.com/ALANDVO)** | alanvo@gmail.com | AI, ML & Data Engineering
