"use client";

import { useEffect, useState } from "react";

/**
 * DemoTimeline – Floating demo navigator per SPEC §2.2.
 *
 * Shows the 4-minute beat markers and auto-advances based on elapsed wall time.
 * Each beat maps to a SPEC §15 success criterion so judges can follow without narration.
 * Supports minimize/dock mode to prevent viewport overlap on smaller displays.
 */

interface Beat {
  /** Seconds from demo start */
  timeSeconds: number;
  /** Short label shown in the timeline bar */
  label: string;
  /** SPEC §15 success criterion index (1-based, 0 = no criterion) */
  criterion: number;
  /** Accent colour class for the active beat */
  accent: string;
}

const BEATS: Beat[] = [
  { timeSeconds: 0,   label: "Dashboard",        criterion: 0, accent: "bg-zinc-400" },
  { timeSeconds: 20,  label: "Weather Alert",     criterion: 1, accent: "bg-red-400" },
  { timeSeconds: 40,  label: "Impact Analysis",   criterion: 3, accent: "bg-amber-400" },
  { timeSeconds: 60,  label: "Multi-Agent",       criterion: 2, accent: "bg-cyan-400" },
  { timeSeconds: 90,  label: "MCP Access",        criterion: 1, accent: "bg-blue-400" },
  { timeSeconds: 110, label: "Manager Query",     criterion: 3, accent: "bg-violet-400" },
  { timeSeconds: 140, label: "Reply Received",    criterion: 3, accent: "bg-violet-300" },
  { timeSeconds: 160, label: "Replanning",        criterion: 4, accent: "bg-amber-300" },
  { timeSeconds: 190, label: "Options A/B/C",     criterion: 4, accent: "bg-emerald-400" },
  { timeSeconds: 210, label: "Producer Approval", criterion: 5, accent: "bg-emerald-500" },
  { timeSeconds: 225, label: "MCP Execution",     criterion: 1, accent: "bg-blue-300" },
  { timeSeconds: 240, label: "Incident Resolved", criterion: 6, accent: "bg-emerald-300" },
];

const CRITERIA_LABELS: Record<number, string> = {
  1: "Gemini + MCP Access",
  2: "Multi-Agent Coordination",
  3: "AI Structuring External Comms",
  4: "Multi-Option with Rationale",
  5: "Human-in-the-loop",
  6: "Closed-Loop Incident Resolution",
};

export interface DemoTimelineProps {
  /** Override elapsed seconds (useful for testing). If undefined, uses real wall time. */
  elapsedSeconds?: number;
  /** Whether the timeline is visible */
  visible?: boolean;
  onClose?: () => void;
}

