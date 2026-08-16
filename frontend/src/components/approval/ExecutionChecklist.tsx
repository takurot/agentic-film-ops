"use client";

import type { ExecutionData } from "@/lib/api";

interface ExecutionChecklistProps {
  execution: ExecutionData;
}

export function ExecutionChecklist({ execution }: ExecutionChecklistProps) {
  const isCompleted = execution.status === "COMPLETED";

  return (
    <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-emerald-500/20 pb-3">
        <div className="flex items-center gap-2">
          {isCompleted ? (
            <span className="flex h-3 w-3 items-center justify-center rounded-full bg-emerald-500 text-[9px] font-bold text-black">
              ✓
            </span>
          ) : (
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
            </span>
          )}
          <h3 className="text-sm font-bold tracking-wider text-emerald-300 uppercase">
            {isCompleted ? "Plan Execution Complete (SPEC §9.10)" : "Executing Plan…"}
          </h3>
        </div>
        <span
          className={`rounded px-2 py-0.5 text-[10px] font-bold tracking-wide ${
            isCompleted
              ? "border border-emerald-500/50 bg-emerald-900/60 text-emerald-300"
              : "border border-amber-500/50 bg-amber-900/60 text-amber-300 animate-pulse"
          }`}
        >
          {execution.status}
        </span>
      </div>

      {/* Checklist items */}
      <div className="mt-4 space-y-2">
        <span className="text-[11px] font-bold tracking-wider text-zinc-400 uppercase">
          MCP Actions Executed:
        </span>
        <ul className="space-y-1.5">
          {execution.steps.map((step, index) => (
            <li
              key={index}
              className="flex items-center gap-2.5 rounded bg-zinc-900/50 px-3 py-2 text-xs text-zinc-200 border border-zinc-800/80"
            >
              <span className="text-emerald-400 font-bold">✓</span>
              <span>{step}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
