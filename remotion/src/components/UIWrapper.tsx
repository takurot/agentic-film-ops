import React from "react";

interface UIWrapperProps {
  title?: string;
  subtitle?: string;
  badge?: string;
  children: React.ReactNode;
}

export const UIWrapper: React.FC<UIWrapperProps> = ({
  title = "Agentic FilmOps — Autonomous Production Command Center",
  subtitle = "Project Titan (Feature Film) • Principal Photography Day 12 / 30",
  badge = "GEMINI + GEN AI SDK + MCP RUNTIME",
  children,
}) => {
  return (
    <div className="relative flex h-full w-full flex-col bg-zinc-950 text-zinc-100 antialiased overflow-hidden select-none">
      {/* Top Ambient Glow */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[1200px] h-[300px] bg-gradient-to-b from-emerald-500/10 via-cyan-500/5 to-transparent blur-3xl" />

      {/* Header Bar */}
      <header className="relative z-10 flex h-20 items-center justify-between border-b border-zinc-800/80 bg-zinc-900/60 px-10 backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-600 shadow-lg shadow-emerald-500/20">
            <span className="font-mono text-xl font-black text-black">🎬</span>
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-extrabold tracking-tight text-white uppercase">{title}</h1>
              <span className="rounded bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-400">
                {badge}
              </span>
            </div>
            <p className="text-xs text-zinc-400">{subtitle}</p>
          </div>
        </div>

        <div className="flex items-center gap-6 font-mono text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-zinc-200">LIVE FEED</span>
          </div>
          <div className="rounded border border-zinc-700 bg-zinc-800/80 px-3 py-1 text-zinc-300">
            TIME: 14:15:20 PST
          </div>
        </div>
      </header>

      {/* Main Screen Content */}
      <main className="relative z-10 flex-1 p-8 overflow-hidden">{children}</main>

      {/* Subtle Bottom Grid lines */}
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-1 border-t border-zinc-800/60" />
    </div>
  );
};
