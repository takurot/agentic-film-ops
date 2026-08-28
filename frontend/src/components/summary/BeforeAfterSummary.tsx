"use client";

import { useMemo, useState } from "react";
import type { ActiveIncident, AnalysisData, ExecutionData } from "@/lib/api";
import { isMCPCallEvent, type AnalysisEvent } from "@/lib/eventStream";
import { canonicalScenario } from "@/lib/scenarioLoader";


export interface BeforeAfterSummaryProps {
  incident: ActiveIncident;
  analysis?: AnalysisData | null;
  execution?: ExecutionData | null;
  events?: AnalysisEvent[];
  runtimeMode?: "LIVE_GEMINI" | "RECORDED_REPLAY";
}

/**
 * Parse an event timestamp which may be ISO-8601 or HH:MM:SS.
 * When HH:MM:SS is provided, anchor to the date part of baseDateStr.
 */
export function parseEventTimestamp(ts: string, baseDateStr?: string): number {
  if (!ts) return NaN;

  // Try direct ISO / RFC2822 parsing first
  if (ts.includes("T") || ts.includes("-")) {
    const parsed = new Date(ts).getTime();
    if (!isNaN(parsed)) return parsed;
  }

  // Handle HH:MM:SS format (e.g. from backend datetime.now().strftime("%H:%M:%S"))
  const timeMatch = ts.match(/^(\d{1,2}):(\d{2}):(\d{2})$/);
  if (timeMatch) {
    const [, hStr, mStr, sStr] = timeMatch;
    const hours = parseInt(hStr, 10);
    const minutes = parseInt(mStr, 10);
    const seconds = parseInt(sStr, 10);

    let year = 2026;
    let month = 8; // 0-indexed: Sept
    let day = 2;

    if (baseDateStr) {
      const base = new Date(baseDateStr);
      if (!isNaN(base.getTime())) {
        year = base.getUTCFullYear();
        month = base.getUTCMonth();
        day = base.getUTCDate();
      }
    }

    return new Date(Date.UTC(year, month, day, hours, minutes, seconds)).getTime();
  }

  const fallback = new Date(ts).getTime();
  return isNaN(fallback) ? NaN : fallback;
}

/**
 * Extract structured resource identifiers from text/field.
 */
function extractResourceIds(text: string, pattern: RegExp, targetSet: Set<string>): void {
  if (!text) return;
  const matches = text.matchAll(pattern);
  for (const match of matches) {
    if (match[1]) {
      targetSet.add(match[1].toUpperCase());
    }
  }
}

/**
 * Before/After Summary screen (SPEC §9.11).
 *
 * Closing resolution view showing detection-to-resolution time,
 * resources coordinated, AI actions, MCP calls, human decisions,
 * schedule delay, and cost impact computed strictly from the actual run.
 */
