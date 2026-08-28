"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

/**
 * DemoTimeline – Floating demo navigator per SPEC §2.2 & Issue #85.
 *
 * Shows the 4-minute beat markers and auto-advances based on elapsed wall time.
 * Each beat maps to a SPEC §15 success criterion so judges can follow without narration.
 * Defaults to minimized dock mode on mobile/tablet viewports (< 768px) to prevent covering action CTAs.
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

function subscribeMediaQuery(callback: () => void) {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return () => {};
  }
  const mql = window.matchMedia("(max-width: 767px)");
  mql.addEventListener("change", callback);
  return () => mql.removeEventListener("change", callback);
}

function getMobileSnapshot() {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  return window.matchMedia("(max-width: 767px)").matches;
}

function getServerSnapshot() {
  return false;
}

export interface DemoTimelineProps {
  /** Override elapsed seconds (useful for testing). If undefined, uses real wall time. */
  elapsedSeconds?: number;
  /** Whether the timeline is visible */
  visible?: boolean;
  onClose?: () => void;
  /** Render the timeline as recorded sample data rather than an active live feed. */
  replay?: boolean;
}

export function DemoTimeline({
  elapsedSeconds,
  visible = true,
  onClose,
  replay = false,
}: DemoTimelineProps) {
  const [startTime] = useState(() => Date.now());
  const [wallElapsed, setWallElapsed] = useState(0);
  const isMobile = useSyncExternalStore(
    subscribeMediaQuery,
    getMobileSnapshot,
    getServerSnapshot
  );
  const [userMinimized, setUserMinimized] = useState<boolean | null>(null);
  const isMinimized = userMinimized ?? isMobile;

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
        className="fixed bottom-3 right-3 z-30 flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-950/95 px-3 py-1.5 shadow-2xl backdrop-blur-md transition-all hover:border-zinc-500 animate-fadeIn"
      >
        <span className="relative flex h-2 w-2">
          {!replay && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75 motion-reduce:animate-none" />}
          <span className={`relative inline-flex h-2 w-2 rounded-full ${replay ? "bg-amber-400" : "bg-red-500"}`} />
        </span>
        <span className="font-mono text-xs font-bold text-zinc-200">
          {formatTime(displayElapsed)}
        </span>
        <span className="hidden xs:inline rounded bg-zinc-800 px-2 py-0.5 font-mono text-[10px] text-zinc-300">
          {activeBeat.label}
        </span>
        <button
          type="button"
          aria-label="Expand demo timeline"
          onClick={() => setUserMinimized(false)}
          className="flex h-9 w-9 items-center justify-center rounded-full text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
          title="Expand timeline"
        >
          ▲
        </button>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close demo timeline"
            className="flex h-9 w-9 items-center justify-center rounded-full text-xs text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
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
      className="fixed bottom-3 left-1/2 z-30 -translate-x-1/2 w-[min(94vw,900px)] rounded-xl border border-zinc-700/80 bg-zinc-950/95 shadow-2xl backdrop-blur-md animate-slideInUp"
      role="region"
    >
      {/* Header row */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 px-3.5 py-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            {!replay && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75 motion-reduce:animate-none" />}
            <span className={`relative inline-flex h-2 w-2 rounded-full ${replay ? "bg-amber-400" : "bg-red-500"}`} />
          </span>
          <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-zinc-100">
            {replay ? "RECORDED REPLAY" : "LIVE DEMO"}
          </span>
        </div>
        <div className="flex items-center gap-2">
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
            onClick={() => setUserMinimized(true)}
            aria-label="Minimize demo timeline"
            className="flex h-8 w-8 items-center justify-center rounded text-xs text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
            title="Minimize to floating pill"
          >
            ▼
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close demo timeline"
              className="flex h-8 w-8 items-center justify-center rounded text-xs text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
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
      <div className="relative px-3.5 py-2.5">
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
                      ? `${beat.accent} ring-2 ring-offset-1 ring-offset-zinc-950 ring-current animate-pulse motion-reduce:animate-none`
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
                  className={`text-center text-[9px] font-semibold leading-tight truncate max-w-full ${
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
