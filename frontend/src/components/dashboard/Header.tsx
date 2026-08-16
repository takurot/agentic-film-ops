"use client";

/**
 * Header – AGENTIC FILMOPS brand bar with production day indicator (SPEC §9.1).
 */
export function Header({
  dayCurrent,
  dayTotal,
}: {
  dayCurrent: number;
  dayTotal: number;
}) {
  return (
    <header className="flex items-center justify-between border-b border-white/10 bg-zinc-950 px-6 py-4">
      <div className="flex items-center gap-3">
        <span className="inline-block h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
        <h1 className="text-lg font-semibold tracking-widest text-white uppercase">
          Agentic FilmOps
        </h1>
      </div>
      <span className="rounded bg-zinc-800 px-3 py-1.5 font-mono text-xs tracking-wider text-zinc-300">
        Production Day {dayCurrent} / {dayTotal}
      </span>
    </header>
  );
}
