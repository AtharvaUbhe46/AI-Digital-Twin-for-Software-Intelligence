# AI Digital Twin System for Software Intelligence

> **B.Tech CSE Major Project** — An autonomous AI-powered digital twin for software repositories that maintains an active virtual representation of project health, architecture, risk hotspots, and future evolution.

[![Phase 1: Foundation](https://img.shields.io/badge/Status-Phase%201%20Foundation%20Complete-emerald)](./)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](./backend)
[![React](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript-61DAFB?logo=react&logoColor=black)](./frontend)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?logo=postgresql&logoColor=white)](./)
[![Docker](https://img.shields.io/badge/Containerization-Docker%20Compose-2496ED?logo=docker&logoColor=white)](./)

---

## 📑 Overview & Architecture

The **AI Digital Twin for Software Intelligence** mirrors a software project's reality in a dynamic computational model. It continuously tracks code commits, pull requests, issues, developer collaboration graphs, and code churn to predict risk hotspots, measure project health, explain anomalies using AI, and run what-if simulations.

### Logical System Pipeline
```
GitHub Repository
       ↓
Data Collection Layer
       ↓
Normalization & Preprocessing
       ↓
PostgreSQL (Relational Store) + Neo4j (Knowledge Graph)
       ↓
Digital Twin Core State Engine
       ↓
Analytics & ML Risk Prediction Engine
       ↓
FastAPI Backend (Async REST API)
       ↓
React + Vite Intelligence Dashboard
```

---

## 🗂️ Project Directory Structure

```
AI Digital twin for Software Intelligence/
├── .env                          # Local environment variables
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore specifications
├── docker-compose.yml            # Multi-container orchestration (Postgres, Backend, Frontend)
├── README.md                     # Engineering documentation
│
├── backend/                      # FastAPI Python Backend
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py        # System & DB ping endpoint
│   │   │       │   └── projects.py      # Projects & dashboard summary endpoints
│   │   │       └── router.py            # Aggregated API router
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic Settings configuration
│   │   │   └── database.py              # SQLAlchemy 2.0 connection pool & health ping
│   │   ├── models/
│   │   │   ├── base.py                  # Common TimeStampedModel
│   │   │   └── project.py               # Project & MetricSnapshot models
│   │   ├── schemas/
│   │   │   ├── health.py                # Pydantic health validation schemas
│   │   │   └── project.py               # Project & summary schemas
│   │   ├── services/
│   │   │   └── project_service.py       # Reusable service business logic
│   │   └── main.py                      # FastAPI app entrypoint, CORS & lifespan
│   ├── tests/
│   │   └── test_health.py               # Pytest health check tests
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
│
└── frontend/                     # React + TypeScript + Vite Frontend
    ├── src/
    │   ├── components/
    │   │   ├── common/
    │   │   │   ├── Header.tsx           # Telemetry status bar & repo selector
    │   │   │   ├── Sidebar.tsx          # 12-section SaaS navigation
    │   │   │   └── StatCard.tsx         # KPI metric cards with trends
    │   │   └── dashboard/
    │   │       ├── ActivityChart.tsx    # Recharts commit/PR velocity visualizer
    │   │       ├── HealthScoreGauge.tsx # Explainable health score breakdown
    │   │       ├── ModuleRiskTable.tsx  # Component risk & churn table
    │   │       └── SystemStatusBanner.tsx # Live backend & DB monitor
    │   ├── pages/
    │   │   ├── DashboardPage.tsx        # High-density intelligence dashboard
    │   │   └── PlaceholderPage.tsx      # Roadmap preview for upcoming phases
    │   ├── services/
    │   │   └── api.ts                   # Axios client with error handling
    │   ├── types/
    │   │   └── index.ts                 # Typed TypeScript models
    │   ├── App.tsx                      # App container & auto-polling
    │   ├── index.css                    # Tailwind directives & sleek dark styling
    │   └── main.tsx                     # React 18 DOM mount point
    ├── index.html
    ├── package.json
    ├── postcss.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── vite.config.ts
    └── Dockerfile
```

---

## 🚀 Quick Start Guide

You can run the system using **Docker Compose** (recommended for all-in-one execution) or run the components **locally on your machine**.

### Option A: Running with Docker Compose (Recommended)

Make sure Docker and Docker Compose are installed and running.

1. **Clone or navigate to the project directory:**
   ```bash
   cd "c:/Users/atharva_ubhe/Desktop/AI Digital twin for Software Intelligence"
   ```

2. **Launch all containers:**
   ```bash
   docker compose up --build
   ```

3. **Access the application:**
   - **Frontend UI:** [http://localhost:5173](http://localhost:5173)
   - **Backend API:** [http://localhost:8000](http://localhost:8000)
   - **Interactive API Docs (Swagger):** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - **System & DB Health Check:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

4. **Stop the containers:**
   ```bash
   docker compose down
   ```

---

### Option B: Running Locally (Native Development)

#### 1. Start PostgreSQL
You can run a quick PostgreSQL container or use a local instance:
```bash
docker run --name digital_twin_postgres -e POSTGRES_DB=software_digital_twin -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16-alpine
```

#### 2. Start the FastAPI Backend
```bash
cd backend

# Create virtual environment (optional but recommended)
python -m venv venv
venv\Scripts\activate      # On Windows
# source venv/bin/activate # On Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Launch FastAPI with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Start the React Frontend
Open a new terminal window:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## 📡 Core API Endpoints (Phase 1)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | API status and links to documentation |
| `GET` | `/api/v1/health` | Live system and PostgreSQL connection status & latency |
| `GET` | `/api/v1/projects` | List active software projects in the Digital Twin |
| `GET` | `/api/v1/dashboard/summary` | Aggregate health score, risk counts, module risks, and activity feed |
| `GET` | `/api/v1/docs` | Interactive OpenAPI / Swagger documentation |

---

## 🧪 Testing

Run backend tests using `pytest`:
```bash
cd backend
pytest tests/
```

Run frontend production build verification:
```bash
cd frontend
npm run build
```

---

## 🏥 Phase 4: Software Health & Risk Detection

> **Important Clarification:** Health scores are deterministic engineering indicators derived from repository activity, review velocity, issue aging, and contributor distributions; they are not absolute measures of software quality or individual developer performance.

### 1. Software Health Engine
The Software Health module evaluates 6 distinct dimensions with configurable weights and dynamic reweighting:
- **Repository Activity Health (`activity`, weight: 20%):** Commit frequency, recency of last commit, active authors in recent window.
- **Issue Health (`issues`, weight: 20%):** Open backlog size, stale issues exceeding configured threshold (`HEALTH_STALE_ISSUE_DAYS`), resolution/closure rate.
- **Pull Request Health (`pull_requests`, weight: 20%):** Open PRs, stale review backlog (`HEALTH_STALE_PR_DAYS`), merge rate.
- **Contributor Health (`contributors`, weight: 15%):** Contributor concentration share, active authors breadth.
- **Release Health (`releases`, weight: 10%):** Recency of latest release tag, cadence. (If 0 releases exist, status is marked `INSUFFICIENT_DATA` and remaining dimensions dynamically reweight to sum to 1.0).
- **Maintenance Health (`maintenance`, weight: 15%):** Inactivity days combined with total stale issues and PRs.

#### Health Status Definitions:
- `HEALTHY` (Score ≥ 75.0)
- `ATTENTION` (50.0 ≤ Score < 75.0)
- `DEGRADED` (30.0 ≤ Score < 50.0)
- `CRITICAL` (Score < 30.0)
- `INSUFFICIENT_DATA` (dimension has no reliable data, never treated as 0)

---

### 2. Risk Detection Engine
Deterministic, rule-based evaluation of repository telemetry with idempotent deduplication via fingerprints (`hash(project_id, risk_type, entity_ref)`) and automatic resolution when underlying conditions clear.

#### 8 Core Deterministic Rules:
1. `REPOSITORY_INACTIVITY`: Triggers when days since last commit > `RISK_INACTIVITY_DAYS` (default: 14d). Severity: `MEDIUM` (14-30d), `HIGH` (30-60d), `CRITICAL` (>60d).
2. `STALE_ISSUES`: Triggers when open issues age ≥ `RISK_STALE_ISSUE_DAYS` (default: 30d). Evidence contains stale count, oldest age, and issue URLs.
3. `STALE_PULL_REQUESTS`: Triggers when unmerged PRs age ≥ `RISK_STALE_PR_DAYS` (default: 14d). Evidence contains PR numbers, review age, and GitHub links.
4. `ISSUE_BACKLOG_GROWTH`: Triggers when opened issues exceed closed issues by ≥ `RISK_ISSUE_BACKLOG_THRESHOLD` over `RISK_BACKLOG_WINDOW_DAYS`.
5. `PR_BACKLOG_GROWTH`: Triggers when opened PRs exceed merged PRs by ≥ `RISK_PR_BACKLOG_THRESHOLD` over `RISK_BACKLOG_WINDOW_DAYS`.
6. `LOW_CONTRIBUTOR_DIVERSITY`: Triggers when primary contributor accounts for ≥ `RISK_CONTRIBUTOR_CONCENTRATION_THRESHOLD` (default: 65%) of commits. Neutral project-level concentration signal.
7. `RELEASE_STAGNATION`: Triggers when days since latest release > `RISK_RELEASE_STAGNATION_DAYS` (default: 90d). Only triggers if releases exist; if 0 releases exist, marked as insufficient data.
8. `ACTIVITY_SPIKE`: Triggers when recent commit velocity is ≥ `RISK_ACTIVITY_SPIKE_MULTIPLIER` (default: 3.0x) higher than historical baseline.

#### Risk Lifecycle:
- `OPEN` → `ACKNOWLEDGED` (via `/projects/{id}/risks/{risk_id}/acknowledge`)
- `OPEN` or `ACKNOWLEDGED` → `RESOLVED` (via `/projects/{id}/risks/{risk_id}/resolve` or auto-resolved when condition clears)

---

### 3. Phase 4 Database Models
- `software_health_snapshots`: Stores overall score, status, calculated timestamp, twin version, and diagnostic explanation bullets.
- `health_dimension_results`: Stores individual dimension score, weight, status, metrics JSON, and explanation bullets.
- `software_risks`: Stores risk type, title, description, severity, status, unique fingerprint, detection rule, metric value, threshold value, structured evidence JSON, and affected entities.

---

### 4. Phase 4 API Endpoints
- `GET /api/v1/projects/{project_id}/health`: Latest Software Health snapshot with dimensions.
- `GET /api/v1/projects/{project_id}/health/history`: Historical snapshots for trend charting.
- `GET /api/v1/projects/{project_id}/health/dimensions`: Dimension results breakdown.
- `POST /api/v1/projects/{project_id}/health/recalculate`: Recalculates and persists a new snapshot.
- `GET /api/v1/projects/{project_id}/risks`: Filtered risks (`status`, `severity`, `risk_type`).
- `GET /api/v1/projects/{project_id}/risks/summary`: Aggregate counts by severity and status.
- `GET /api/v1/projects/{project_id}/risks/{risk_id}`: Granular risk detail and evidence.
- `POST /api/v1/projects/{project_id}/risks/{risk_id}/acknowledge`: Mark risk acknowledged.
- `POST /api/v1/projects/{project_id}/risks/{risk_id}/resolve`: Mark risk resolved.
- `POST /api/v1/projects/{project_id}/risks/recalculate`: Re-evaluates risk rules.

---

### 5. Running Tests
```bash
# Run all Phase 4 automated tests (22 test cases)
cd backend
python -m pytest tests/test_phase4_health_risks.py -v

# Run full backend regression suite
python -m pytest tests/ -v

# Verify frontend production build
cd ../frontend
npm run build
```
