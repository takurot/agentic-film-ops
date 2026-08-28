"use client";

import { useCallback } from "react";
import { canonicalScenario } from "@/lib/scenarioLoader";

interface JudgeExecutiveSummaryProps {
  onOpenVideoModal?: () => void;
  runtimeMode?: "LIVE_GEMINI" | "RECORDED_REPLAY";
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function JudgeExecutiveSummary({
  onOpenVideoModal,
  runtimeMode = "RECORDED_REPLAY",
  isCollapsed = false,
  onToggleCollapse,
}: JudgeExecutiveSummaryProps) {
  const model = canonicalScenario.cost_benefit_model;

  const scrollToSection = useCallback((sectionId: string) => {
    const el = document.getElementById(sectionId);
    if (!el) return;

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;


    el.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "start",
    });

    // Move focus to target section for keyboard accessibility
    el.setAttribute("tabIndex", "-1");
    el.focus({ preventScroll: true });
  }, []);

  return (
    <section
      id="judge-executive-summary"
      aria-label="Judge Executive Summary"
      className="w-full rounded-xl border border-amber-500/40 bg-gradient-to-b from-amber-950/30 via-zinc-900/90 to-zinc-950 p-3.5 sm:p-5 shadow-2xl backdrop-blur-md transition-all"
    >
      {/* Top Banner Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-500/20 pb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-amber-400 ring-2 ring-amber-500/30" />
          <h2 className="text-xs sm:text-sm font-bold tracking-wider text-amber-300 uppercase">
            Judge Executive Summary & Verification Guide
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <span className="rounded bg-zinc-800 px-2 py-0.5 font-mono text-[9px] sm:text-[10px] font-semibold text-zinc-300">
            SPEC §15 Evaluation Suite
          </span>
          {onToggleCollapse && (
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-expanded={!isCollapsed}
              className="rounded p-1 text-xs text-zinc-400 hover:text-zinc-200 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              title={isCollapsed ? "Expand Executive Summary" : "Collapse Executive Summary"}
            >
              {isCollapsed ? "▼ Expand" : "▲ Collapse"}
            </button>
          )}
        </div>
      </div>

      {!isCollapsed && (
        <div className="mt-3.5 space-y-4">
          {/* Executive 4-Point Value Grid */}
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4 font-mono text-xs">
            {/* 1. Problem */}
            <div className="rounded-lg border border-red-500/30 bg-red-950/20 p-3">
              <span className="text-[10px] font-bold text-red-400 uppercase tracking-wider block">
                🚨 Disruption (Day 27)
              </span>
              <p className="mt-1 text-zinc-200 font-semibold text-[11px] leading-tight">
                Scene 42 Outdoor Rain Alert
              </p>
              <p className="mt-0.5 text-[10px] text-zinc-400">
                Shibuya Rooftop shoot blocked (92% rain probability)
              </p>
            </div>

            {/* 2. Autonomous Solution */}
            <div className="rounded-lg border border-cyan-500/30 bg-cyan-950/20 p-3">
              <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider block">
                🎯 Autonomous Plan
              </span>
              <p className="mt-1 text-zinc-200 font-semibold text-[11px] leading-tight">
                Option A — Studio B Soundstage
              </p>
              <p className="mt-0.5 text-[10px] text-zinc-400">
                0-day schedule delay • 1.5h setup turnaround
              </p>
            </div>

            {/* 3. Financial Impact */}
            <div className="rounded-lg border border-emerald-500/40 bg-emerald-950/25 p-3 shadow-md shadow-emerald-500/10">
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block">
                💰 Cost Avoidance
              </span>
              <p className="mt-1 text-emerald-300 font-extrabold text-sm sm:text-base leading-tight">
                +${model.net_cost_avoided_usd.toLocaleString()} Net Saved
              </p>
              <p className="mt-0.5 text-[10px] text-zinc-400">
                ${model.standby_day_penalty_usd.toLocaleString()} Standby - ${model.option_a_variance_usd.toLocaleString()} Replan
              </p>
            </div>

            {/* 4. Human Governance */}
            <div className="rounded-lg border border-violet-500/30 bg-violet-950/20 p-3">
              <span className="text-[10px] font-bold text-violet-400 uppercase tracking-wider block">
                🛡️ Human Governance
              </span>
              <p className="mt-1 text-zinc-200 font-semibold text-[11px] leading-tight">
                Producer Approval Gate
              </p>
              <p className="mt-0.5 text-[10px] text-zinc-400">
                No autonomous side-effects before explicit signoff
              </p>
            </div>
          </div>

          {/* 1-Click Evidence Deep-Links (SPEC §15) */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/80 p-3">
            <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-300">
              ⚡ 1-Click SPEC §15 Live Evidence Jumps:
            </p>
            <nav aria-label="Evidence Navigation Links" className="mt-2.5 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => scrollToSection("incident-section")}
                className="min-h-[36px] rounded border border-red-500/40 bg-red-950/30 px-2.5 py-1.5 text-[11px] font-bold text-red-300 hover:bg-red-900/40 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                §15.3 Alert Trigger
              </button>
              <button
                type="button"
                onClick={() => scrollToSection("agent-orchestration-section")}
                className="min-h-[36px] rounded border border-cyan-500/40 bg-cyan-950/30 px-2.5 py-1.5 text-[11px] font-bold text-cyan-300 hover:bg-cyan-900/40 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                §15.2 6-Agent Swarm
              </button>
              <button
                type="button"
                onClick={() => scrollToSection("mcp-activity-section")}
                className="min-h-[36px] rounded border border-blue-500/40 bg-blue-950/30 px-2.5 py-1.5 text-[11px] font-bold text-blue-300 hover:bg-blue-900/40 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                §15.1 MCP Stdio Calls
              </button>
              <button
                type="button"
                onClick={() => scrollToSection("external-comms-section")}
                className="min-h-[36px] rounded border border-violet-500/40 bg-violet-950/30 px-2.5 py-1.5 text-[11px] font-bold text-violet-300 hover:bg-violet-900/40 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                §15.3 External NLP Comms
              </button>
              <button
                type="button"
                onClick={() => scrollToSection("replan-options-section")}
                className="min-h-[36px] rounded border border-amber-500/40 bg-amber-950/30 px-2.5 py-1.5 text-[11px] font-bold text-amber-300 hover:bg-amber-900/40 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                §15.4 Pareto Options
              </button>
              <button
                type="button"
                onClick={() => scrollToSection("approval-section")}
                className="min-h-[36px] rounded border border-emerald-500/40 bg-emerald-950/30 px-2.5 py-1.5 text-[11px] font-bold text-emerald-300 hover:bg-emerald-900/40 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                §15.5 Approval Gate
              </button>
              <button
                type="button"
                onClick={() => scrollToSection("summary-section")}
                className="min-h-[36px] rounded border border-emerald-500/60 bg-emerald-900/40 px-2.5 py-1.5 text-[11px] font-bold text-emerald-200 hover:bg-emerald-800/50 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                §15.6 Closed-Loop Summary
              </button>
            </nav>
          </div>

          {/* Video & Verification Links Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-zinc-400 uppercase font-mono">Current Engine:</span>
              <span className="font-mono text-[10px] font-bold text-amber-300 bg-zinc-800/80 px-2 py-0.5 rounded border border-zinc-700">
                {runtimeMode === "LIVE_GEMINI" ? "⚡ Live Gemini 2.5 + MCP stdio" : "🎬 Recorded Replay Fixture"}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {onOpenVideoModal && (
                <button
                  type="button"
                  onClick={onOpenVideoModal}
                  className="min-h-[32px] rounded-lg border border-amber-500/50 bg-amber-500/10 px-3 py-1 font-bold text-amber-300 hover:bg-amber-500/20 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
                >
                  🎬 Watch 90s Promo Video
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
