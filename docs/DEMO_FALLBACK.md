# Agentic FilmOps — Live Demo Fallback Plan

This document covers contingency procedures when the live demo encounters failures.
Ties to Issue #27 (Finalize and rehearse the 4-minute demo script) and SPEC §10 (Promo Video).

---

## §1. Failure Triage Matrix

| Symptom | Likely Cause | Immediate Action |
|---|---|---|
| Frontend blank / 404 | Next.js build issue | Hard refresh → `npm run dev` → check `NEXT_PUBLIC_API_URL` |
| "Failed to load dashboard" error | Backend not running | `cd backend && uvicorn app.main:app --reload` |
| Analysis stuck at "Analyzing…" | Agent timeout / Gemini API rate limit | Check `backend/.env` for `GOOGLE_API_KEY`; restart backend |
| Weather Alert not appearing | Demo state not reset | Click **↺ Reset Demo** in header or `POST /api/demo/reset` |
| React Flow blank / no graph | Browser SSR issue | Refresh; React Flow requires client-side hydration |
| Option Comparison not showing | Analysis timeout | Wait 30s; if still blank, `POST /api/demo/reset` and retry |

---

## §2. Partial-Failure Recovery Procedures

### §2.1 Backend Restart (< 30 sec)
```bash
cd /path/to/agentic-film-ops/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### §2.2 Demo State Reset
**Via UI:** Click **↺ Reset Demo** in the header.  
**Via CLI:**
```bash
curl -X POST http://localhost:8000/api/demo/reset
```
This clears all incidents and analyses, resetting to a fresh pre-incident state.

### §2.3 Full Restart Sequence (< 60 sec)
```bash
# Terminal 1 — Backend
cd backend && uvicorn app.main:app --reload

# Terminal 2 — Frontend  
cd frontend && npm run dev

# Browser
open http://localhost:3000
# Click ↺ Reset Demo
# Click ▶ Timeline to start the overlay
```

---

## §3. Total Failure — Pre-recorded Video Fallback

If neither backend nor frontend can be recovered within 2 minutes:

1. Open the pre-recorded screen capture: **`docs/assets/demo-recording.mp4`**  
   *(Record this before the presentation; see §4 for recording instructions)*
2. Play at 1x speed with narration cues from [DEMO_SCRIPT.md](./DEMO_SCRIPT.md)
3. Alternatively, the Remotion promo video (Issue #28, Issue #36) serves as a
   condensed 60–90 sec fallback covering the 6 SPEC §15 success criteria visually

**Narration pivot for video fallback:**
> *"Let me show you a recorded walkthrough since we want to focus on the agent behavior
> rather than setup time. The same system is running here, and I'll narrate the key moments."*

---

## §4. Pre-Presentation Recording Instructions

Record at least one full run-through before the live presentation:

```bash
# macOS — QuickTime Player → File → New Screen Recording
# Set: 1920×1080, audio off, cursor highlight on
# Start recording, then run the demo scenario end-to-end
# Save as docs/assets/demo-recording.mp4
```

Alternatively use OBS:
- Scene: Display capture + window capture (browser)
- Output: MP4, 1920×1080, 30fps
- File: `docs/assets/demo-recording.mp4`

---

## §5. Network / API Key Contingency

If the venue has no internet (Gemini API requires connectivity):

- The backend has a mock analysis mode. All MCP servers are already mocks (SPEC §11).
- Set `GEMINI_MOCK=true` in `backend/.env` to use pre-scripted responses:
  ```env
  GEMINI_MOCK=true
  MOCK_ANALYSIS_DELAY_MS=3000
  ```
- This produces realistic event streams without any external API calls.
- Restart backend after changing `.env`.

---

## §6. Checklist — Day of Presentation

- [ ] Screen capture recorded and accessible at `docs/assets/demo-recording.mp4`
- [ ] Backup laptop with demo repo cloned and `npm run dev` + `uvicorn` verified
- [ ] `GOOGLE_API_KEY` loaded in both laptops' `backend/.env`
- [ ] `GEMINI_MOCK=true` mode tested and working as fallback
- [ ] Demo Timeline overlay tested at venue resolution
- [ ] Promo video (Issue #28) downloaded and accessible offline
