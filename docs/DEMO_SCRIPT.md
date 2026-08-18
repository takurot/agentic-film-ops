# Agentic FilmOps — 4-Minute Live Demo Script

## Quick Reference: SPEC §2.2 Timing Beats

| Time  | Beat                          | SPEC §15 Criterion | Action / Narration Cue                                                          |
|------:|-------------------------------|---------------------|---------------------------------------------------------------------------------|
| 0:00  | Production Dashboard          | —                   | "Day 12 / 45. Three scenes today. Risk: MEDIUM."                                |
| 0:20  | Weather Alert                 | §15.1 MCP Access    | ⛈ Alert appears. "Scene 42 – 92% rain probability. AI detecting incident."       |
| 0:40  | Impact Analysis starts        | §15.1               | Click **Start AI Impact Analysis**. Orchestrator begins multi-agent dispatch.   |
| 1:00  | Multi-Agent parallel work     | §15.2 Multi-Agent   | Resource Network View lights up: Actor, Equipment, Location agents active.      |
| 1:30  | MCP Access visible            | §15.1               | MCP Activity Monitor shows `→ actor.check_availability()` etc.                  |
| 1:50  | Manager query sent            | §15.3 AI Structuring| External Communication: "Could Emma move Scene 42 to Wednesday 16:00–20:00?"   |
| 2:20  | Manager reply received        | §15.3               | "She can make it after 4 PM, must finish by 8 PM." → AI interprets as `16:00–20:00`. |
| 2:40  | Replanning                    | §15.4 Options       | "AI evaluating 3 alternative plans…"                                            |
| 3:10  | Option A / B / C presented    | §15.4               | Option Comparison grid. Point out cost/delay/risk. Recommend badge on Option A. |
| 3:30  | Producer Approval             | §15.5 Human-loop    | Click **Approve & Execute**. "One click. Human stays in control."               |
| 3:45  | MCP Execution                 | §15.1               | Execution Checklist: actor booking, equipment, studio, calendar, call sheet.    |
| 4:00  | Incident Resolved             | §15.6 Closed-loop   | Before/After Summary. Show detection→resolution time and AI telemetry.          |

---

## Step-by-Step Narration Notes

### 0:00 – Dashboard (30 sec)
- Open browser at `http://localhost:3000`
- Point out: Production Day counter, schedule %, budget, scenes, risk badge
- Say: *"This is the production command center — all status from a single API."*

### 0:20 – Weather Alert (20 sec)
- The `⛈ Weather Risk` card appears automatically
- Say: *"A typhoon warning just hit the weather MCP. Scene 42 outdoors — 92% rain probability. The AI has already detected the incident."*

### 0:40 – Impact Analysis (20 sec)
- Click **Start AI Impact Analysis**
- Say: *"One click triggers Gemini Orchestrator. It dispatches five domain agents in parallel."*

### 1:00 – Multi-Agent (30 sec)
- Resource Network View: animated edges lighting up
- Agent Live View: Actor, Equipment, Location nodes turn cyan/active
- Say: *"Five agents — Actor, Equipment, Location, Script, Budget — working simultaneously. This is genuine multi-agent coordination."*

### 1:30 – MCP Access (20 sec)
- MCP Activity Monitor scrolling: `→ actor.check_availability()`, `← Available: Emma Carter`
- Say: *"Every call goes through the Model Context Protocol. Standardized, auditable, tool-agnostic."*

### 1:50 – Manager Query (30 sec)
- External Communication panel shows the AI message to Emma's manager
- Say: *"The AI needs to check actor availability. It sends a natural-language query to the talent agency manager."*

### 2:20 – Reply Received (20 sec)
- Reply appears: *"She can make it after 4 PM, must finish by 8 PM."*
- AI Interpretation box: `AVAILABLE · Window: 16:00–20:00 · Constraint: Hard stop 20:00`
- Say: *"Unstructured free text — the AI converts it to a structured constraint. Zero human re-entry."*

### 2:40 – Replanning (30 sec)
- Analysis continues, Option Comparison grid loading
- Say: *"The constraint solver evaluates all feasible alternatives against budget, schedule, and risk."*

### 3:10 – Options A/B/C (20 sec)
- Three option cards visible with metrics
- Point out **RECOMMENDED** badge and explainability panel ("Why Option A?")
- Say: *"Three plans, with cost impact, schedule delay, and risk — plus a deterministic explanation."*

### 3:30 – Producer Approval (15 sec)
- Click **Approve & Execute** on Option A
- Say: *"The Producer makes the call. One decision, full context. Human-in-the-loop preserved."*

### 3:45 – MCP Execution (15 sec)
- Execution Checklist: items ticking green
- MCP Activity right panel: `actor.confirm_actor() → OK 200`
- Say: *"The approved plan executes through MCP. Actor booking, equipment, studio, calendar, call sheet — all automated."*

### 4:00 – Incident Resolved (15 sec)
- Before/After Summary: detection→resolution time, AI actions count, MCP calls count
- Say: *"Incident resolved. Closed loop — from weather alert to confirmed schedule change, fully autonomous except for one human approval."*

---

## Pre-Demo Checklist

Before presenting, verify:

- [ ] Backend running: `cd backend && uvicorn app.main:app --reload`
- [ ] Frontend running: `cd frontend && npm run dev`
- [ ] Demo state reset: click **↺ Reset Demo** in the header (or `POST /api/demo/reset`)
- [ ] Demo Timeline overlay visible (click **▶ Timeline** toggle)
- [ ] Browser at 1920×1080, zoom 100% (or 1280×800 minimum)
- [ ] Backend health check: `curl http://localhost:8000/api/production/health` returns 200
- [ ] No stale incidents: `curl http://localhost:8000/api/incidents/active` should show 0 or pre-seeded data

---

## Fallback Plan (Live Demo Failure)

See [DEMO_FALLBACK.md](./DEMO_FALLBACK.md) for full contingency procedures.

**30-second triage:**
1. **API error** → Check backend logs, restart with `cd backend && uvicorn app.main:app --reload`
2. **Frontend blank** → Hard refresh (`Cmd+Shift+R`), check `NEXT_PUBLIC_API_URL`
3. **Agent timeout** → Backend latency config: `LATENCY_FLOOR_MS` env var, default 500ms
4. **Total failure** → Switch to pre-recorded screen capture (see DEMO_FALLBACK.md §3)
