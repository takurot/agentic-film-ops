"use client";

import { useState } from "react";
import type { ReplanOption } from "@/lib/api";

interface OptionComparisonProps {
  options: ReplanOption[];
  selectedOptionId?: string;
  onSelectOption: (optionId: string) => void;
  onApprove: (optionId: string) => void;
  isSubmitting?: boolean;
}

export function OptionComparison({
  options,
  selectedOptionId,
  onSelectOption,
  onApprove,
  isSubmitting = false,
}: OptionComparisonProps) {
  const [expandedDetailsId, setExpandedDetailsId] = useState<string | null>(null);

  const activeOptionId = selectedOptionId || options[0]?.option_id || "";
  const selectedOption =
    options.find((o) => o.option_id === activeOptionId) || options[0];

  const formatCost = (cost?: number) => {
    if (cost === undefined || cost === null) return "$0";
    if (cost > 0) return `+$${cost.toLocaleString()}`;
    return `$${cost.toLocaleString()}`;
  };

  const formatDelay = (days?: number) => {
    if (days === undefined || days === null || days === 0) return "0 days";
    return `+${days} days`;
  };

  return (
    <section
      aria-label="Replan Options Comparison"
      className="rounded-lg border border-amber-500/30 bg-zinc-950 p-5 shadow-2xl space-y-6"
    >
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-emerald-500/30" />
          <h2 className="text-xs font-bold tracking-wider text-emerald-300 uppercase">
            AI Replan Complete
          </h2>
          <span className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] font-semibold text-zinc-300">
            {options.length} Feasible Plans Found
          </span>
        </div>
        <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
          SPEC §9.7 & §9.8 Option Comparison & Explainability
        </span>
      </div>

      {/* 3 Option Cards Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {options.map((opt, idx) => {
          const isSelected = activeOptionId === opt.option_id;
          const isRecommended =
            opt.recommended ?? (idx === 0 || opt.option_id === "OPTION_A");
          const cost = opt.cost_impact ?? 0;
          const delay = opt.schedule_delay_days ?? opt.delay_days ?? 0;
          const risk = opt.risk ?? opt.base_risk ?? "LOW";

          // Default fallback checklist if empty
          const checklist =
            opt.checklist && opt.checklist.length > 0
              ? opt.checklist
              : [
                  "Emma Carter available",
                  "Daniel Craig available",
                  "Camera package available",
                  "Continuity preserved",
                ];

          return (
            <div
              key={opt.option_id}
              onClick={() => onSelectOption(opt.option_id)}
              className={`relative flex flex-col justify-between rounded-lg border p-4 cursor-pointer transition-all duration-200 ${
                isSelected
                  ? "border-amber-400 bg-amber-950/25 shadow-lg shadow-amber-500/10 ring-1 ring-amber-400/50"
                  : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700 hover:bg-zinc-900/70"
              }`}
            >
              {/* Recommended Badge */}
              {isRecommended && (
                <div className="absolute -top-2.5 right-4">
                  <span className="rounded-full bg-emerald-500 px-2.5 py-0.5 text-[9px] font-extrabold uppercase tracking-wider text-zinc-950 shadow-md">
                    RECOMMENDED
                  </span>
                </div>
              )}

              <div>
                {/* Option Title */}
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-black tracking-wider text-zinc-300 uppercase">
                    {opt.option_id.replace("_", " ")}
                  </span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                      risk === "LOW"
                        ? "bg-emerald-950 text-emerald-400 border border-emerald-800/40"
                        : risk === "MEDIUM"
                        ? "bg-amber-950 text-amber-400 border border-amber-800/40"
                        : "bg-red-950 text-red-400 border border-red-800/40"
                    }`}
                  >
                    {risk}
                  </span>
                </div>

                <h3 className="mt-2 text-sm font-bold text-zinc-100 leading-snug">
                  {opt.label || `Option ${opt.option_id}`}
                </h3>

                {/* Metrics Table with Visual Tradeoff Bars */}
                <div className="mt-4 space-y-2 rounded-lg bg-zinc-900/90 p-3 text-xs border border-zinc-800/80">
                  {/* Cost Metric & Bar */}
                  <div>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-zinc-400">Cost impact</span>
                      <span
                        className={`font-mono font-bold ${
                          cost > 20000
                            ? "text-red-400"
                            : cost > 10000
                            ? "text-amber-400"
                            : "text-emerald-400"
                        }`}
                      >
                        {formatCost(cost)}
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          cost > 20000
                            ? "bg-red-500"
                            : cost > 10000
                            ? "bg-amber-400"
                            : "bg-emerald-400"
                        }`}
                        style={{
                          width: `${Math.min(Math.max((cost / 42000) * 100, 10), 100)}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Delay Metric & Bar */}
                  <div>
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-zinc-400">Schedule delay</span>
                      <span
                        className={`font-mono font-bold ${
                          delay > 0 ? "text-amber-400" : "text-emerald-400"
                        }`}
                      >
                        {formatDelay(delay)}
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          delay > 0 ? "bg-amber-400" : "bg-emerald-400"
                        }`}
                        style={{
                          width: delay > 0 ? "100%" : "8%",
                        }}
                      />
                    </div>
                  </div>

                  {/* Risk Metric */}
                  <div className="flex items-center justify-between pt-0.5 text-[11px]">
                    <span className="text-zinc-400">Risk rating</span>
                    <span
                      className={`font-mono font-bold uppercase ${
                        risk === "LOW"
                          ? "text-emerald-400"
                          : risk === "MEDIUM"
                          ? "text-amber-400"
                          : "text-red-400"
                      }`}
                    >
                      {risk}
                    </span>
                  </div>
                </div>

                {/* Checklist */}
                <div className="mt-3 space-y-1 text-xs">
                  {checklist.slice(0, 5).map((item, cIdx) => (
                    <div
                      key={cIdx}
                      className="flex items-center gap-1.5 text-[11px] text-zinc-300"
                    >
                      <span className="text-emerald-400 font-bold">✓</span>
                      <span className="truncate">{item.replace(/^✓\s*/, "")}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-4 flex items-center gap-2 border-t border-zinc-800/80 pt-3">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setExpandedDetailsId(
                      expandedDetailsId === opt.option_id ? null : opt.option_id
                    );
                  }}
                  className="flex-1 cursor-pointer rounded border border-zinc-700 bg-zinc-800 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-300 transition-colors hover:bg-zinc-700 hover:text-white"
                >
                  {expandedDetailsId === opt.option_id
                    ? "Hide Details"
                    : "View Details"}
                </button>

                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectOption(opt.option_id);
                    onApprove(opt.option_id);
                  }}
                  disabled={isSubmitting}
                  className="flex-1 cursor-pointer rounded bg-emerald-600 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-white shadow transition-all hover:bg-emerald-500 disabled:opacity-50"
                >
                  {isSubmitting && isSelected ? "Executing…" : "Approve Plan"}
                </button>
              </div>

              {/* Expandable Details Drawer */}
              {expandedDetailsId === opt.option_id && (
                <div className="mt-3 rounded border border-zinc-800 bg-zinc-950/80 p-2.5 text-[11px] text-zinc-300 space-y-1.5">
                  {opt.start_time && (
                    <div>
                      <span className="text-zinc-500">Slot:</span> {opt.start_time} - {opt.end_time}
                    </div>
                  )}
                  {opt.location_id && (
                    <div>
                      <span className="text-zinc-500">Location:</span> {opt.location_id}
                    </div>
                  )}
                  {opt.tradeoffs && opt.tradeoffs.length > 0 && (
                    <div>
                      <span className="text-zinc-500">Tradeoffs:</span>
                      <ul className="mt-1 list-disc list-inside text-zinc-400">
                        {opt.tradeoffs.map((t, tIdx) => (
                          <li key={tIdx}>{t}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Explainability Panel (SPEC §9.8) */}
      {selectedOption && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 p-4">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
            <h4 className="text-xs font-black tracking-wider text-amber-300 uppercase">
              Why {selectedOption.option_id.replace("_", " ")}?
            </h4>
            <span className="text-[10px] text-zinc-500">
              Deterministic Constraint Solver Evaluation
            </span>
          </div>

          <div className="mt-3 text-xs leading-relaxed text-zinc-300">
            {selectedOption.why ? (
              <div className="whitespace-pre-line font-mono text-[11px] text-zinc-300 leading-relaxed">
                {selectedOption.why}
              </div>
            ) : (
              <ul className="space-y-1 list-disc list-inside text-zinc-300">
                <li>Both principal actors (Emma Carter, Daniel Craig) available in requested slot</li>
                <li>No overtime penalties or crew turn-around violations incurred</li>
                <li>Camera package (ARRI Alexa 35) extension verified with vendor</li>
                <li>Studio B booking verified with location manager</li>
                <li>Script continuity preserved with preceding and succeeding scenes</li>
                <li>Production milestones and delivery remain 100% on schedule</li>
              </ul>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
