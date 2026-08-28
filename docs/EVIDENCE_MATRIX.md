# Agentic FilmOps — Evidence & Implementation Matrix

This matrix provides complete transparency into the implementation status, execution modes, and verifiable proof points for every feature and claim in the submission (per SPEC §11 and SPEC §15).

---

## 1. Core Feature & Claim Classification Matrix

| Feature / Claim | Status / Mode | Technical Implementation | Verifiable Evidence & Test Suite | Promo Video |
| :--- | :---: | :--- | :--- | :---: |
| **Multi-Agent Orchestration (6 Domain Agents)** | **REAL (Live Backend)** | `backend/app/orchestrator.py`, `backend/app/agents/*` (Weather, Script, Location, Actor, Equipment, Budget) powered by Gemini 2.5 Flash via Google Gen AI SDK. | [`test_orchestrator.py`](../backend/tests/test_orchestrator.py), [`test_actor_agent.py`](../backend/tests/test_actor_agent.py) | Scene 3 (0:15–0:30) |
| **Model Context Protocol (MCP stdio Transport)** | **REAL (Live Backend)** | 6 standalone MCP stdio servers (`weather_mcp`, `script_mcp`, `actor_mcp`, `location_mcp`, `equipment_mcp`, `budget_mcp`) communicating over JSON-RPC 2.0. | [`test_mcp_stdio_contract.py`](../backend/tests/test_mcp_stdio_contract.py), [`test_mcp_common_server.py`](../backend/tests/test_mcp_common_server.py) | Scene 4 (0:30–0:45) |
| **Asynchronous Job Execution & Real-Time SSE** | **REAL (Live Backend)** | `backend/app/analysis_runner.py` background runner + `GET /api/analyses/{id}/events` Server-Sent Events stream. | [`test_analysis_runner.py`](../backend/tests/test_analysis_runner.py), [`test_event_stream.py`](../backend/tests/test_event_stream.py) | Scene 3–4 (0:20–0:40) |
| **Durable Post-Approval State Machine & Retry** | **REAL (Live Backend)** | `NOT_STARTED` → `IN_PROGRESS` → `COMPLETED` / `FAILED` state machine with idempotency keys and step-skipping retries. | [`test_execution_resilience.py`](../backend/tests/test_execution_resilience.py) | Scene 7 (1:10–1:20) |
| **External Comms NLP & Time-Window Extraction** | **REAL (Live Backend)** | Gemini structured extraction parsing unstructured talent manager replies into deterministic SAG-AFTRA constraints. | [`test_actor_agent.py`](../backend/tests/test_actor_agent.py), [`ExternalCommunicationMock.tsx`](../frontend/src/components/live/ExternalCommunicationMock.tsx) | Scene 5 (0:45–0:55) |
| **Pareto Multi-Objective Replan Solver (A/B/C)** | **REAL (Live Backend)** | Mathematical constraint solver ranking Option A (Studio B swap), Option B (1-day delay), and Option C (night shoot). | [`test_schedule_agent.py`](../backend/tests/test_schedule_agent.py), [`OptionComparison.tsx`](../frontend/src/components/approval/OptionComparison.tsx) | Scene 6 (0:55–1:10) |
| **Human-in-the-Loop Producer Approval Gate** | **REAL (Live & Replay)** | Fail-closed governance: no autonomous external bookings occur without explicit Producer decision (`POST /api/analyses/{id}/decision`). | [`test_execution_resilience.py`](../backend/tests/test_execution_resilience.py), [`ApprovalPanel.test.tsx`](../frontend/src/components/approval/ApprovalPanel.test.tsx) | Scene 7 (1:10–1:20) |
| **Cost Avoidance Financial Model ($79,800 Saved)** | **REAL (Mathematical & Scenario Bound)** | Formula: $84,000 Standby Penalty (48 union crew headcount lost day) - $4,200 Option A Studio B fee = $79,800 net avoided costs (95.0% avoidance efficiency). | [`test_scenario_contract.py`](../backend/tests/test_scenario_contract.py), [`scenarioContract.test.ts`](../frontend/src/lib/scenarioContract.test.ts) | Scene 8 (1:20–1:30) |
| **Canonical Versioned Scenario (`SCENARIO-SC042-RAIN-V1`)** | **REAL (Multi-Surface Single Source)** | Single canonical JSON (`scenario/v1/demo_scenario.json`) shared across Backend API/seed, Frontend Replay fixtures, and Remotion video assets with SHA-256 validation. | [`sync_scenario.py`](../scripts/sync_scenario.py), [`test_scenario_contract.py`](../backend/tests/test_scenario_contract.py) | Scene 2, 8 |
| **Recorded Replay Public Experience** | **RECORDED REPLAY (Network Isolated)** | Zero-backend static Firebase export (`takurot0708.web.app`) running 100% locally in browser without pretending to be live API calls. | [`replay.spec.ts`](../frontend/e2e/replay.spec.ts), [`judge-mode-mobile.spec.ts`](../frontend/e2e/judge-mode-mobile.spec.ts) | Entire Video |
| **Judge Mode & Mobile Viewport Support (390x844)** | **REAL (Frontend)** | 4-point first-viewport executive summary, 1-click SPEC §15 deep jumps, auto-minimized timeline, 0 horizontal overflow. | [`JudgeExecutiveSummary.test.tsx`](../frontend/src/components/judge/JudgeExecutiveSummary.test.tsx), [`judge-mode-mobile.spec.ts`](../frontend/e2e/judge-mode-mobile.spec.ts) | Outro (1:25–1:30) |
| **Live Production Integrations (StudioBinder, Yamdu)** | **PLANNED (Post-Hackathon)** | Integration with commercial proprietary movie scheduling and budgeting APIs. | Roadmapped in SPEC §14. | Future |

---

## 2. Automated Test Suite Metrics (Verified Total: 458 Tests)

All test suites run locally and in GitHub Actions CI (`.github/workflows/ci.yml`):

- **Backend (Pytest & Python 3.13)**: 331 tests passing (Agent orchestration, MCP stdio protocol, resilience state machine, scenario contracts, API router).
- **Frontend (Vitest & React 19)**: 111 unit/integration tests passing (Judge Mode, Option Comparison, Approval Panel, Event Stream parsing, Before/After metrics).
- **Remotion (Vitest & Video Tests)**: 9 unit tests passing (2,700-frame subtitle continuity, 8-scene rendering).
- **Playwright E2E**: 7 multi-viewport tests passing (Recorded Replay isolation, Mobile 390x844, Tablet 768x1024, Desktop 1440x900, Live-Offline error handling).
- **Artifact Freshness**: `python scripts/sync_scenario.py --check` passing.
