# Agentic FilmOps — Devpost "About the Project"

## Inspiration

Film and television productions are massive, high-stakes logistical machines. A standard mid-budget feature film costs anywhere from **$50,000 to over $250,000 per shoot day**. When reality disrupts the production schedule—such as a sudden 92% thunderstorm forecast on an outdoor rooftop scene, an actor getting stuck in transit, or specialized camera gear failing—the ripple effect is catastrophic. 

Producers and First Assistant Directors (1st ADs) are forced into frantic, chaotic scrambles: making dozens of emergency phone calls to talent agencies, rental houses, and soundstages, negotiating overtime penalty rates, and manually calculating union rest periods. In a typical Hollywood shoot, a single weather disruption can cost **$79,800+ in idle crew standby penalties** and push back the master wrap date.

We asked ourselves: *What if an entire film production ecosystem was interconnected through standard AI protocols? What if a coordinated team of AI agents could observe real-world disruptions, traverse the production dependency graph, negotiate with external stakeholders, and present optimal recovery plans in minutes rather than hours?*

This vision became **Agentic FilmOps**: an Autonomous Production Control Tower for film and television, built on **Gemini 2.5** and the **Model Context Protocol (MCP)**.

---

## What it does

**Agentic FilmOps** turns every human, piece of equipment, soundstage, script dependency, and budget constraint into an AI-accessible **Production Resource Network**. When an unforeseen disruption strikes, a network of 6 specialized domain agents autonomously executes a complete closed-loop resolution in **under 4 minutes**:

1. **Observe (Real-World Sensing)**: The **Weather Agent** monitors live forecasts and alerts the system when severe rain threatens an outdoor shoot (e.g. Scene 42 on the Shibuya Tower rooftop on Production Day 27).
2. **Reason (Dependency Traversal)**: The **Production Orchestrator** (powered by Gemini 2.5) evaluates the cascade of impacted resources—principal cast (Emma Carter & Daniel), camera packages (ARRI Alexa 35 & Lighting Kit), soundstages, and crew call times.
3. **Coordinate (External AI-to-Human Comms)**: The **Actor Agent** autonomously reaches out to talent agency managers. When a manager replies in unstructured natural language (*"Emma can make it after 4 PM, but has a hard stop at 8 PM"*), the agent ingests the text and structures it into deterministic time-window constraints with zero human data re-entry.
4. **Re-Plan (Multi-Objective Constraint Solving)**: Rather than hallucinating a schedule, the **Schedule Agent** runs a deterministic multi-objective constraint solver to generate 3 Pareto-optimal recovery plans:
   - **Option A (Recommended)**: Swap Scene 42 to Studio B soundstage (+$4,200 studio variance, 0 days delay, saves $79,800 in idle crew fees).
   - **Option B**: Stand down crew for 1 day (+$42,000 union standby cost, +1 day wrap drift).
   - **Option C**: Pivot to night shoot with rain wet-down look (+$18,500 cost, high safety risk).
5. **Human Approval Gate**: The Producer reviews the visual trade-off meters (Cost, Delay, Risk) and the AI's transparent *"Why?"* Explainability breakdown, authorizing the plan with a single click.
6. **Execute (Autonomous Dispatch)**: Upon approval, the system executes standardized MCP tool calls across domain servers to lock Studio B, reallocate camera gear, update digital call sheets, and sync master production slates.
7. **Judge Mode & Executive Telemetry**: A dedicated first-viewport executive summary displays key problem/solution/savings metrics and provides 1-click deep jumps to live evidence across desktop and mobile devices (390px responsive).

---

## How we built it

We designed Agentic FilmOps from the ground up with architectural rigor, modularity, and zero shortcuts:

- **AI Core & Multi-Agent Orchestration**: Built with **Google Gemini 2.5 Flash through the Google Gen AI SDK**. Six domain agents (**Weather, Script, Location, Actor, Equipment, Budget**) communicate with the central Production Orchestrator implemented in Python/FastAPI.
- **Standardized Tool Bus (Model Context Protocol - MCP)**: Every domain communicates strictly over MCP stdio transport layers (`weather_mcp`, `script_mcp`, `actor_mcp`, `location_mcp`, `equipment_mcp`, `budget_mcp`). The UI never directly calls agents—preserving complete protocol integrity.
- **Production Resource Dependency Graph**: Modeled in **SQLAlchemy & SQLite**, mapping scenes, cast members, rental equipment, stage facilities, and contract availability into an interconnected knowledge graph.
- **Frontend Command Center & Judge Mode**: Built with **Next.js 16 (App Router)**, **React 19**, **Tailwind CSS v4**, and **React Flow**. A local `LIVE_GEMINI` profile visualizes backend SSE activity; the public Firebase deployment is an explicitly labeled, network-isolated `RECORDED_REPLAY` using sample data.
- **Programmatic Video Production**: Authored our 90-second promotional showcase entirely in code using **Remotion v4**, React, Vitest, and an automated auto-ducking audio synthesis engine.
- **Automated Verification**: Engineered a full suite of **458 automated tests** (331 Pytest backend tests, 111 Vitest frontend tests, 9 Remotion tests, and 7 Playwright multi-viewport E2E tests).

