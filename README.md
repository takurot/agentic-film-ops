# Agentic FilmOps

<div align="center">

**Autonomous Film Production Operations & Disruption Recovery Powered by Gemini 2.5 + Model Context Protocol (MCP)**

[![Live Web App](https://img.shields.io/badge/Live%20Demo-takurot0708.web.app-00DC82?style=for-the-badge&logo=firebase&logoColor=white)](https://takurot0708.web.app)
[![YouTube Video](https://img.shields.io/badge/YouTube-Watch%20Demo%20(90s)-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://youtu.be/2UmZ72bTpjk)
[![GitHub Repo](https://img.shields.io/badge/GitHub-takurot%2Fagentic--film--ops-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/takurot/agentic-film-ops)
[![Test Suite](https://img.shields.io/badge/Tests-354%20Passing-emerald?style=for-the-badge)](https://github.com/takurot/agentic-film-ops/actions)

<br/>

[![Watch the 90s Promo Video](https://takurot0708.web.app/youtube_thumbnail.jpg)](https://youtu.be/2UmZ72bTpjk)

*Click above to watch the full 90-second voiceover demo video on YouTube: [https://youtu.be/2UmZ72bTpjk](https://youtu.be/2UmZ72bTpjk)*

</div>

---

## 🌟 Executive Summary for Judges

When reality disrupts a $20M+ film production—such as a sudden 92% thunderstorm forecast on an outdoor rooftop shoot—producers face hours of chaotic calls, union overtime disputes, and **tens of thousands in idle crew standby penalties ($79,800+)**.

**Agentic FilmOps** turns every production resource (actors, equipment, stages, weather, budgets) into an AI-accessible **Production Resource Network** connected through the **Model Context Protocol (MCP)**. Powered by **Gemini 2.5 through the Google Gen AI SDK**, a team of 6 domain agents autonomously observes the disruption, reasons across cascading constraints, negotiates with external talent managers, generates Pareto-optimal replanning options with explainability, and executes the approved plan—**resolving the entire crisis in under 4 minutes with 1 human approval.**

```text
Observe (Doppler Radar) 
  → Reason (Cascading Graph) 
    → Coordinate (Talent / MCP) 
      → Re-plan (Pareto Solver) 
        → Human Approve (Producer Gate) 
          → Execute (Closed-Loop)
```

---

## ⚡ Quick Links & Live Demos

| Resource | Link | Description |
|---|---|---|
| 🌐 **Live Interactive App** | [https://takurot0708.web.app](https://takurot0708.web.app) | Full interactive Next.js 16 dashboard with live AI simulation mode |
| 🎥 **YouTube Demo Video** | [https://youtu.be/2UmZ72bTpjk](https://youtu.be/2UmZ72bTpjk) | 90-second cinematic showcase with voice narration & subtitles |
| 🎬 **Promo Video Direct Stream** | [https://takurot0708.web.app/promo-video.mp4](https://takurot0708.web.app/promo-video.mp4) | High-definition 1080p MP4 generated programmatically via Remotion |
| 📖 **Complete Specification** | [`docs/SPEC.md`](docs/SPEC.md) | Comprehensive engineering specification & domain data models |
| 🔄 **Implementation Workflow** | [`docs/WORKFLOW.md`](docs/WORKFLOW.md) | Standardized git/PR issue lifecycle and acceptance gates |

---

## 🏆 Key Breakthroughs (Why This Wins)

### 1. Everything is Connected via MCP (No Shortcuts)
The UI **never** bypasses the Orchestrator or calls agents directly. Every single interaction flows through standardized Model Context Protocol (MCP) tool buses (`weather_mcp`, `script_mcp`, `actor_mcp`, `location_mcp`, `equipment_mcp`, `budget_mcp`).

### 2. Real-Time Resource Graph Propagation (Flagship Visual)
The **Production Resource Network** dynamically traverses cascading dependencies (Scene 42 → Lead Actors Emma & Daniel → Shibuya Rooftop → ARRI Alexa 35 Camera Package → Rental Company → Weather Radar). Live pulse animations visualize the real-time AI impact propagation.

### 3. AI-to-Human External Comms Structuring
Unstructured natural-language negotiations with external talent agents (e.g. *"She can make it after 4 PM, but must wrap by 8 PM"*) are ingested and structured into strict JSON constraints with zero human data re-entry.

### 4. Deterministic Multi-Objective Constraint Solver
Rather than relying on hallucinated LLM schedules, the Schedule Agent runs a deterministic multi-objective solver to evaluate Pareto efficiency across Cast Union Rules, Golden Hour Lighting, Stage Availability, and Budget Variances.

### 5. Strict Human-in-the-Loop Approval Gate
The AI generates 3 explainable options (Option A: Studio B Swap [Recommended], Option B: 1-Day Delay, Option C: Night Shoot) with a *"Why?"* rationale breakdown. **The system will never commit financial or logistical changes without explicit Producer authorization.**

---

## ⏱️ 4-Minute Demo Scenario Timeline

| Beat | Timestamp | System Action & Judge Focus |
|:---:|:---:|---|
| **1** | `0:00` | **Production Dashboard**: 54-day shoot overview, 94% schedule adherence, $12.4M spent. |
| **2** | `0:20` | **Weather Risk Alert**: Doppler radar detects 92% rain on Scene 42 rooftop shoot. |
| **3** | `0:40` | **Impact Analysis**: Producer triggers AI Impact Analysis. |
| **4** | `1:00` | **Multi-Agent Coordination**: 6 domain agents activate in parallel, with Gemini reasoning via the Google Gen AI SDK. |
| **5** | `1:30` | **Live MCP Tool Bus**: Real-time stdio stream captures tool queries and responses. |
| **6** | `1:50` | **External Agency Comms**: Actor Agent negotiates with talent agency manager. |
| **7** | `2:20` | **Structured Comms Ingestion**: Unstructured chat parsed into time-window constraints. |
| **8** | `2:40` | **Constraint Solving**: Pareto solver explores alternatives across cast, stages, and trucks. |
| **9** | `3:10` | **Replan Options A/B/C**: 3 viable plans presented with cost, delay, and risk trade-off meters. |
| **10** | `3:30` | **Producer Approval Gate**: Producer reviews Explainability rationale and clicks **Approve & Execute**. |
| **11** | `3:45` | **Autonomous Execution**: 7 automated tasks fire across MCP tools (call sheets, soundstages, equipment). |
| **12** | `4:00` | **Closed-Loop Resolution**: Before/After summary displays $79,800 saved, 0 days delay, incident closed. |

---

## 🏛️ System Architecture

```text
                    ┌────────────────────────────────────────┐
                    │      Producer Web Dashboard (Next.js)  │
                    │  Health • Graph • Options • Execution  │
                    └───────────────────┬────────────────────┘
                                        │
                                 WebSocket / SSE / API
                                        │
                    ┌───────────────────▼────────────────────┐
                    │        PRODUCTION ORCHESTRATOR         │
                    │      Gemini 2.5 + Google Gen AI SDK   │
                    └───────────────────┬────────────────────┘
                                        │
                                  MCP Layer (Bus)
                                        │
    ┌──────────┬────────────┬───────────┴┬───────────┬───────────┐
    ▼          ▼            ▼            ▼           ▼           ▼
ACTOR MCP  EQUIPMENT    LOCATION      SCRIPT      WEATHER     BUDGET
  SERVER   MCP SERVER  MCP SERVER   MCP SERVER  MCP SERVER  MCP SERVER
    │          │            │            │           │           │
    ▼          ▼            ▼            ▼           ▼           ▼
Actor      Equipment    Location      Script      Weather     Budget
Agent      Agent        Agent         Agent       Agent       Agent
    │          │            │                                    │
    ▼          ▼            ▼                                    ▼
Talent     Cinema       Facility                             Production
Agency     Rental       Manager                               Cost DB
    └──────────┴────────────┼────────────────────────────────────┘
                            │
               ┌────────────▼────────────┐
               │   Production Resource   │
               │     Dependency Graph    │
               └────────────┬────────────┘
                            │
               ┌────────────▼────────────┐
               │     Schedule Agent      │
               │ (Pareto Constraint      │
               │       Solver)           │
               └─────────────────────────┘
```

---

## 💻 Tech Stack & Engineering Rigor

```text
Frontend
 ├─ Next.js 16 (App Router) & React 19
 ├─ Tailwind CSS v4 & Lucide Icons
 ├─ React Flow (Interactive Resource Network Graph)
 └─ Server-Sent Events (SSE) & WebSocket real-time stream

Backend & AI Core
 ├─ Python 3.11 / FastAPI
 ├─ Gemini 2.5 Flash via Google Gen AI SDK
 ├─ Model Context Protocol (MCP) Python SDK
 └─ SQLite + SQLAlchemy (Production Resource Graph)

Video Generation & Automation
 ├─ Remotion v4 (Programmatic React-to-Video engine)
 ├─ Auto-Ducking Audio Synthesis & Dynamic Narration
 └─ Automated Playwright E2E Browser Testing Suite
```

---

## 🧪 Comprehensive Test Coverage (100% Green)

Every layer is rigorously verified by automated unit, integration, and end-to-end tests:

```text
========================================================================
✔ Frontend Vitest Suite:     72 passed (15 test files)
✔ Backend Pytest Suite:     282 passed (full coverage across MCP/Agents)
✔ Remotion Vitest Suite:      9 passed (SPEC §10 timeline beats)
✔ Live Browser E2E Suite:    15 passed (Playwright live site verification)
========================================================================
TOTAL:                      378 automated tests passing
```

---

## 🚀 Running Locally

### 1. Prerequisites
- Node.js v20+ / npm
- Python 3.11+

### 2. Frontend Setup (Dashboard)
```bash
cd frontend
npm install
npm run dev
# Dashboard opens at http://localhost:3000
```

### 3. Backend Setup (FastAPI & MCP Servers)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m app.seed                      # Populate Scene 42 scenario
export FILMOPS_RUNTIME_MODE=LIVE_GEMINI
export GEMINI_API_KEY="your-key"
uvicorn app.main:app --reload --port 8000
```

`LIVE_GEMINI` uses Gemini through the Google Gen AI SDK and maintains six
validated MCP stdio sessions. Missing credentials, provider errors, malformed
model output, and MCP failures remain visible as `FAILED`; the backend never
silently changes modes. For deterministic judging or local rehearsal, select
`FILMOPS_RUNTIME_MODE=RECORDED_REPLAY` explicitly. The dashboard displays the
active runtime profile reported by `GET /api/runtime`.

### 4. Promo Video (Remotion Preview & Render)
```bash
cd remotion
npm install
npm run dev                             # Open Remotion Studio preview at http://localhost:3100
npm run render                          # Render 1080p MP4 to remotion/out/promo-video.mp4
```

---

## 📁 Repository Structure

```text
.
├── frontend/                # Next.js 16 + React 19 Dashboard & Component Library
│   ├── src/app/             # App Router pages & layouts
│   ├── src/components/      # Dashboard, React Flow Network, Approval, Video Modal
│   └── src/lib/             # API client, SSE stream, Mock fallback fixtures
├── backend/                 # FastAPI server & Gemini Multi-Agent Orchestrator
│   ├── app/agents/          # 6 Domain Agents (Weather, Script, Actor, Location, etc.)
│   ├── app/mcp_servers/     # 6 Standalone MCP Server implementations (stdio)
│   ├── app/models.py        # SQLAlchemy Production Resource Graph models
│   └── tests/               # 282 Pytest integration tests
├── remotion/                # Remotion v4 programmatic promo video project
│   ├── src/scenes/          # 8 Scene components matching SPEC §10.3 beats
│   └── scripts/             # Voiceover narration & BGM auto-ducking generators
├── docs/                    # Specification and architectural documentation
│   ├── SPEC.md              # Master engineering specification (Japanese)
│   ├── IDEA.md              # Original system architecture concept notes
│   └── WORKFLOW.md          # Standardized PR & issue lifecycle guide
└── README.md
```

---

## 🎬 Credits & Acknowledgments

- **Hackathon Entry**: Built for the Google Gemini AI Hackathon.
- **Architectural Reference**: Model Context Protocol (MCP) and the Google Gen AI SDK.
- **Video Production**: Rendered with [Remotion](https://www.remotion.dev/).

---

<div align="center">
<b>Agentic FilmOps — Autonomous Production Disruption Recovery for Film & TV</b><br/>
<i>When reality changes, AI coordinates the production in real time.</i>
</div>