export function DemoTimeline({
  elapsedSeconds,
  visible = true,
  onClose,
}: DemoTimelineProps) {
  const [startTime] = useState(() => Date.now());
  // wallElapsed is only used when elapsedSeconds prop is not provided
  const [wallElapsed, setWallElapsed] = useState(0);
  const [isMinimized, setIsMinimized] = useState(false);

  // Wall-clock tracking — only runs when NOT controlled by elapsedSeconds prop
  useEffect(() => {
    if (elapsedSeconds !== undefined) return;
    const id = setInterval(() => {
      setWallElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [elapsedSeconds, startTime]);

  // Derive elapsed: prop takes priority over wall clock
  const elapsed = elapsedSeconds ?? wallElapsed;

  const totalSeconds = 240;
  const displayElapsed = Math.min(elapsed, totalSeconds);
  const progressPct = Math.min((elapsed / totalSeconds) * 100, 100);

  // Active beat: last beat whose timeSeconds <= elapsed
  const activeBeatIndex = BEATS.reduce(
    (acc, beat, i) => (elapsed >= beat.timeSeconds ? i : acc),
    0
  );
  const activeBeat = BEATS[activeBeatIndex];

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${String(sec).padStart(2, "0")}`;
  };

  if (!visible) return null;

  // Render minimized dock pill
  if (isMinimized) {
    return (
      <div
        id="demo-overlay"
        aria-label="Demo Timeline (Minimized)"
        className="fixed bottom-4 right-4 z-40 flex items-center gap-2.5 rounded-full border border-zinc-700 bg-zinc-950/95 px-4 py-2 shadow-2xl backdrop-blur-md transition-all hover:border-zinc-500 animate-fadeIn"
      >
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
        </span>
        <span className="font-mono text-xs font-bold text-zinc-200">
          {formatTime(displayElapsed)} / {formatTime(totalSeconds)}
        </span>
        <span className="rounded bg-zinc-800 px-2 py-0.5 font-mono text-[10px] text-zinc-300">
          {activeBeat.label}
        </span>
        <button
          type="button"
          aria-label="Expand demo timeline"
          onClick={() => setIsMinimized(false)}
          className="rounded p-1 text-xs text-zinc-400 hover:text-zinc-100 transition-colors"
          title="Expand timeline"
        >
          ▲
        </button>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close demo timeline"
            className="rounded p-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            ✕
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      id="demo-overlay"
      aria-label="Demo Timeline"
      className="fixed bottom-4 left-1/2 z-40 -translate-x-1/2 w-[min(92vw,900px)] rounded-xl border border-zinc-700/80 bg-zinc-950/95 shadow-2xl backdrop-blur-md animate-slideInUp"
      role="region"
    >
      {/* Header row */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-red-500" />
          </span>
          <span className="text-[11px] font-bold uppercase tracking-widest text-zinc-100">
            LIVE DEMO — AGENTIC FILMOPS
          </span>
        </div>
        <div className="flex items-center gap-2.5">
          {/* Current SPEC §15 criterion */}
          {activeBeat.criterion > 0 && (
            <span className="hidden sm:inline rounded bg-zinc-800 px-2 py-0.5 text-[10px] font-semibold text-zinc-300 font-mono">
              §15.{activeBeat.criterion} {CRITERIA_LABELS[activeBeat.criterion]}
            </span>
          )}
          <span className="font-mono text-xs text-zinc-400">
            {formatTime(displayElapsed)} / {formatTime(totalSeconds)}
          </span>
          <button
            type="button"
            onClick={() => setIsMinimized(true)}
            aria-label="Minimize demo timeline"
            className="rounded p-1 text-xs text-zinc-400 hover:text-zinc-100 transition-colors"
            title="Minimize to floating pill"
          >
            ▼
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close demo timeline"
              className="rounded p-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-0.5 w-full bg-zinc-800">
        <div
          className={`h-full transition-all duration-1000 ease-linear ${activeBeat.accent}`}
          style={{ width: `${progressPct}%` }}
          role="progressbar"
          aria-valuenow={elapsed}
          aria-valuemin={0}
          aria-valuemax={totalSeconds}
        />
      </div>

      {/* Beat markers */}
      <div className="relative px-4 py-3">
        <div className="flex items-start justify-between gap-1 overflow-x-auto">
          {BEATS.map((beat, i) => {
            const isActive = i === activeBeatIndex;
            const isPast = i < activeBeatIndex;

            return (
              <div
                key={beat.timeSeconds}
                className={`flex min-w-0 flex-1 flex-col items-center gap-1 transition-all duration-300 ${
                  isActive ? "scale-105" : isPast ? "opacity-60" : "opacity-35"
                }`}
              >
                {/* Dot */}
                <span
                  className={`h-2 w-2 rounded-full shrink-0 ${
                    isActive
                      ? `${beat.accent} ring-2 ring-offset-1 ring-offset-zinc-950 ring-current animate-pulse`
                      : isPast
                      ? "bg-zinc-500"
                      : "bg-zinc-700"
                  }`}
                />
                {/* Time */}
                <span className="font-mono text-[9px] text-zinc-500 shrink-0">
                  {formatTime(beat.timeSeconds)}
                </span>
                {/* Label */}
                <span
                  className={`text-center text-[9px] font-semibold leading-tight ${
                    isActive ? "text-zinc-100" : "text-zinc-500"
                  }`}
                >
                  {beat.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
