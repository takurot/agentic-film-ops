"use client";

/**
 * Header – AGENTIC FILMOPS brand bar with production day indicator (SPEC §9.1).
 * Includes optional demo controls for Issue #27 rehearsal: timeline toggle and reset.
 */
export function Header({
  dayCurrent,
  dayTotal,
  onToggleTimeline,
  onReset,
  resetting = false,
  showTimeline = false,
}: {
  dayCurrent: number;
  dayTotal: number;
  onToggleTimeline?: () => void;
  onReset?: () => void;
  resetting?: boolean;
  showTimeline?: boolean;
}) {
  return (
    <header className="flex items-center justify-between border-b border-white/10 bg-zinc-950 px-6 py-4">
      <div className="flex items-center gap-3">
        <span className="inline-block h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
        <h1 className="text-lg font-semibold tracking-widest text-white uppercase">
          Agentic FilmOps
        </h1>
      </div>

      <div className="flex items-center gap-3">
        {/* Demo control buttons */}
        {onToggleTimeline && (
          <button
            id="toggle-demo-timeline-btn"
            onClick={onToggleTimeline}
            title={showTimeline ? "Hide demo timeline" : "Show demo timeline"}
            className={`rounded px-3 py-1 text-[10px] font-bold uppercase tracking-wider transition-colors ${
              showTimeline
                ? "bg-red-900/60 text-red-300 border border-red-700/50 hover:bg-red-900"
                : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:text-zinc-200"
            }`}
          >
            {showTimeline ? "⏹ Timeline" : "▶ Timeline"}
          </button>
        )}

        {onReset && (
          <button
            id="demo-reset-btn"
            onClick={onReset}
            disabled={resetting}
            title="Reset demo to initial state"
            className="rounded border border-zinc-700 bg-zinc-800 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-zinc-400 transition-colors hover:text-zinc-200 disabled:cursor-wait disabled:opacity-50"
          >
            {resetting ? "Resetting…" : "↺ Reset Demo"}
          </button>
        )}

        <span className="rounded bg-zinc-800 px-3 py-1.5 font-mono text-xs tracking-wider text-zinc-300">
          Production Day {dayCurrent} / {dayTotal}
        </span>
      </div>
    </header>
  );
}