---

## Challenges we ran into

1. **Simulating Realistic Human Turnaround Latencies**: In a live hackathon demo, instant 100ms API responses feel like mock static data rather than authentic agentic reasoning. We implemented a deliberate *Configurable Latency Simulation Layer* that models real-world async delays (e.g., manager communication takes 3–4 seconds of simulated waiting), complete with real-time SSE streaming.
2. **Bridging Unstructured Talent Negotiations with Strict Constraint Solvers**: Talent representatives communicate in nuanced natural language. We designed few-shot Gemini prompt pipelines with strict JSON schemas to reliably extract hard stop times, SAG-AFTRA turnaround rules, and meal penalty boundaries without hallucination.
3. **Multi-Variable Pareto Optimization in Film Production**: A movie schedule has conflicting trade-offs: minimizing actor overtime vs. avoiding golden-hour lighting loss vs. stage rental variances. Balancing deterministic constraint solving with Gemini's high-level strategic reasoning required careful architectural separation between reasoning agents and deterministic mathematical solvers.
4. **Truthful Cloud Replay for Zero-Backend Hosting**: The public Firebase app is built explicitly as `RECORDED_REPLAY`. It never attempts a backend, SSE, or WebSocket connection and labels both the first viewport and result summary as sample data. Live failures are never converted into simulated successes.

---

## Accomplishments that we're proud of

- **100% Protocol Compliance**: Built a true Model Context Protocol (MCP) architecture across 6 independent servers where every single tool call, argument, and error propagates through standard stdio JSON-RPC buses.
- **End-to-End Closed-Loop Resolution**: Proved that complex real-world physical operations (truck dispatching, talent re-routing, stage bookings, budget ledger syncing) can be completed in under 4 minutes with a single human producer approval.
- **The Flagship Resource Network View**: Built a dynamic, animated React Flow dependency graph that visually demonstrates how a single weather alert cascades through actors, gear, locations, and vendors.
- **Engineering Excellence & Test Coverage**: Achieved a 100% green test suite of **458 automated tests**, zero console errors, full WCAG 2.1 AA accessibility, and automated CI/CD quality gates.
- **Programmatic Promo Video in Remotion**: Built a synchronized 90-second promotional video purely in React code with voiceover narration, auto-ducked ambient synthesizer music, and bilingual subtitles.
- **Mobile-First Judge Mode**: Guaranteed 0 horizontal overflow across mobile (390x844), tablet, and desktop screens with an executive summary in the first viewport.

---

## What we learned

- **MCP is the Universal Language for Agentic Operations**: Standardizing tool calling through MCP transformed our architecture. Agents no longer need custom API wrappers; they simply query standardized capabilities across domains.
- **Humans Must Stay in the Approval Loop**: Autonomous execution without human oversight creates legal and financial anxiety in high-budget environments. By positioning AI as an *Options Generator & Execution Engine* with explicit human sign-off gates, trust and adoption skyrocket.
- **Explainability Trumps Raw Accuracy**: Presenting a recommended schedule isn't enough for a film producer. Explaining *why* Option A saves $79,800 compared to Option B while preserving SAG-AFTRA turnaround compliance is what turns AI recommendations into actionable decisions.

---

## What's next for Agentic FilmOps

- **Live Production Integrations**: Connect real-world production management tools (StudioBinder, Yamdu, Movie Magic Budgeting, and Scenechronize) via production-grade MCP servers.
- **Multi-Incident Cascading Solvers**: Expand the constraint solver to handle simultaneous multi-disruptions (e.g., lead actor illness + camera lens breakdown + rain on the same shoot day).
- **Voice-Activated Mobile App for On-Set 1st ADs**: Develop an on-set iOS/Android companion app enabling 1st Assistant Directors to converse with the Production Orchestrator via speech (*"Hey FilmOps, Daniel's flight is delayed 2 hours—recalculate today's call sheet"*).
- **Predictive Risk & Weather Forecasting**: Integrate long-range machine learning weather models and traffic telemetry to preemptively suggest schedule swaps days before filming commences.
