"use client";

import { useState } from "react";
import type { AnalysisData } from "@/lib/api";
import { OptionComparison } from "./OptionComparison";

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
    <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-950/10 p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-amber-500/20 pb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-amber-400 animate-pulse" />
          <h3 className="text-sm font-bold tracking-wider text-amber-300 uppercase">
            Human Approval Required (SPEC §9.9)
          </h3>
        </div>
        <span className="text-[11px] text-zinc-400 font-mono">
          Analysis ID: {analysis.analysis_id}
        </span>
      </div>

      {/* AI Explainability Summary */}
      {analysis.explainability && (
        <div className="rounded-lg bg-zinc-900/80 p-3.5 border border-zinc-800">
          <span className="text-[11px] font-bold tracking-wider text-zinc-400 uppercase">
            AI Impact & Feasibility Assessment:
          </span>
          <p className="mt-1 text-xs leading-relaxed text-zinc-300">
            {analysis.explainability}
          </p>
        </div>
      )}

      {/* Replan Option Comparison Grid (SPEC §9.7 & §9.8) */}
      {hasOptions ? (
        <OptionComparison
          options={options}
          selectedOptionId={selectedOptionId}
          onSelectOption={(optId) => setSelectedOptionId(optId)}
          onApprove={onApprove}
          isSubmitting={isSubmitting}
        />
      ) : (
        <div className="rounded border border-red-500/30 bg-red-950/20 p-4 text-center text-xs text-red-300">
          No feasible plan found. Manual intervention required.
        </div>
      )}

      {/* Primary Action Buttons */}
      <div className="flex items-center gap-3 border-t border-amber-500/20 pt-4">
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
