# Autonomous Software Company (ASC)

> A production-grade multi-agent AI platform that functions like a complete software company.

[![Qwen Cloud Global AI Hackathon](https://img.shields.io/badge/Hackathon-Qwen%20Cloud-blue)](https://hackathon.qwen.cloud)
[![Track 3 - Agent Society](https://img.shields.io/badge/Track-Agent%20Society-purple)](https://hackathon.qwen.cloud)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🚀 Overview

**ASC** orchestrates **14 specialized AI agents** that collaborate, negotiate, plan, build, review, test, deploy, and maintain software products from a single user request.

Instead of using a single AI assistant, ASC functions like a complete engineering organization:

```
User Request → CEO → PM → Research → Architect → UI/UX → Frontend + Backend
→ Security → QA → Reviewer → DevOps → Documentation → Memory → Deploy
```

### Example

> "Build a hospital management SaaS with mobile apps, admin dashboard, payment integration, and AI appointment scheduling."

ASC automatically:
- ✅ Understands requirements
- ✅ Performs research
- ✅ Creates a PRD
- ✅ Designs system architecture
- ✅ Generates UI
- ✅ Writes frontend & backend
- ✅ Designs database
- ✅ Creates APIs
- ✅ Generates infrastructure
- ✅ Performs QA & Security review
- ✅ Reviews code
- ✅ Documents everything
- ✅ Deploys to cloud

---

## 🧠 Agent Team

| # | Agent | Role | Key Outputs |
|---|-------|------|-------------|
| 1 | **CEO** | Project vision, milestones, conflict resolution | Roadmap, Sprint Plan |
| 2 | **Product Manager** | PRD, user stories, prioritization | Product Specification |
| 3 | **Researcher** | Tech research, competitor analysis | Research Report |
| 4 | **Architect** | System design, APIs, scalability | Architecture Diagram |
| 5 | **UI/UX Designer** | User flows, wireframes, design tokens | UI Screens |
| 6 | **Frontend Engineer** | React/Next.js, Tailwind, state management | Production Frontend |
| 7 | **Backend Engineer** | APIs, auth, services, queues | Production Backend |
| 8 | **Database Engineer** | SQL, indexes, migrations | Schema, ER Diagram |
| 9 | **DevOps Engineer** | Docker, K8s, CI/CD, monitoring | Infrastructure |
| 10 | **Security Engineer** | OWASP, secrets, RBAC | Security Report |
| 11 | **QA Engineer** | Unit, integration, E2E tests | Test Report |
| 12 | **Reviewer** | Code review, best practices | Review Notes |
| 13 | **Documentation** | README, API docs, user manual | Complete Docs |
| 14 | **Memory Agent** | Persistent memory across 5 tiers | Context & Recall |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 15)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │  Agent   │ │Workflow  │ │ Memory   │ │  Deployment   │  │
│  │  Panel   │ │  Graph   │ │ Explorer │ │  Dashboard    │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │  Agent   │ │ Workflow │ │ Memory   │ │    Tools      │  │
│  │  System  │ │  Engine  │ │  System  │ │   (MCP, Git)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└──────┬────────────┬────────────┬──────────────┬────────────┘
       │            │            │              │
┌──────▼──┐ ┌──────▼──┐ ┌──────▼──┐ ┌────────▼────────┐
│PostgreSQL│ │  Redis  │ │ Qdrant  │ │     Neo4j       │
│ (Primary)│ │ (Cache) │ │(Vectors)│ │ (Knowledge Graph)│
└─────────┘ └─────────┘ └─────────┘ └─────────────────┘
```

### Memory Architecture (5 Tiers)

```
Working Memory → Session Memory → Project Memory → Organization Memory → Long-Term Memory
     ↓                ↓                ↓                   ↓                    ↓
  Current Task    Conversation    Project History    Cross-Project       Semantic Knowledge
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS, Recharts |
| **Backend** | FastAPI, Python 3.12, Celery, Redis |
| **Database** | PostgreSQL 16, Qdrant (vectors), Neo4j (graph) |
| **AI/LLM** | Qwen (DashScope) OpenAI-compatible API |
| **Infrastructure** | Docker, Docker Compose, Kubernetes, Prometheus, Grafana |
| **Cloud** | Alibaba Cloud ECS, OSS, RDS, API Gateway |
| **Storage** | MinIO (S3-compatible object storage) |

---

## 🚦 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose (for infrastructure)
- Qwen API key from [Alibaba Cloud DashScope](https://dashscope.aliyuncs.com)

### Quick Start (Development)

#### 1. Clone and setup backend

```bash
cd asc/backend
cp .env.example .env
# Edit .env and add your QWEN_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

#### 2. Setup frontend

```bash
cd asc/frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`

#### 3. Run with Docker (full stack)

```bash
cd asc/infrastructure
docker compose up -d
```

This starts all services: backend, frontend, PostgreSQL, Redis, Qdrant, Neo4j, MinIO, Prometheus, and Grafana.

---

## 📡 API Endpoints

### Workflows
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/workflows` | Start a new software development workflow |
| `GET` | `/api/v1/workflows/{id}` | Get workflow status |
| `POST` | `/api/v1/workflows/{id}/approve` | Approve a workflow (human-in-the-loop) |
| `GET` | `/api/v1/workflows/{id}/graph` | Get workflow execution DAG |
| `GET` | `/api/v1/workflows/{id}/outputs` | Get all generated outputs |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/agents` | Get status of all agents |

### Memory
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/memory/search` | Search through memory |
| `GET` | `/api/v1/memory/stats` | Get memory system statistics |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/dashboard/agents` | Agent statuses for dashboard |
| `GET` | `/api/v1/dashboard/workflows` | All workflow summaries |
| `GET` | `/api/v1/dashboard/costs` | Token and cost metrics |
| `GET` | `/api/v1/dashboard/deployment` | Deployment status |

### WebSocket
| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/api/v1/ws/{workflow_id}` | Real-time workflow updates |

---

## 🎯 Workflow Modes

| Mode | Description |
|------|-------------|
| **Autonomous** | Full pipeline runs without human intervention |
| **Approval** | Pauses at key gates (PRD, Architecture, UI, Deployment) for human approval |
| **Manual** | Each step requires explicit human confirmation |

### Approval Gates
- PRD Approval
- Architecture Approval
- UI Approval
- Production Deployment
- Major Refactoring
- Security Exceptions

---

## 📊 Dashboard Features

- **Live Agent Panel** - Real-time status of all 14 agents
- **Workflow Graph** - Visual DAG showing agent execution and dependencies
- **Memory Explorer** - Timeline, semantic search, knowledge graph
- **Cost Dashboard** - Token usage, API calls, agent runtime
- **Deployment Dashboard** - Build status, health, rollback

---

## 🧪 Demo Script (3 Minutes)

1. Enter: *"Build an Airbnb clone for pet boarding"*
2. CEO Agent decomposes the request into milestones
3. Product Manager generates a complete PRD
4. Research Agent gathers technical references
5. Architect produces system design and API plan
6. Frontend, Backend, Database, and DevOps agents work in parallel
7. Security and QA agents detect issues and send them back
8. Reviewer Agent approves the final implementation
9. Memory Agent recalls user's preferred stack and applies it
10. DevOps Agent deploys to Alibaba Cloud
11. Dashboard visualizes everything in real-time

---

## 🗺️ Future Roadmap

- [ ] Voice-driven engineering workflows
- [ ] Self-improving agents using reinforcement learning
- [ ] Cross-project organizational memory
- [ ] Marketplace for reusable agents and workflows
- [ ] Autonomous bug fixing from production telemetry
- [ ] IDE extensions (VS Code, JetBrains)
- [ ] Mobile companion application
- [ ] Enterprise SSO and advanced RBAC
- [ ] Multi-cloud deployment orchestration
- [ ] Open-source plugin ecosystem

---

## 🏆 Hackathon Tracks

| Track | Focus | How ASC Addresses It |
|-------|-------|---------------------|
| **Track 1** | MemoryAgent | 5-tier memory system with importance scoring, consolidation, and semantic recall |
| **Track 3** | Agent Society | 14 specialized agents with structured communication, negotiation, and conflict resolution |
| **Track 4** | Autopilot Agent | Fully autonomous workflow engine with human-in-the-loop approval gates |

---

## 🔧 Production Notes

- **CORS**: the API only accepts requests from origins listed in `CORS_ORIGINS`
  (comma-separated). Set it to your real dashboard URL in production — it
  defaults to the local dev origins and is never the wildcard when credentials
  are enabled.
- **Secrets**: always set a strong `SECRET_KEY`. The shipped default must be
  overridden before any deployment.
- **Observability**: a Prometheus `/metrics` endpoint exposes `asc_workflows_total`
  and `asc_agents_total` gauges; point Prometheus at it (see
  `infrastructure/prometheus.yml`).
- **Database & memory**: Postgres, Redis, Qdrant, and Neo4j are optional. When
  unavailable the platform degrades gracefully (in-memory users, in-memory
  workflow state, in-memory vector/graph memory) so it still runs for local demos.
- **Background workflows**: `POST /api/v1/workflows/background` runs the pipeline
  in a Celery worker; its state is persisted and visible to the API/dashboard.

---

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Qwen Cloud](https://qwen.cloud) for the AI model APIs
- [Alibaba Cloud](https://alibabacloud.com) for cloud infrastructure
- All open-source libraries that made this possible