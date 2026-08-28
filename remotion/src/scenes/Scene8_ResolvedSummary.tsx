import React from "react";
import { useCurrentFrame, spring, useVideoConfig } from "remotion";
import { UIWrapper } from "../components/UIWrapper";


export const Scene8_ResolvedSummary: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const isOutro = frame >= 180;
  const outroScale = spring({
    frame: frame - 180,
    fps,
    config: { damping: 12, mass: 0.8 },
  });

  return (
    <div className="relative h-full w-full bg-zinc-950 text-white overflow-hidden">
      {!isOutro ? (
        <UIWrapper
          title="Incident Resolved — Before / After Impact Summary"
          badge="PRODUCTION RESTORED TO NOMINAL"
        >
          <div className="mx-auto flex max-w-5xl flex-col gap-6">
            {/* Resolution Success Banner */}
            <div className="flex items-center justify-between rounded-xl border border-emerald-500/50 bg-emerald-950/30 p-5 backdrop-blur-md">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 text-black font-extrabold text-xl shadow-lg shadow-emerald-500/30">
                  ✓
                </div>
                <div>
                  <h3 className="text-base font-bold text-emerald-300 uppercase">
                    Incident INC-2026-0819-01 Successfully Resolved
                  </h3>
                  <p className="text-xs text-zinc-300">
                    Day 12 filming shifted smoothly to Stage 2 Soundstage. Principal wrap date preserved.
                  </p>
                </div>
              </div>
              <span className="font-mono text-xs font-bold text-emerald-400">
                RECOVERY EFFICIENCY: 95.0%
              </span>
            </div>

            {/* Before vs After Comparison Grid */}
            <div className="grid grid-cols-2 gap-6">
              {/* Without Agentic FilmOps */}
              <div className="rounded-xl border border-red-500/40 bg-zinc-900/70 p-6 backdrop-blur-md">
                <p className="font-mono text-xs font-bold text-red-400 uppercase tracking-wider">
                  TRADITIONAL MANUAL RESCHEDULING
                </p>
                <div className="mt-4 space-y-4 font-mono">
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                    <span className="text-xs text-zinc-400">Set Down Time:</span>
                    <span className="text-sm font-bold text-red-400">+4.5 Hours</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                    <span className="text-xs text-zinc-400">Cost Penalty (Idle Crew):</span>
                    <span className="text-sm font-bold text-red-400">+$84,000 USD</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                    <span className="text-xs text-zinc-400">Wrap Schedule Impact:</span>
                    <span className="text-sm font-bold text-red-400">+1 Day Delay</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-zinc-400">Decision Latency:</span>
                    <span className="text-sm font-bold text-red-400">3 - 4 Hours</span>
                  </div>
                </div>
              </div>

              {/* With Agentic FilmOps */}
              <div className="rounded-xl border border-emerald-500/60 bg-gradient-to-b from-emerald-950/40 via-zinc-900/80 to-emerald-950/30 p-6 shadow-2xl shadow-emerald-500/15 backdrop-blur-md">
                <p className="font-mono text-xs font-bold text-emerald-400 uppercase tracking-wider">
                  WITH AGENTIC FILMOPS (AI AUTONOMOUS)
                </p>
                <div className="mt-4 space-y-4 font-mono">
                  <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
                    <span className="text-xs text-zinc-300">Set Down Time:</span>
                    <span className="text-sm font-bold text-emerald-300">1.5 Hours (-3.0h saved)</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
                    <span className="text-xs text-zinc-300">Actual Cost Impact:</span>
                    <span className="text-sm font-bold text-emerald-300">$4,200 ($79,800 saved)</span>
                  </div>
                  <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
                    <span className="text-xs text-zinc-300">Wrap Schedule Impact:</span>
                    <span className="text-sm font-bold text-emerald-300">0 Days (On Track)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-zinc-300">Decision Latency:</span>
                    <span className="text-sm font-bold text-emerald-300">2 Minutes 14 Seconds</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom ROI Note */}
            <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 font-mono text-xs text-zinc-400">
              <span>95% Cost Avoidance • SAG-AFTRA Turnaround Compliant</span>
              <span className="text-emerald-400 font-bold">100% Deterministic & Verifiable</span>
            </div>
          </div>
        </UIWrapper>
      ) : (
        /* Final Outro Screen */
        <div
          style={{ transform: `scale(${outroScale})` }}
          className="relative flex h-full w-full flex-col items-center justify-center text-center p-8"
        >
          <div className="pointer-events-none absolute h-[600px] w-[800px] rounded-full bg-gradient-to-tr from-emerald-500/25 via-teal-500/20 to-cyan-500/15 blur-3xl" />

          <div className="relative z-10 flex flex-col items-center">
            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-cyan-500 p-0.5 shadow-2xl shadow-emerald-500/40">
              <div className="flex h-full w-full items-center justify-center rounded-2xl bg-zinc-950">
                <span className="text-4xl">🎬</span>
              </div>
            </div>

            <h1 className="bg-gradient-to-r from-emerald-300 via-teal-200 to-cyan-300 bg-clip-text text-5xl font-black tracking-tight text-transparent uppercase drop-shadow-xl">
              AGENTIC FILM OPS
            </h1>

            <p className="mt-4 text-xl font-medium text-zinc-200">
              Autonomous Disruption Recovery for Film & TV Production
            </p>

            <div className="mt-8 flex items-center gap-4 rounded-full border border-emerald-500/40 bg-zinc-900/90 px-8 py-3 shadow-2xl">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="font-mono text-xs font-bold text-emerald-300 tracking-widest uppercase">
                Gemini 2.5 Flash • Google Gen AI SDK • Model Context Protocol
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
