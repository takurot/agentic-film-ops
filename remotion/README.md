# Agentic FilmOps — Remotion Promo Video

This package contains the **Remotion** video generation project for [Agentic FilmOps](../README.md), implementing the promo video specifications from `docs/SPEC.md` §10.

## Overview

The promo video is a 90-second (2700 frames at 30 fps, 1920x1080) video demonstrating autonomous production disruption recovery:

| Beat | Timestamp | Scene Component | Description |
|---|---|---|---|
| **Scene 1** | 0:00 - 0:05 (0-150f) | `Scene1_Logo` | Product Logo & Concept Copy |
| **Scene 2** | 0:05 - 0:15 (150-450f) | `Scene2_Dashboard` | Production Dashboard + Severe Weather Alert on Scene 42 |
| **Scene 3** | 0:15 - 0:30 (450-900f) | `Scene3_MultiAgent` | Multi-Agent Live View (Weather, Script, Location, Actor, Equipment, Budget) |
| **Scene 4** | 0:30 - 0:45 (900-1350f) | `Scene4_NetworkMcp` | Resource Network View (ReactFlow graph) + Live MCP Tool Stream |
| **Scene 5** | 0:45 - 0:55 (1350-1650f) | `Scene5_ManagerComms` | External Communication Mock (Talent Agency automated chat + Gemini extraction) |
| **Scene 6** | 0:55 - 1:10 (1650-2100f) | `Scene6_ReplanningOptions` | Replan Options (A/B/C) + Gemini Constraint Solver Explainability |
| **Scene 7** | 1:10 - 1:20 (2100-2400f) | `Scene7_ApprovalExecution` | Producer Human Approval Gate + Autonomous Execution Pipeline |
| **Scene 8** | 1:20 - 1:30 (2400-2700f) | `Scene8_ResolvedSummary` | Before/After Summary ($79,800 saved, 0 days drift) + Outro |

## Quick Start

### 1. Install Dependencies
```bash
cd remotion
npm install
```

### 2. Preview Compositions in Browser
```bash
npm run dev
```

### 3. Run Unit & Compliance Tests
```bash
npm test
```

### 4. Render Video Deliverables

- **Full Master Cut with Subtitles & Audio (Issue #28)**:
  ```bash
  npm run render
  # Outputs: remotion/out/promo-video.mp4
  ```

- **Silent Footage Render Pass (Issue #36)**:
  ```bash
  npm run render:silent
  # Outputs: remotion/out/promo-video-silent.mp4
  ```
