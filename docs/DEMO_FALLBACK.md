# Agentic FilmOps — Live Demo Fallback & Rehearsal Plan

This document covers contingency procedures when rehearsing or presenting the demo under network-constrained or live-failure conditions (per SPEC §11 and Issue #87).

---

## §1. Failure Triage & Recovery Matrix

| Symptom | Root Cause | Immediate Action |
|---|---|---|
| Frontend blank / 404 | Node server stopped | Run `npm run dev` in `frontend/` (port 3000) or check `takurot0708.web.app` |
| "Failed to load dashboard" error | Backend not running | Run `uvicorn app.main:app --reload` in `backend/` (port 8000) |
| Analysis error / backend timeout | `GEMINI_API_KEY` missing or invalid | Check `backend/.env` for valid `GEMINI_API_KEY` or switch to `RECORDED_REPLAY` mode |
| Weather Alert not appearing | Demo state already decided | Click **↺ Reset** in the header or call `POST /api/demo/reset` |
| Zero internet at venue | Venue offline | Run frontend in `RECORDED_REPLAY` mode (`npm run build:replay && npm run serve:export`) |
| Hardware / browser crash | Complete device failure | Play pre-rendered 1080p video at `remotion/out/promo-video.mp4` or load on smartphone |

---

## §2. Mode-Based Execution Profiles

### Profile A: Live Gemini Mode (Requires Internet & `GEMINI_API_KEY`)
1. **Backend (Terminal 1):**
   ```bash
   cd backend
   export GEMINI_API_KEY="your-gemini-api-key"
   /Users/takurot/Library/Python/3.14/bin/pybun run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
2. **Frontend (Terminal 2):**
   ```bash
   cd frontend
   NEXT_PUBLIC_FILMOPS_MODE=LIVE_GEMINI npm run dev
   ```
3. Open `http://localhost:3000` in browser.

---

### Profile B: Zero-Backend Recorded Replay Mode (100% Offline, Zero API Key)
The frontend contains a fully standalone, network-isolated replay profile that requires **zero backend servers, zero API keys, and zero internet connection**:
```bash
cd frontend
npm run build:replay
npm run serve:export
```
Open `http://localhost:4173` in any browser.

---

## §3. Fast Restart Sequences (< 30 Seconds)

### Reset Demo Database State
**Via Dashboard UI:** Click **↺ Reset** in the top navigation bar.  
**Via CLI:**
```bash
curl -X POST http://localhost:8000/api/demo/reset
```
This resets Scene 42 and incident `INC-20260902-001` back to their initial un-resolved state.

---

## §4. Video Fallback (< 10 Seconds)

If a live presentation environment encounters unforeseen projector, browser, or network failure:
1. Open the rendered 90-second promotional showcase:
   ```bash
   open remotion/out/promo-video.mp4
   ```
2. The video covers the complete 8-scene lifecycle:
   - **0:05**: Weather alert trigger on Scene 42 (Day 27).
   - **0:15**: 6-domain parallel agent swarm.
   - **0:30**: MCP stdio dependency graph propagation.
   - **0:45**: Talent manager NLP negotiation (Emma Carter).
   - **0:55**: Pareto-optimal recovery options (Option A saves $79,800).
   - **1:10**: Producer approval gate & autonomous dispatch.
   - **1:20**: Closed-loop resolution summary & judge verification links.

---

## §5. Pre-Demo Verification Checklist

- [ ] `GEMINI_API_KEY` configured in `backend/.env` (if presenting Live Mode).
- [ ] Backend tests passing: `pybun test` (331 tests green).
- [ ] Frontend tests passing: `npm test` (111 tests green).
- [ ] Replay build verified: `npm run test:e2e:replay` (0 horizontal overflow, 0 errors).
- [ ] Rendered video verified: `remotion/out/promo-video.mp4` playable.
- [ ] Public Web App bookmarked: `https://takurot0708.web.app` (Judge Mode ready).
