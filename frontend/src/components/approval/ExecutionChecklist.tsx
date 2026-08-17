"use client";

import { useMemo } from "react";
import type { ExecutionData } from "@/lib/api";

interface ExecutionChecklistProps {
  execution: ExecutionData;
}

interface ExecutionItem {
  id: string;
  label: string;
  mcpCall: string;
  details?: string;
}

const SPEC_EXECUTION_ITEMS: ExecutionItem[] = [
  {
    id: "actor-booking",
    label: "Actor booking updated",
    mcpCall: "actor.confirm_actor()",
    details: "Emma Carter & Daniel Craig confirmed for revised slot",
  },
  {
    id: "manager-notified",
    label: "Manager notified",
    mcpCall: "actor.contact_manager()",
    details: "Talent agency signed off on schedule shift",
  },
  {
    id: "equipment-extended",
    label: "Equipment extended",
    mcpCall: "equipment.reserve()",
    details: "ARRI Alexa 35 camera package confirmed with rental vendor",
  },
  {
    id: "studio-reserved",
    label: "Studio B reserved",
    mcpCall: "location.confirm()",
    details: "Indoor stage locked in as weather contingency",
  },
  {
    id: "calendar-updated",
    label: "Production calendar updated",
    mcpCall: "calendar.update()",
    details: "Scene 42 shifted on primary production Gantt",
  },
  {
    id: "call-sheet",
    label: "Call sheet regenerated",
    mcpCall: "script.generate_call_sheet()",
    details: "Call Sheet #28 dispatched to all department heads",
  },
  {
    id: "budget-forecast",
    label: "Budget forecast updated",
    mcpCall: "budget.update()",
    details: "Cost variances recorded in production ledger",
  },
];

export function ExecutionChecklist({ execution }: ExecutionChecklistProps) {
  const isCompleted = execution.status === "COMPLETED";

  // Determine completed item count
  const completedCount = useMemo(() => {
    if (isCompleted) return SPEC_EXECUTION_ITEMS.length;
    // When in progress, calculate based on returned steps or minimum 2
    return Math.max(1, Math.min(execution.steps.length, SPEC_EXECUTION_ITEMS.length - 1));
  }, [isCompleted, execution.steps.length]);

  return (
    <section
      aria-label="Execution Checklist Screen"
      className="mt-4 rounded-lg border border-emerald-500/30 bg-zinc-950 p-5 shadow-2xl space-y-5"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-800 pb-3">
        <div className="flex items-center gap-2">
          {isCompleted ? (
            <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-black text-black">
              ✓
            </span>
          ) : (
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
            </span>
          )}
          <h3 className="text-xs font-bold tracking-wider text-emerald-300 uppercase">
            {isCompleted ? "Plan Execution Complete" : "Executing Plan…"}
          </h3>
          <span className="rounded bg-emerald-950/80 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-800/40">
            SPEC §9.10
          </span>
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

      {/* 2-Column Execution Grid: Left = Checklist Animation, Right = MCP Activity */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Left Column: EXECUTING PLAN Checklist */}
        <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/50 p-4">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
            <span className="text-xs font-bold tracking-wider text-zinc-300 uppercase">
              Executing Plan
            </span>
            <span className="text-[10px] text-zinc-400 font-mono">
              {completedCount} / {SPEC_EXECUTION_ITEMS.length} Completed
            </span>
          </div>

          <ul className="mt-3 space-y-2">
            {SPEC_EXECUTION_ITEMS.map((item, index) => {
              const itemDone = isCompleted || index < completedCount;
              const itemCurrent = !isCompleted && index === completedCount;

              return (
                <li
                  key={item.id}
                  className={`flex items-start gap-3 rounded-md border p-2.5 transition-all duration-300 ${
                    itemDone
                      ? "border-emerald-500/30 bg-emerald-950/20 text-zinc-100"
                      : itemCurrent
                      ? "border-amber-400/60 bg-amber-950/30 text-amber-200 ring-1 ring-amber-400/30 animate-pulse"
                      : "border-zinc-800/60 bg-zinc-900/30 text-zinc-500"
                  }`}
                >
                  <div className="mt-0.5">
                    {itemDone ? (
                      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500/20 text-[10px] font-bold text-emerald-400 border border-emerald-500/40">
                        ✓
                      </span>
                    ) : itemCurrent ? (
                      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-amber-500/20 text-[10px] font-bold text-amber-300 border border-amber-500/40 animate-spin">
                        ◌
                      </span>
                    ) : (
                      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-zinc-800 text-[10px] text-zinc-600">
                        ⏳
                      </span>
                    )}
                  </div>

                  <div className="flex-1">
                    <div className="text-xs font-bold leading-tight">
                      {item.label}
                    </div>
                    {item.details && (
                      <div className="mt-0.5 text-[10px] text-zinc-400">
                        {item.details}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>

          {/* Real Backend Executed Steps Log */}
          {execution.steps && execution.steps.length > 0 && (
            <div className="mt-4 border-t border-zinc-800/80 pt-3">
              <span className="text-[10px] font-bold tracking-wider text-zinc-400 uppercase">
                Applied Production State Changes:
              </span>
              <ul className="mt-2 space-y-1.5 font-mono text-[11px] text-zinc-300">
                {execution.steps.map((step, sIdx) => (
                  <li key={sIdx} className="flex items-start gap-1.5">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right Column: MCP Activity Panel */}
        <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/50 p-4">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
            <span className="text-xs font-bold tracking-wider text-cyan-300 uppercase">
              MCP Activity
            </span>
            <span className="text-[10px] text-zinc-500 font-mono">
              Live Stdio Invocation Feed
            </span>
          </div>

          <div className="mt-3 space-y-2 font-mono text-xs">
            {SPEC_EXECUTION_ITEMS.map((item, index) => {
              const callDone = isCompleted || index <= completedCount;

              return (
                <div
                  key={item.id}
                  className={`flex items-center justify-between rounded border px-3 py-2 transition-all ${
                    callDone
                      ? "border-cyan-500/30 bg-cyan-950/20 text-cyan-200"
                      : "border-zinc-800/50 bg-zinc-950/40 text-zinc-600"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        callDone ? "bg-cyan-400" : "bg-zinc-700"
                      }`}
                    />
                    <span className="font-semibold">{item.mcpCall}</span>
                  </div>
                  <span
                    className={`text-[10px] font-bold ${
                      callDone ? "text-emerald-400" : "text-zinc-600"
                    }`}
                  >
                    {callDone ? "OK 200" : "PENDING"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
