"use client";

/**
 * Header – AGENTIC FILMOPS brand bar with production day indicator and Judge Mode toggle (SPEC §9.1, Issue #85).
 */
export function Header({
  dayCurrent,
  dayTotal,
  onToggleTimeline,
  onReset,
  resetting = false,
  showTimeline = false,
  runtimeLabel,
  isJudgeMode = true,
  onToggleJudgeMode,
}: {
  dayCurrent: number;
  dayTotal: number;
  onToggleTimeline?: () => void;
  onReset?: () => void;
  resetting?: boolean;
  showTimeline?: boolean;
  runtimeLabel?: string;
  isJudgeMode?: boolean;
  onToggleJudgeMode?: () => void;
}) {
  return (
    <header className="w-full max-w-full overflow-x-hidden border-b border-white/10 bg-zinc-950 px-3.5 py-2.5 sm:px-6 sm:py-3">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2.5">
        {/* Brand & Live Pulse */}
        <div className="flex items-center gap-2.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
          <h1 className="text-base sm:text-lg font-semibold tracking-wider sm:tracking-widest text-white uppercase">
            Agentic FilmOps
          </h1>
        </div>

        {/* Action Controls & Metadata Badges */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-2.5">
          {runtimeLabel && (
            <span
              className="rounded border border-sky-500/40 bg-sky-950/40 px-2 sm:px-3 py-1 font-mono text-[9px] sm:text-[10px] font-bold tracking-wider text-sky-300"
              title={runtimeLabel}
            >
              <span className="inline sm:hidden">
                {runtimeLabel.includes("RECORDED") ? "REPLAY" : "LIVE"}
              </span>
              <span className="hidden sm:inline">{runtimeLabel}</span>
            </span>
          )}

          {/* Judge Mode Toggle */}
          {onToggleJudgeMode && (
            <button
              type="button"
              id="toggle-judge-mode-btn"
              onClick={onToggleJudgeMode}
              title={isJudgeMode ? "Collapse Judge Executive Summary" : "Expand Judge Executive Summary"}
              aria-pressed={isJudgeMode}
              className={`min-h-[36px] sm:min-h-[32px] rounded px-2.5 sm:px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none ${
                isJudgeMode
                  ? "border border-amber-500/60 bg-amber-950/60 text-amber-300 shadow-[0_0_8px_rgba(245,158,11,0.2)]"
                  : "border border-zinc-700 bg-zinc-800 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              ⚖ <span className="hidden xs:inline">Judge Mode</span>
              <span className="xs:hidden">Judge</span>
            </button>
          )}

          {/* Demo Timeline Toggle */}
          {onToggleTimeline && (
            <button
              type="button"
              id="toggle-demo-timeline-btn"
              onClick={onToggleTimeline}
              title={showTimeline ? "Hide demo timeline" : "Show demo timeline"}
              aria-pressed={showTimeline}
              className={`min-h-[36px] sm:min-h-[32px] rounded px-2.5 sm:px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none ${
                showTimeline
                  ? "border border-red-700/50 bg-red-900/60 text-red-300 hover:bg-red-900"
                  : "border border-zinc-700 bg-zinc-800 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {showTimeline ? "⏹ Timeline" : "▶ Timeline"}
            </button>
          )}

          {/* Reset Demo State Button */}
          {onReset && (
            <button
              type="button"
              id="demo-reset-btn"
              onClick={onReset}
              disabled={resetting}
              title="Reset demo to initial state"
              className="min-h-[36px] sm:min-h-[32px] rounded border border-zinc-700 bg-zinc-800 px-2.5 sm:px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-zinc-400 transition-colors hover:text-zinc-200 disabled:cursor-wait disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
            >
              {resetting ? (
                "Resetting…"
              ) : (
                <>
                  <span className="inline sm:hidden">↺ Reset</span>
                  <span className="hidden sm:inline">↺ Reset Demo</span>
                </>
              )}
            </button>

          )}

          {/* Production Day Indicator */}
          <span className="rounded bg-zinc-800/90 px-2.5 sm:px-3 py-1 font-mono text-[10px] sm:text-xs tracking-wider text-zinc-300">
            <span className="inline sm:hidden">Day {dayCurrent}/{dayTotal}</span>
            <span className="hidden sm:inline">Production Day {dayCurrent} / {dayTotal}</span>
          </span>
        </div>
      </div>
    </header>
  );
}
