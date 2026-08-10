# Agentic FilmOps

**A Production Control Tower for film production, built on the Model Context Protocol (MCP).**

> Every production resource becomes AI-accessible through MCP.
> When reality changes, agents coordinate the entire production in real time.

Agentic FilmOps turns the people, equipment, locations, budget, script, and external conditions (weather, etc.) involved in a film production into an AI-accessible **Production Resource Network**. When something changes mid-production — like a sudden weather risk — a set of coordinated AI agents investigate impact, contact stakeholders, and re-plan the schedule, closing the loop end to end:

```text
Observe → Reason → Coordinate → Re-plan → Human Approve → Execute
```

This is not just a scheduler. It's a demonstration of multi-agent coordination over a live resource graph, with humans kept firmly in the approval loop.

For the full specification, see [`docs/SPEC.md`](docs/SPEC.md). The original concept notes are in [`docs/IDEA.md`](docs/IDEA.md).

---

## Table of Contents

- [Demo Scenario](#demo-scenario)
- [Architecture](#architecture)
- [Production Resource Graph](#production-resource-graph)
- [MCP Servers](#mcp-servers)
- [Agents](#agents)
- [Latency Simulation](#latency-simulation)
- [Event Stream](#event-stream)
- [UI Overview](#ui-overview)
- [Promo Video (Remotion)](#promo-video-remotion)
- [Mock vs. Real Boundary](#mock-vs-real-boundary)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Local Development](#local-development)
- [Implementation Phases](#implementation-phases)
- [Non-Functional Requirements](#non-functional-requirements)
- [Success Criteria](#success-criteria)

---

## Demo Scenario

The night before shooting, a heavy-rain forecast (92% probability) hits an outdoor scene — **Scene 42**.

```text
Weather MCP
    ↓
Weather Agent
    ↓
Production Orchestrator (impact analysis)
    ↓
┌────────────┬────────────┬────────────┐
Actor Agent  Equipment    Location     Budget
             Agent        Agent        Agent
    ↓            ↓            ↓            ↓
Manager      Rental       Location     Cost DB
inquiry      Company      Manager
    ↓            ↓            ↓
response      response      response
    └────────────┬────────────┘
                 ↓
        Production Resource Graph
                 ↓
          Schedule Agent (re-plan)
                 ↓
          Option A / B / C
                 ↓
        Producer Dashboard
                 ↓
             APPROVE
                 ↓
         Production Update (execution)
```

The whole flow is designed as a **~4-minute live demo**:

| Time | Beat |
| ---: | --- |
| 0:00 | Production Dashboard |
| 0:20 | Weather Alert fires |
| 0:40 | Impact Analysis starts |
| 1:00 | Multi-agent coordination |
| 1:30 | MCP calls visible |
| 1:50 | Manager contacted |
| 2:20 | Response received |
| 2:40 | Replanning |
| 3:10 | Option A/B/C presented |
| 3:30 | Producer approval |
| 3:45 | MCP execution |
| 4:00 | Incident resolved |

---

## Architecture

```text
                    ┌───────────────────────┐
                    │  Producer Dashboard   │
                    │  React / Next.js      │
                    └───────────┬───────────┘
                                │
                         WebSocket / API
                                │
                    ┌───────────▼───────────┐
                    │ PRODUCTION            │
                    │ ORCHESTRATOR          │
                    │ Gemini + Google ADK   │
                    └───────────┬───────────┘
                                │
                           MCP Layer
                                │
        ┌──────────┬────────────┼────────────┬──────────┐
        ▼          ▼            ▼            ▼          ▼
   ACTOR MCP   EQUIPMENT    LOCATION      SCRIPT     WEATHER
                  MCP          MCP          MCP         MCP
        │          │            │            │          │
        ▼          ▼            ▼            ▼          ▼
 Actor Agent  Equipment     Location      Script     Weather
              Agent         Agent         Agent      Agent
        │          │            │
        ▼          ▼            ▼
   Manager     Rental       Location
    Mock       Company       Manager
               Mock           Mock
                                │
                    ┌───────────▼───────────┐
                    │ Production Resource  │
                    │ Graph                │
                    └───────────────────────┘
```

### Core constraint

**The UI never calls an Agent directly.** Every operation flows through:

```text
Dashboard → Orchestrator → MCP → Resource / Agent
```

This keeps the core concept unambiguous: every production resource is connected to AI through MCP. No shortcut path is allowed in either the UI or Orchestrator implementation.

### Agent vs. MCP

```text
Agent = Reasoning (thinking / decision-making)
MCP   = Access / Action (talking to the world)
```

---

## Production Resource Graph

The central data model. A `Scene` sits at the center, connected to `Actor`, `Equipment`, `Location`, and `Crew`.

### Scene

```json
{
  "scene_id": "SC-042",
  "name": "Rooftop confrontation",
  "type": "outdoor",
  "duration_hours": 4,
  "actors": ["ACT-001", "ACT-002"],
  "location": "LOC-003",
  "equipment": ["EQ-001", "EQ-004"],
  "crew": ["CREW-001"],
  "scheduled": "2026-09-02T14:00"
}
```

### Actor

```json
{
  "id": "ACT-001",
  "name": "Emma Carter",
  "manager": "MGR-001",
  "availability": [],
  "status": "confirmed"
}
```

### Equipment

```json
{
  "id": "EQ-001",
  "name": "ARRI Alexa 35",
  "vendor": "Cinema Rental Tokyo",
  "availability": [],
  "daily_cost": 1200
}
```

```text
                 SCENE 42
                    │
       ┌────────────┼─────────────┐
       ↓            ↓             ↓
     Emma         Daniel       Rooftop
       │            │             │
    Manager      Manager       Location
       │                          Owner
       ↓
    Agency

                 SCENE 42
                    │
             ┌──────┴──────┐
             ↓             ↓
         Alexa 35       Lighting Kit
             │
             ↓
       Rental Company
```

---

## MCP Servers

For the hackathon, these are **mock MCP servers**, but they're designed as interfaces a real service could drop into — the tool signatures and response shapes are fixed as if production-ready.

### Actor MCP
`get_actor()` · `get_actor_availability()` · `get_actor_constraints()` · `contact_manager()` · `get_contact_status()` · `get_manager_response()` · `hold_actor()` · `confirm_actor()`

### Equipment MCP
`get_equipment()` · `check_availability()` · `request_extension()` · `request_reservation()` · `get_vendor_response()` · `reserve_equipment()`

### Location MCP
`get_location()` · `check_availability()` · `contact_location_manager()` · `find_alternative_locations()` · `hold_location()` · `confirm_location()`

### Weather MCP
`get_forecast()` · `get_weather_risk()` · `subscribe_weather_alert()`

### Script MCP
`get_scene()` · `get_scene_requirements()` · `get_scene_dependencies()` · `get_continuity_constraints()`

### Budget MCP
`get_current_budget()` · `estimate_change_cost()` · `calculate_overtime()` · `calculate_vendor_cost()`

---

## Agents

Agents and MCP servers are kept strictly separate (see [Agent vs. MCP](#agent-vs-mcp)).

### Production Orchestrator

The system's command center, powered by Gemini.

```text
Event detection
  ↓
Determine affected resources
  ↓
Delegate investigation
  ↓
Collect responses
  ↓
Generate alternatives
  ↓
Evaluate alternatives
  ↓
Request human approval
  ↓
Execute approved plan
```

### Actor Agent

Handles talent-related coordination. Example request from the Orchestrator:

> Can Emma Carter move Scene 42 to Wednesday afternoon?

```text
1. Actor MCP → check calendar
2. Check contract constraints
3. Determine a manager inquiry is required
4. contact_manager()
5. WAITING_EXTERNAL_RESPONSE
6. Manager mock response
7. Parse response
8. AVAILABLE_AFTER_16:00
9. Return result to Orchestrator
```

### Equipment / Location / Budget / Schedule Agents

Each follows the same pattern within its own domain (equipment, location, budget, scheduling), coordinating and evaluating options through its MCP server.

---

## Latency Simulation

**A deliberate non-functional requirement.** If every response comes back in under 0.1s, it just looks like a stack of API calls — not an agentic process. Latency is inserted on purpose.

**Actor Agent example:**

```text
Checking calendar...        ↓ 1.2 sec
Checking contract...        ↓ 0.8 sec
Contacting manager...       ↓
WAITING FOR MANAGER         ↓ 4 sec
Manager replied
"Emma can make it after 4 PM."
                             ↓
Parsing response...          ↓
AVAILABLE
```

**Equipment Agent example:**

```text
Checking inventory
       ↓
Contacting rental company
       ↓
WAITING
       ↓
Vendor confirmed
```

Latency values are configurable per agent so they can be tuned live during a demo.

---

## Event Stream

The backend records every agent event and pushes it to the dashboard in real time over WebSocket/SSE — this is what makes the UI feel alive.

```json
{
  "timestamp": "14:07:13",
  "agent": "ActorAgent",
  "type": "EXTERNAL_REQUEST",
  "status": "WAITING",
  "message": "Contacting Emma Carter's manager",
  "resource": "ACT-001"
}
```

**Status values:** `QUEUED` · `THINKING` · `QUERYING_MCP` · `WAITING_EXTERNAL` · `RESPONSE_RECEIVED` · `ANALYZING` · `COMPLETED` · `FAILED`

Delivery latency is synchronized with the [per-agent latency](#latency-simulation) above.

---

## UI Overview

- **Main Dashboard** — production health (schedule / budget / scenes / risk), active incident card, "Start AI Impact Analysis" trigger, today's scene progress.
- **Agent Live View** — the Orchestrator fanning out to Actor / Equipment / Location / Budget agents, each with a live status indicator.
- **MCP Activity Monitor** — a live stream of `→`/`←` MCP calls, the single most important panel for making the "everything is connected via MCP" story land visually.
- **Resource Network View** — the flagship screen. Gemini at the center, MCP as the connective layer, resources radiating outward; access propagates as an animated pulse across the graph during the incident.
- **External Communication Mock** — chat-style transcript showing an unstructured manager reply being parsed into structured availability data.
- **Replanning** — a real (not faked) constraint solver evaluates schedule combinations against cast, crew, equipment, location, continuity, and budget.
- **Option Comparison** — Options A/B/C with cost impact, schedule delay, and risk, one marked "Recommended."
- **Explainability** — every recommendation ships with a "Why?" breakdown and a comparison against the alternatives.
- **Human Approval** — the AI never commits a change on its own; a Producer must Approve or Reject.
- **Execution** — approved changes are applied and shown as a checklist, mirrored by live MCP calls.
- **Before / After Summary** — closing screen: detection-to-resolution time, resources coordinated, AI actions, MCP calls, human decisions, schedule delay, and cost impact.

Full mockups and per-screen specs live in [`docs/SPEC.md` §9](docs/SPEC.md#9-ui仕様).

---

## Promo Video (Remotion)

In addition to the live demo, a short **Remotion**-built promo video is part of the hackathon submission — useful as pre-read material for judges and as a fallback if the live demo hits trouble.

- **Format:** built as React components and rendered to MP4 via `@remotion/cli`.
- **Visual source of truth:** reuses the actual UI components (Dashboard, Agent Live View, MCP Activity Monitor, Resource Network View, etc.) rather than a separate design, so the video matches the real product.
- **Length:** 60–90 seconds, a condensed version of the [4-minute demo timeline](#demo-scenario).
- **Sequencing:** built after UI implementation is far enough along (after Phase 3 of the [implementation phases](#implementation-phases)), as part of Phase 4 polish — it depends on the real UI components existing first.
- **Deliverables:** one MP4 (60–90s) plus the Remotion project (`remotion/`, scene-per-component).

See [`docs/SPEC.md` §10](docs/SPEC.md#10-プロモーション動画remotion) for the full scene-by-scene breakdown.

---

## Mock vs. Real Boundary

Not everything is mocked. The rule: **the world is mocked, but the AI system operating on that world is real.**

| Component | MVP approach |
| --- | --- |
| Gemini Orchestrator | **Real** |
| Agent reasoning | **Real** |
| MCP calls | **Real** |
| Resource data | Mock |
| Actor | Mock |
| Manager | Mock |
| Rental company | Mock |
| Location manager | Mock |
| Weather data | Mock / Real (switchable) |
| Scheduling (constraint solver) | **Real** |
| Dashboard | **Real** |
| Agent event stream | **Real** |

---

## Tech Stack

```text
Frontend
 └─ Next.js
     ├─ React
     ├─ Tailwind
     ├─ React Flow (Resource Network View)
     └─ SSE / WebSocket (event stream)

Backend
 └─ Python / FastAPI

AI
 ├─ Gemini
 └─ Google ADK (Agent Development Kit)

Agents
 ├─ Production Orchestrator
 ├─ Actor Agent
 ├─ Equipment Agent
 ├─ Location Agent
 ├─ Schedule Agent
 └─ Budget Agent

MCP
 ├─ Actor MCP
 ├─ Equipment MCP
 ├─ Location MCP
 ├─ Script MCP
 ├─ Weather MCP
 └─ Budget MCP

Data
 └─ SQLite（Production Resource Graph）

External API
 └─ Gemini API（API key auth, not via Vertex AI）
```

**Deployment target:** local-only (decided in Issue #35). This is a hackathon live-demo project, so it runs entirely on the presenter's machine — `frontend` and `backend` started locally, data persisted in SQLite, Gemini called directly via API key. No Cloud Run / Firestore / Vertex AI deployment. This minimizes network dependency and failure points during a judged demo.

---

## Repository Structure

```text
.
├─ frontend/          # Next.js (App Router) + Tailwind + React Flow dashboard
│  └─ src/
│     ├─ app/         # Routes/pages
│     └─ lib/         # Client-side helpers (e.g. event stream client)
├─ backend/           # FastAPI app
│  └─ app/
│     ├─ main.py      # App entrypoint + health check
│     ├─ mcp_servers/ # MCP server implementations (Phase 1.2)
│     └─ agents/      # Domain + Orchestrator agents (Phase 1.3/1.4)
├─ docs/
│  ├─ SPEC.md         # Full specification (primary source of truth)
│  ├─ IDEA.md         # Original concept notes
│  └─ WORKFLOW.md     # Issue implementation workflow
└─ README.md
```

## Local Development

**Frontend** (Next.js):

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm test         # vitest
npm run lint
```

**Backend** (FastAPI):

```bash
cd backend
uv venv && uv pip install -e ".[dev]"    # or: python -m venv .venv && pip install -e ".[dev]"
source .venv/bin/activate
uvicorn app.main:app --reload            # http://localhost:8000
pytest --cov=app                         # tests
ruff check . && ruff format --check .    # lint
```

`GET /api/production/health` returns `{"status": "ok"}` once the backend is running.

---

## Implementation Phases

No need to build every agent from day one — build in phases:

1. **Phase 1 (core):** Dashboard → Weather incident → Orchestrator → Actor/Equipment/Location MCP → Replanning → Approval, end to end.
2. **Phase 2 (conversation & visibility):** Mock manager conversation, Agent Activity view, MCP Activity Monitor.
3. **Phase 3 (network visualization):** Resource Graph visualization, option comparison UI, execution animation.
4. **Phase 4 (polish):** UI polish, fixed demo script and rehearsal, [promo video](#promo-video-remotion).

---

## Non-Functional Requirements

- **Perceived responsiveness:** deliberate per-agent latency ([Latency Simulation](#latency-simulation)) so the coordination feels agentic, not like a flat API call list.
- **Explainability:** every final recommendation carries a "Why?" rationale.
- **Human approval:** no change is ever committed without explicit Producer approval.
- **Architectural constraint:** the UI never bypasses the Orchestrator to call an Agent or MCP directly.
- **Observability:** every agent event is recorded and streamed to the dashboard in real time.
- **Replaceability:** mock MCP servers are designed as drop-in interfaces for real services.
- **Submission redundancy:** a Remotion promo video backs up the live demo in case of technical issues.

---

## Success Criteria

A judge should understand all of the following **without narration**:

1. Gemini sits at the center as Orchestrator, reaching people, equipment, and locations through MCP.
2. Multiple agents coordinate in parallel (multi-agent coordination).
3. Real-world change (weather) is detected, and unstructured communication with stakeholders is turned into structured production data by AI.
4. The AI evaluates multiple alternatives and presents them with rationale.
5. The final decision is made by a human (the Producer) — human-in-the-loop.
6. Incident detection through resolution forms one closed loop.

---

## Documentation

- [`docs/SPEC.md`](docs/SPEC.md) — full specification (Japanese)
- [`docs/IDEA.md`](docs/IDEA.md) — original concept notes (Japanese)
