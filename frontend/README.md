# Agentic FilmOps — Frontend Dashboard & Judge Command Center

The frontend dashboard serves as the real-time control tower for film and television disruption management. Built with **Next.js 16 (App Router)**, **React 19**, **Tailwind CSS v4**, and **React Flow**.

---

## 1. Runtime Modes

The dashboard operates under two explicit, fail-closed build profiles (per SPEC §11):

1. **`RECORDED_REPLAY` (Default Public Build):**
   - Pure client-side static export with bundled canonical scenario fixtures (`@/scenario/demo_scenario.json`).
   - Network isolated: executes **0 fetch calls to `/api/`**, opens **0 SSE streams**, and **0 WebSockets**.
   - Clear amber runtime banners and fixture labels.
2. **`LIVE_GEMINI` (Live Hackathon Evaluation Mode):**
   - Connects to the Python FastAPI backend via Server-Sent Events (`/api/analyses/{id}/events`).
   - Requires `NEXT_PUBLIC_API_URL` and validates runtime handshake (`GET /api/runtime`) before rendering.

---

## 2. Key Features

- **Judge Mode & Executive Summary (`JudgeExecutiveSummary.tsx`):**
  - Aggregates the 4-point value grid (Problem, Solution, $79,800 Cost Avoidance, Producer Governance) in the first viewport.
  - 1-Click SPEC §15 Live Evidence Jumps to each resolution phase with accessible keyboard focus and reduced-motion safety.
- **Resource Network View (`ResourceNetworkView.tsx`):**
  - Interactive 14-node React Flow dependency graph illustrating cascading disruption propagation across domain agents, talent, equipment, and soundstages.
  - Collapsible on demand for mobile viewports.
- **Pareto Replan Options & Explainability (`OptionComparison.tsx`):**
  - Dynamic comparison of Option A (Studio B swap), Option B (1-day crew delay), and Option C (night wet-down look).
- **Human-in-the-Loop Approval Gate (`ApprovalPanel.tsx`):**
  - Enforces explicit Producer sign-off before executing autonomous MCP side effects.
- **Before / After Resolution Summary (`BeforeAfterSummary.tsx`):**
  - Verifiable mathematical breakdown of avoided standby penalties ($84,000 baseline - $4,200 replan cost = $79,800 net saved).
- **Responsive & Mobile Viewport Optimized:**
  - 0 horizontal overflow across Mobile (390x844), Tablet (768x1024), and Desktop (1440x900).
  - Floating Demo Timeline auto-minimizes on small screens to prevent CTA obstruction.

---

## 3. Getting Started

### Install Dependencies
```bash
npm ci
```

### Run Local Development (Replay Mode)
```bash
npm run dev
```
Open `http://localhost:3000`.

### Run Local Development (Live Gemini Mode)
```bash
export NEXT_PUBLIC_FILMOPS_MODE=LIVE_GEMINI
export NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## 4. Quality Verification & Testing

```bash
# Linting (ESLint 9)
npm run lint

# TypeScript Typecheck
npx tsc --noEmit

# Vitest Unit & Component Tests (111 tests)
npm test

# Playwright Replay & Multi-Viewport E2E Tests (Mobile 390x844, Tablet, Desktop)
npm run test:e2e:replay

# Playwright Live-Offline Error Handling E2E Tests
npm run test:e2e:live
```
