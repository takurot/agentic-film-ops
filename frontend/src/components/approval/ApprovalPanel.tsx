"use client";

import { useState } from "react";
import type { AnalysisData } from "@/lib/api";

interface ApprovalPanelProps {
  analysis: AnalysisData;
  onApprove: (optionId: string) => void;
  onReject: () => void;
  isSubmitting?: boolean;
}

export function ApprovalPanel({
  analysis,
  onApprove,
  onReject,
  isSubmitting = false,
}: ApprovalPanelProps) {
  const options = analysis.options || [];
  const [selectedOptionId, setSelectedOptionId] = useState<string>(
    options[0]?.option_id ?? ""
  );

  const hasOptions = options.length > 0;

  return (
    <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-950/10 p-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-amber-500/20 pb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-amber-400" />
          <h3 className="text-sm font-bold tracking-wider text-amber-300 uppercase">
            Human Approval Required (SPEC §9.9)
          </h3>
        </div>
        <span className="text-[11px] text-zinc-400">
          Analysis ID: {analysis.analysis_id}
        </span>
      </div>

      {/* AI Explainability */}
      {analysis.explainability && (
        <div className="mt-3 rounded bg-zinc-900/60 p-3 border border-zinc-800">
          <span className="text-[11px] font-semibold tracking-wider text-zinc-400 uppercase">
            AI Impact & Feasibility Assessment:
          </span>
          <p className="mt-1 text-xs leading-relaxed text-zinc-300">
            {analysis.explainability}
          </p>
        </div>
      )}

      {/* Options List */}
      <div className="mt-4 space-y-2.5">
        <span className="text-[11px] font-bold tracking-wider text-zinc-300 uppercase">
          Generated Replan Options:
        </span>

        {!hasOptions ? (
          <div className="rounded border border-red-500/30 bg-red-950/20 p-4 text-center text-xs text-red-300">
            No feasible plan found. Manual intervention required.
          </div>
        ) : (
          options.map((opt) => {
            const isSelected = selectedOptionId === opt.option_id;
            const costImpact = opt.cost_impact ?? 0;
            const delayDays = opt.delay_days ?? opt.schedule_delay_days ?? 0;
            const risk = opt.risk ?? opt.base_risk ?? "LOW";

            return (
              <label
                key={opt.option_id}
                htmlFor={`option-${opt.option_id}`}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-all ${
                  isSelected
                    ? "border-amber-500/80 bg-amber-950/30 shadow-md shadow-amber-950/50"
                    : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-700"
                }`}
              >
                <input
                  type="radio"
                  id={`option-${opt.option_id}`}
                  name="approval-option"
                  value={opt.option_id}
                  checked={isSelected}
                  onChange={() => setSelectedOptionId(opt.option_id)}
                  disabled={isSubmitting}
                  className="mt-1 text-amber-500 focus:ring-amber-500"
                />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-100">
                      {opt.label || `Option ${opt.option_id}`}
                    </span>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-bold tracking-wide ${
                        risk === "LOW"
                          ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800/50"
                          : risk === "MEDIUM"
                          ? "bg-amber-950/80 text-amber-400 border border-amber-800/50"
                          : "bg-red-950/80 text-red-400 border border-red-800/50"
                      }`}
                    >
                      {risk} RISK
                    </span>
                  </div>

                  <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-zinc-400">
                    <div>
                      Cost Impact:{" "}
                      <span className="font-semibold text-zinc-200">
                        {costImpact > 0
                          ? `+$${costImpact.toLocaleString()}`
                          : `$${costImpact.toLocaleString()}`}
                      </span>
                    </div>
                    <div>
                      Schedule Delay:{" "}
                      <span className="font-semibold text-zinc-200">
                        {delayDays === 0 ? "0 DAYS" : `+${delayDays} DAYS`}
                      </span>
                    </div>
                    {opt.start_time && opt.end_time && (
                      <div className="text-[11px] text-zinc-500">
                        Slot: {opt.start_time.split("T")[1] || opt.start_time} -{" "}
                        {opt.end_time.split("T")[1] || opt.end_time}
                      </div>
                    )}
                  </div>
                </div>
              </label>
            );
          })
        )}
      </div>

      {/* Action CTA Buttons */}
      <div className="mt-5 flex items-center gap-3 pt-2">
        <button
          id="approve-plan-btn"
          type="button"
          onClick={() => selectedOptionId && onApprove(selectedOptionId)}
          disabled={isSubmitting || !hasOptions || !selectedOptionId}
          className="cursor-pointer rounded bg-emerald-600 px-5 py-2.5 text-xs font-bold tracking-wider text-white uppercase shadow-lg transition-all hover:bg-emerald-500 hover:shadow-emerald-500/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? "Executing…" : "Approve & Execute"}
        </button>

        <button
          id="reject-plan-btn"
          type="button"
          onClick={onReject}
          disabled={isSubmitting}
          className="cursor-pointer rounded border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-xs font-bold tracking-wider text-zinc-300 uppercase transition-all hover:bg-zinc-700 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reject Plan
        </button>
      </div>
    </div>
  );
}
