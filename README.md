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

## 🎯 What Works in Phase 1

1. **Modular Architecture:** Clean separation of concerns across API routing, business services, database models, and schemas.
2. **PostgreSQL Database Connectivity:** Live database ping helper (`check_db_connection()`) measuring latency in milliseconds.
3. **Health Check API:** `/api/v1/health` returning system status, environment, uptime, and database telemetry.
4. **Professional SaaS Dashboard:**
   - Real-time connection badge for FastAPI and PostgreSQL.
   - 6 KPI Stat Cards (Health Score, High Risk Modules, Tracked Commits, Contributors, Open PRs, Open Issues).
   - Explainable Health Score Model with weighted contribution breakdown.
   - Activity velocity chart powered by Recharts.
   - Component Risk and Code Churn Table.
   - Live Digital Twin Event Feed.
5. **12 Navigation Modules:** Interactive sidebar mapped to the complete major project blueprint with informative phase preview views.
6. **Container Orchestration:** Complete `docker-compose.yml` configuration.

---

## 🔮 Next Step: Phase 2 Roadmap

In **Phase 2 (GitHub Project Onboarding & Data Collection)**:
- Enter and validate any GitHub repository URL.
- Collect commits, branches, issues, pull requests, and contributor activity via GitHub REST/GraphQL API.
- Normalize and persist raw git telemetry into PostgreSQL.
- Trigger automated initial Digital Twin synchronization.
