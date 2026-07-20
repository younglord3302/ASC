# Autonomous Software Company (ASC)

> A production-grade, multi-tenant multi-agent AI platform that behaves like a complete software company — turning a single prompt into researched, designed, built, reviewed, tested, and deployed software.

[![Qwen Cloud Global AI Hackathon](https://img.shields.io/badge/Hackathon-Qwen%20Cloud-blue)](https://hackathon.qwen.cloud)
[![Track 3 - Agent Society](https://img.shields.io/badge/Track-Agent%20Society-purple)](https://hackathon.qwen.cloud)
[![Tests](https://img.shields.io/badge/tests-83%20backend%20%2B%2021%20frontend-brightgreen)](#-testing)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Overview

**ASC** orchestrates **14 specialized AI agents** that collaborate, negotiate, plan, build, review, test, deploy, and document software from a single user request. Instead of one AI assistant, ASC works like a full engineering organization.

```
User Request → CEO → PM → Research → Architect → UI/UX → Frontend + Backend
→ Database → DevOps → Security → QA → (feedback loop) → Reviewer → Docs → Memory → Deploy
```

Ask for *"Build a hospital management SaaS with an admin dashboard and payment integration"* and ASC decomposes it into milestones, writes a PRD, designs the architecture, generates frontend/backend/database/infra, runs security + QA with a real fix-it feedback loop, reviews the result, documents it, and deploys — all visualized live on the dashboard.

---

## Highlights

- **14-agent society** with structured messaging and a QA/Security → engineer **feedback loop** (agents actually revise each other's work).
- **Multi-tenant** — every workflow and memory is scoped to the owning user; cross-user access is rejected.
- **Role-based access control** — first user is bootstrapped as `admin`; admin-only endpoints for users, all-workflows, and audit.
- **Human-in-the-loop** approval gates (Autonomous / Approval / Manual modes).
- **5-tier memory** with semantic recall and an optional knowledge graph.
- **Tool system** — an extensible, sandbox-safe tool registry agents can call during a workflow.
- **Production hardening** — LLM retries with backoff, per-workflow token budget, API rate limiting, audit logging, CORS allow-list, Prometheus metrics, and opt-in OpenTelemetry tracing.
- **Graceful degradation** — runs with zero external services (in-memory users, workflows, and memory) for instant local demos.

---

## Agent Team

| # | Agent | Role | Key Outputs |
|---|-------|------|-------------|
| 1 | **CEO** | Vision, milestones, conflict resolution | Roadmap |
| 2 | **Product Manager** | PRD, user stories, prioritization | Product Spec |
| 3 | **Researcher** | Tech + competitor research | Research Report |
| 4 | **Architect** | System design, APIs, scalability | Architecture |
| 5 | **UI/UX Designer** | Flows, wireframes, design tokens | UI Spec |
| 6 | **Frontend Engineer** | React/Next.js, Tailwind | Frontend Code |
| 7 | **Backend Engineer** | APIs, auth, services | Backend Code |
| 8 | **Database Engineer** | Schema, indexes, migrations | DB Schema |
| 9 | **DevOps Engineer** | Docker, CI/CD, monitoring | Infrastructure |
| 10 | **Security Engineer** | OWASP, secrets, RBAC review | Security Report |
| 11 | **QA Engineer** | Unit/integration/E2E + tool-computed metrics | Test Report |
| 12 | **Reviewer** | Code review, best practices | Review Notes |
| 13 | **Documentation** | README, API docs, manuals | Docs |
| 14 | **Memory Agent** | Persistent memory across 5 tiers | Context & Recall |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 15)                    │
│   Agent Panel · Workflow Graph · Memory Explorer · Costs     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / WebSocket (JWT auth)
┌──────────────────────▼──────────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  Auth/RBAC · Workflow Engine · Agent System · Memory · Tools │
│  Rate limiting · Audit log · Metrics · Tracing · Celery      │
└──────┬────────────┬────────────┬──────────────┬─────────────┘
       │            │            │              │
┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐  ┌────────▼─────────┐
│PostgreSQL│  │  Redis  │  │ Qdrant  │  │       Neo4j      │
│ (Primary)│  │ (Queue) │  │(Vectors)│  │ (Knowledge Graph)│
└──────────┘  └─────────┘  └─────────┘  └──────────────────┘
   (all external services optional — in-memory fallbacks exist)
```

### Memory (5 tiers)

```
Working → Session → Project → Organization → Long-Term
  task     convo     history    cross-project   semantic recall
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts, Vitest |
| **Backend** | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy (async), Celery |
| **Auth** | JWT (OAuth2 bearer), bcrypt password hashing, RBAC |
| **Data** | PostgreSQL 16, Redis, Qdrant (vectors), Neo4j (graph), MinIO |
| **AI/LLM** | Qwen (DashScope) via OpenAI-compatible API |
| **Ops** | Docker Compose, Prometheus, OpenTelemetry, SlowAPI rate limiting |

---

## Getting Started

### Prerequisites
- Python 3.12+, Node.js 20+
- (Optional) Docker & Docker Compose for the full stack
- A Qwen API key from [Alibaba Cloud DashScope](https://dashscope.aliyuncs.com)

### Backend
```bash
cd asc/backend
cp .env.example .env          # add your QWEN_API_KEY and a strong SECRET_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload
```
- API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

> ASC runs even without Postgres/Redis/Qdrant/Neo4j — it falls back to in-memory
> stores so you can demo immediately. Provide an LLM key for real agent output.

### Frontend
```bash
cd asc/frontend
npm install
npm run dev
```
- Dashboard: `http://localhost:3000`

### Full stack (Docker)
```bash
cd asc/infrastructure
docker compose up -d
```
Starts backend, frontend, PostgreSQL, Redis, Qdrant, Neo4j, MinIO, and Prometheus.

---

## Authentication & Roles

1. `POST /api/v1/auth/register` — the **first registered user becomes `admin`**; everyone after is a `user`.
2. `POST /api/v1/auth/login` — returns a JWT bearer token.
3. Send `Authorization: Bearer <token>` on all workflow, memory, tool, and admin calls.

Workflows and memory are **scoped per user**. A user can only see and act on their own workflows; admins get cross-user visibility via the `/admin/*` endpoints.

---

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Create account (first user = admin) |
| `POST` | `/api/v1/auth/login` | Obtain a JWT token |
| `GET`  | `/api/v1/auth/me` | Current user (incl. role) |

### Workflows *(auth required, user-scoped)*
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/workflows` | Start a workflow |
| `POST` | `/api/v1/workflows/background` | Start a workflow via Celery worker |
| `GET`  | `/api/v1/workflows/{id}` | Status |
| `POST` | `/api/v1/workflows/{id}/approve` | Approve at a gate |
| `POST` | `/api/v1/workflows/{id}/deploy` | Deploy a completed workflow |
| `GET`  | `/api/v1/workflows/{id}/graph` | Execution DAG |
| `GET`  | `/api/v1/workflows/{id}/outputs` | Generated outputs |
| `GET`  | `/api/v1/workflows/{id}/messages` | Agent conversation transcript |

### Memory, Agents & Tools *(auth required)*
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/memory/search` | Semantic/keyword memory search |
| `GET`  | `/api/v1/memory/stats` | Memory statistics |
| `GET`  | `/api/v1/memory/related/{id}` | Knowledge-graph neighbors |
| `GET`  | `/api/v1/agents` | Agent statuses |
| `GET`  | `/api/v1/tools` | Available agent tools + schemas |

### Dashboard *(auth required)*
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboard/agents` | Agent statuses |
| `GET` | `/api/v1/dashboard/workflows` | This user's workflows |
| `GET` | `/api/v1/dashboard/costs` | Token/cost metrics |
| `GET` | `/api/v1/dashboard/deployment` | Deployment status |

### Admin *(admin role required)*
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/admin/users` | List all accounts |
| `GET` | `/api/v1/admin/workflows` | All workflows across users |
| `GET` | `/api/v1/audit` | Audit event log |

### Ops & Realtime
| Endpoint | Description |
|----------|-------------|
| `GET /metrics` | Prometheus metrics (root path) |
| `GET /api/v1/health` | Health check |
| `ws://localhost:8000/api/v1/ws/{id}` | Real-time workflow updates |

---

## Workflow Modes

| Mode | Behavior |
|------|----------|
| **Autonomous** | Full pipeline runs end-to-end without pauses |
| **Approval** | Pauses at the PRD gate for human approval, then continues |
| **Manual** | Each step requires explicit confirmation |

**Agent feedback loop:** after QA and Security run, their findings are routed back to the Frontend/Backend engineers for a structured fix pass, and the revised artifacts replace the originals.

---

## Tool System

Agents can call registered tools during a workflow. The registry exposes each tool to the LLM in OpenAI/Qwen function-calling format and executes safely (`safe_execute` never crashes the pipeline; sync tools run off the event loop).

Built-in, sandbox-safe tools:
- `calculator` — arithmetic via an AST allow-list (rejects unsafe input)
- `json_format` — pretty-print/validate JSON
- `word_count` — words/characters (used by QA to produce deterministic code metrics)

Add your own with the `@tool` decorator in `app/tools/`, then it appears at `GET /api/v1/tools` and is callable by any agent via `agent.use_tool(name, args)`.

---

## Production & Configuration

Configure via environment variables (see `asc/backend/.env.example`):

| Setting | Purpose |
|---------|---------|
| `SECRET_KEY` | **Set a strong value** — signs JWTs |
| `CORS_ORIGINS` | Comma-separated allow-list (never wildcard with credentials) |
| `LLM_MAX_RETRIES`, `LLM_RETRY_BACKOFF`, `LLM_TIMEOUT` | LLM resilience |
| `MAX_TOKENS_PER_WORKFLOW` | Hard token budget per run (stops runaway cost) |
| `MEMORY_BACKEND`, `GRAPH_ENABLED` | Memory: `memory`/`qdrant`, optional Neo4j graph |
| `OTEL_ENABLED`, `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP` | OpenTelemetry tracing (opt-in) |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Background workflow queue |

Operational features:
- **Rate limiting** on auth/workflow endpoints (SlowAPI) → HTTP 429 when exceeded.
- **Audit logging** of register/login/workflow/deploy/admin events (`GET /api/v1/audit`, admin only).
- **Observability**: Prometheus `/metrics` gauges; OpenTelemetry spans for HTTP requests, workflow phases, and LLM calls (console or OTLP export).
- **Graceful degradation**: unavailable Postgres/Redis/Qdrant/Neo4j never block requests — the platform fast-fails and uses in-memory fallbacks.

---

## Testing

```bash
# Backend (from asc/backend, venv active)
pytest -q

# Frontend (from asc/frontend)
npm test -- --run
npm run build
```

Current status: **83 backend tests + 21 frontend tests passing**, frontend build clean. The suite runs fully offline (LLM mocked, persistence best-effort) — no external services required.

---

## Project Structure

```
asc/
├── backend/
│   ├── app/
│   │   ├── agents/       # BaseAgent + 14 specialized agents
│   │   ├── api/          # FastAPI routes, deps (auth/RBAC), rate limiter
│   │   ├── core/         # config, llm, security, users, audit, tracing
│   │   ├── memory/       # 5-tier memory system + backends
│   │   ├── models/       # pydantic schemas, SQLAlchemy models, persistence
│   │   ├── tools/        # tool registry + built-in tools
│   │   └── workflow/     # workflow engine (pipeline, feedback loop, budget)
│   └── tests/            # pytest suite
├── frontend/             # Next.js 15 dashboard
└── infrastructure/       # docker-compose, prometheus config
```

---

## Roadmap

- [ ] Admin UI panel in the dashboard
- [ ] Real tool integrations behind an allow-list (read-only git/filesystem)
- [ ] Per-user rate-limit tiers and quotas
- [ ] Self-improving agents from production telemetry
- [ ] IDE extensions and enterprise SSO
- [ ] Multi-cloud deployment orchestration

---

## Hackathon Tracks

| Track | How ASC addresses it |
|-------|----------------------|
| **Track 1 — MemoryAgent** | 5-tier memory with importance scoring, semantic recall, and a knowledge graph |
| **Track 3 — Agent Society** | 14 agents with structured communication, negotiation, and a QA/Security feedback loop |
| **Track 4 — Autopilot Agent** | Autonomous workflow engine with human-in-the-loop approval gates |

---

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [Qwen Cloud](https://qwen.cloud) for the model APIs
- [Alibaba Cloud](https://alibabacloud.com) for cloud infrastructure
- The open-source community behind FastAPI, Next.js, and the wider ecosystem