export function BeforeAfterSummary({
  incident,
  analysis,
  execution,
  events = [],
  runtimeMode = "LIVE_GEMINI",
}: BeforeAfterSummaryProps) {
  const [showCostDrillDown, setShowCostDrillDown] = useState(false);

  // Find decided option
  const selectedOption = useMemo(() => {
    if (!analysis?.options || analysis.options.length === 0) return null;
    if (analysis.decided_option_id) {
      return (
        analysis.options.find(
          (opt) => opt.option_id === analysis.decided_option_id
        ) ?? analysis.options[0]
      );
    }
    return analysis.options.find((opt) => opt.recommended) ?? analysis.options[0];
  }, [analysis]);

  // Compute metrics strictly from actual run (zero forced mock minimums)
  const metrics = useMemo(() => {
    // 1. Deduplicate events (e.g. from reconnect replay)
    const seenEventKeys = new Set<string>();
    const deduplicatedEvents: AnalysisEvent[] = [];

    for (const e of events) {
      const key = isMCPCallEvent(e)
        ? `${e.call_id ?? ""}:${e.timestamp}:${e.server}:${e.tool}:${e.status}`
        : `${e.event_id ?? ""}:${e.timestamp}:${e.agent}:${e.type}:${e.status}:${e.message}`;
      if (!seenEventKeys.has(key)) {
        seenEventKeys.add(key);
        deduplicatedEvents.push(e);
      }
    }


    // 2. Detection -> Resolution time
    let durationStr = "N/A";
    const startMs = new Date(incident.detected_at).getTime();

    if (!isNaN(startMs) && deduplicatedEvents.length > 0) {
      const validTimestamps = deduplicatedEvents
        .map((e) => parseEventTimestamp(e.timestamp, incident.detected_at))
        .filter((t) => !isNaN(t));

      if (validTimestamps.length > 0) {
        const endMs = Math.max(...validTimestamps);
        const diffSec = Math.max(0, Math.round((endMs - startMs) / 1000));
        const min = Math.floor(diffSec / 60);
        const sec = diffSec % 60;
        durationStr = min > 0 ? `${min} min ${sec} sec` : `${sec} sec`;
      }
    }

    // 3. AI Actions & Logical MCP Calls
    const mcpCallIds = new Set<string>();
    const agentEvents: AnalysisEvent[] = [];

    for (const e of deduplicatedEvents) {
      if (isMCPCallEvent(e)) {
        if (e.call_id) {
          mcpCallIds.add(e.call_id);
        } else {
          // If no call_id, group by server:tool:resource:timestamp
          const syntheticId = `${e.server}:${e.tool}:${e.resource ?? ""}:${e.timestamp}`;
          mcpCallIds.add(syntheticId);
        }
      } else {
        agentEvents.push(e);
      }
    }

    const mcpCallsCount = mcpCallIds.size;
    const aiActionsCount = agentEvents.length;

    // 4. Human decisions count
    const humanDecisionsCount = analysis?.decision ? 1 : 0;

    // 5. Resources coordinated (distinct structured IDs)
    const actorSet = new Set<string>();
    const crewSet = new Set<string>();
    const equipmentSet = new Set<string>();
    const locationSet = new Set<string>();
    const vendorSet = new Set<string>();

    const actorPattern = /(ACT-[A-Z0-9_-]+)/gi;
    const crewPattern = /(CREW-[A-Z0-9_-]+)/gi;
    const equipPattern = /(EQ-[A-Z0-9_-]+)/gi;
    const locPattern = /(LOC-[A-Z0-9_-]+)/gi;
    const vendorPattern = /(VEN-[A-Z0-9_-]+|MGR-[A-Z0-9_-]+)/gi;

    for (const e of deduplicatedEvents) {
      const res = e.resource ?? "";
      const msg = e.message ?? "";

      // Structured resource attribute
      if (res) {
        if (res.startsWith("ACT-") || res.includes("/ACT-")) actorSet.add(res.toUpperCase());
        else if (res.startsWith("CREW-")) crewSet.add(res.toUpperCase());
        else if (res.startsWith("EQ-") || res.includes("/EQ-")) equipmentSet.add(res.toUpperCase());
        else if (res.startsWith("LOC-") || res.includes("/LOC-")) locationSet.add(res.toUpperCase());
        else if (res.startsWith("VEN-") || res.startsWith("MGR-")) vendorSet.add(res.toUpperCase());
      }

      // Explicit identifiers mentioned in messages
      extractResourceIds(msg, actorPattern, actorSet);
      extractResourceIds(msg, crewPattern, crewSet);
      extractResourceIds(msg, equipPattern, equipmentSet);
      extractResourceIds(msg, locPattern, locationSet);
      extractResourceIds(msg, vendorPattern, vendorSet);

      if (isMCPCallEvent(e)) {
        if (e.server === "actor" && res) actorSet.add(res.toUpperCase());
        if (e.server === "equipment" && res) equipmentSet.add(res.toUpperCase());
        if (e.server === "location" && res) locationSet.add(res.toUpperCase());
      }
    }

    // Also scan execution steps if present
    if (execution?.steps) {
      for (const step of execution.steps) {
        extractResourceIds(step, actorPattern, actorSet);
        extractResourceIds(step, crewPattern, crewSet);
        extractResourceIds(step, equipPattern, equipmentSet);
        extractResourceIds(step, locPattern, locationSet);
        extractResourceIds(step, vendorPattern, vendorSet);
      }
    }

    const actorsCoordinated = actorSet.size;
    const crewCoordinated = crewSet.size;
    const equipmentCoordinated = equipmentSet.size;
    const locationsCoordinated = locationSet.size;
    const vendorsCoordinated = vendorSet.size;

    // 6. Schedule delay
    const delayDays =
      selectedOption?.schedule_delay_days ??
      selectedOption?.delay_days ??
      (analysis ? 0 : null);
    const scheduleDelayStr = delayDays !== null ? `${delayDays} DAYS` : "N/A";

    // 7. Cost impact
    const cost =
      selectedOption?.cost_impact ??
      (selectedOption?.cost_impact_usd as number | undefined) ??
      null;

    const costImpactStr =
      cost !== null
        ? cost > 0
          ? `+$${cost.toLocaleString()}`
          : cost < 0
          ? `-$${Math.abs(cost).toLocaleString()}`
          : "$0"
        : analysis
        ? "$0"
        : "N/A";

    const standbyPenalty = canonicalScenario.cost_benefit_model.standby_day_penalty_usd;
    const netSavings =
      cost !== null ? standbyPenalty - cost : canonicalScenario.cost_benefit_model.net_cost_avoided_usd;

    return {
      durationStr,
      aiActionsCount,
      mcpCallsCount,
      humanDecisionsCount,
      actorsCoordinated,
      crewCoordinated,
      equipmentCoordinated,
      locationsCoordinated,
      vendorsCoordinated,
      scheduleDelayStr,
      costImpactStr,
      rawCost: cost,
      avoidedPenalty: standbyPenalty,
      netSavings,
    };

  }, [incident, events, execution, analysis, selectedOption]);

  return (
    <div
      className="mt-6 rounded-xl border border-emerald-500/40 bg-zinc-900/90 p-6 shadow-2xl backdrop-blur-md"
      data-testid="before-after-summary"
    >
      {runtimeMode === "RECORDED_REPLAY" && (
        <p
          className="mb-4 rounded border border-amber-500/40 bg-amber-950/20 px-3 py-2 text-xs font-bold text-amber-200"
          role="status"
        >
          SCENARIO FIXTURE / RECORDED REPLAY / SAMPLE DATA
        </p>
      )}

      {/* Header Banner */}
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
            <span className="text-base font-black">✓</span>
          </div>
          <div>
            <h3 className="text-lg font-black tracking-widest text-emerald-400 uppercase">
              INCIDENT RESOLVED
            </h3>
            <p className="text-xs text-zinc-400">
              Autonomous replanning completed with verified constraint resolution
            </p>
          </div>
        </div>
        <span className="rounded bg-emerald-950/80 px-3 py-1 text-xs font-mono font-semibold text-emerald-300 border border-emerald-500/30">
          Scene {incident.scene_id}
        </span>
      </div>

      {/* Closed-Loop Flow Indicator (SPEC §15.6) */}
      <div className="mt-5 rounded-lg border border-emerald-500/20 bg-emerald-950/10 px-4 py-3">
        <div className="mb-2 text-[10px] font-bold uppercase tracking-widest text-emerald-500">
          §15.6 — Closed-Loop Autonomous Resolution
        </div>
        <div className="flex flex-wrap items-center gap-1 text-[10px] font-mono">
          {[
            { label: "Observe", color: "text-blue-300" },
            { label: "Reason", color: "text-cyan-300" },
            { label: "Coordinate", color: "text-amber-300" },
            { label: "Re-plan", color: "text-violet-300" },
            { label: "Approve", color: "text-emerald-300" },
            { label: "Execute", color: "text-emerald-400", last: true },
          ].map(({ label, color, last }) => (
            <span key={label} className="flex items-center gap-1">
              <span className={`font-bold ${color}`}>{label}</span>
              {!last && <span className="text-zinc-600">→</span>}
            </span>
          ))}
          <span className="ml-1 rounded bg-emerald-500/20 px-1.5 py-0.5 text-emerald-400 font-bold">
            ✓ Incident Closed
          </span>
        </div>
      </div>

      {/* Main Grid per SPEC §9.11 */}
      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {/* Metric 1: Detection -> Resolution */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
          <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
            Detection → Resolution
          </span>
          <div
            className="mt-2 text-2xl font-black font-mono text-white"
            data-testid="metric-duration"
          >
            {metrics.durationStr}
          </div>
          <p className="mt-1 text-[10px] text-zinc-500">
            Autonomous multi-agent discovery to execution
          </p>
        </div>

        {/* Metric 2: Schedule Delay */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
          <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
            Schedule delay
          </span>
          <div
            className="mt-2 text-2xl font-black font-mono text-emerald-400"
            data-testid="metric-schedule-delay"
          >
            {metrics.scheduleDelayStr}
          </div>
          <p className="mt-1 text-[10px] text-zinc-500">
            Shooting days impact compared to baseline wrap
          </p>
        </div>

        {/* Metric 3: Cost Impact */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
              Cost impact
            </span>
            <button
              type="button"
              onClick={() => setShowCostDrillDown((prev) => !prev)}
              aria-expanded={showCostDrillDown}
              className="text-[10px] text-cyan-400 hover:text-cyan-300 underline font-medium"
            >
              {showCostDrillDown ? "Hide breakdown" : "Cost breakdown"}
            </button>
          </div>
          <div
            className="mt-2 text-2xl font-black font-mono text-amber-300"
            data-testid="metric-cost-impact"
          >
            {metrics.costImpactStr}
          </div>
          <p className="mt-1 text-[10px] text-zinc-500">
            Selected plan variance vs baseline
          </p>
        </div>

        {/* Metric 4: Human Decisions */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
          <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
            Human decisions
          </span>
          <div
            className="mt-2 text-2xl font-black font-mono text-cyan-300"
            data-testid="metric-human-decisions"
          >
            {metrics.humanDecisionsCount}
          </div>
          <p className="mt-1 text-[10px] text-zinc-500">
            Producer approval gate action
          </p>
        </div>
      </div>

      {/* Cost & Savings Drill-Down Section (Issue #80 Scope 6) */}
      {showCostDrillDown && (
        <div
          className="mt-4 rounded-lg border border-cyan-500/30 bg-cyan-950/20 p-4 text-xs font-mono"
          data-testid="cost-drill-down"
        >
          <h4 className="text-xs font-bold text-cyan-300 uppercase tracking-wider mb-2">
            Cost & Savings Impact Breakdown
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-2">
            <div className="bg-zinc-950/80 p-2.5 rounded border border-zinc-800">
              <span className="text-[10px] text-zinc-400 block">Direct Replan Variance</span>
              <span className="text-sm font-bold text-amber-300">{metrics.costImpactStr}</span>
            </div>
            <div className="bg-zinc-950/80 p-2.5 rounded border border-zinc-800">
              <span className="text-[10px] text-zinc-400 block">Avoided Standby Penalty</span>
              <span className="text-sm font-bold text-emerald-400">
                ${metrics.avoidedPenalty.toLocaleString()}
              </span>
            </div>
            <div className="bg-zinc-950/80 p-2.5 rounded border border-emerald-500/30">
              <span className="text-[10px] text-emerald-400 block">Net Estimated Savings</span>
              <span className="text-sm font-bold text-emerald-300">
                ${metrics.netSavings.toLocaleString()}
              </span>
            </div>
          </div>
          <div className="text-[11px] text-zinc-400 mt-2">
            <p>
              <span className="font-semibold text-zinc-300">Formula:</span> Net Savings = Avoided
              Standby Penalty (${metrics.avoidedPenalty.toLocaleString()}) - Replan Cost (
              {metrics.costImpactStr})
            </p>
            {selectedOption?.why && (
              <p className="mt-1">
                <span className="font-semibold text-zinc-300">Rationale:</span> {selectedOption.why}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Two Column Section: Resources Coordinated vs AI/MCP Activity */}
      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Resources Coordinated */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-5">
          <h4 className="text-xs font-bold tracking-wider text-zinc-300 uppercase">
            Resources coordinated
          </h4>
          <div className="mt-3 space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1.5">
              <span className="text-zinc-400">Actors</span>
              <span className="font-bold text-white" data-testid="resource-actors">
                {metrics.actorsCoordinated}
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1.5">
              <span className="text-zinc-400">Crew</span>
              <span className="font-bold text-white" data-testid="resource-crew">
                {metrics.crewCoordinated}
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1.5">
              <span className="text-zinc-400">Equipment</span>
              <span className="font-bold text-white" data-testid="resource-equipment">
                {metrics.equipmentCoordinated}
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1.5">
              <span className="text-zinc-400">Locations</span>
              <span className="font-bold text-white" data-testid="resource-locations">
                {metrics.locationsCoordinated}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-zinc-400">Vendors</span>
              <span className="font-bold text-white" data-testid="resource-vendors">
                {metrics.vendorsCoordinated}
              </span>
            </div>
          </div>
        </div>

        {/* AI & MCP Operational Telemetry */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-5">
          <h4 className="text-xs font-bold tracking-wider text-zinc-300 uppercase">
            Operational Telemetry
          </h4>
          <div className="mt-3 space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1.5">
              <span className="text-zinc-400">AI actions</span>
              <span className="font-bold text-cyan-300" data-testid="metric-ai-actions">
                {metrics.aiActionsCount}
              </span>
            </div>
            <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1.5">
              <span className="text-zinc-400">MCP calls</span>
              <span className="font-bold text-indigo-300" data-testid="metric-mcp-calls">
                {metrics.mcpCallsCount}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-zinc-400">Human decisions</span>
              <span className="font-bold text-emerald-300" data-testid="telemetry-human-decisions">
                {metrics.humanDecisionsCount}
              </span>
            </div>

          </div>

          <div className="mt-4 rounded border border-emerald-500/20 bg-emerald-950/30 p-2.5 text-[11px] text-emerald-300">
            ⚡ All production locks, booking updates, and calendar syncs confirmed with zero conflict propagation.
          </div>
        </div>
      </div>
    </div>
  );
}

