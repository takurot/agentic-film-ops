"use client";

import { useState } from "react";
import type { ActiveIncident, AnalysisData, ExecutionData } from "@/lib/api";
import {
  startAnalysis,
  fetchAnalysis,
  submitDecision,
  fetchExecution,
} from "@/lib/api";
import { ApprovalPanel, ExecutionChecklist } from "@/components/approval";

/**
 * ActiveIncidentCard – Weather risk alert with AI analysis,
 * Human Approval (SPEC §9.9), and Execution checklist (SPEC §9.10).
 */
export function ActiveIncidentCard({
  incident,
}: {
  incident: ActiveIncident;
}) {
  const [analyzing, setAnalyzing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [execution, setExecution] = useState<ExecutionData | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const { analysis_id } = await startAnalysis(incident.incident_id);
      const analysisData = await fetchAnalysis(analysis_id);
      setAnalysis(analysisData);
    } catch (err) {
      setError(String(err));
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleApprove(optionId: string) {
    if (!analysis) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await submitDecision(analysis.analysis_id, "APPROVE", optionId);
      setAnalysis(updated);
      const execData = await fetchExecution(analysis.analysis_id);
      setExecution(execData);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReject() {
    if (!analysis) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const updated = await submitDecision(analysis.analysis_id, "REJECT");
      setAnalysis(updated);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  const isResolved = incident.resolved || execution?.status === "COMPLETED";
  const isRejected = analysis?.decision === "REJECT";

  return (
    <section
      aria-label="Active Incident"
      className={`relative overflow-hidden rounded-lg border p-5 transition-colors ${
        isResolved
          ? "border-emerald-500/30 bg-emerald-950/10"
          : isRejected
          ? "border-zinc-700 bg-zinc-900/40"
          : "border-red-500/30 bg-red-950/20"
      }`}
    >
      {/* Pulse indicator / Status badge */}
      <div className="absolute top-5 right-5 flex items-center gap-2">
        {isResolved ? (
          <span className="text-[11px] font-bold tracking-wider text-emerald-400 uppercase">
            ✓ Incident Resolved
          </span>
        ) : isRejected ? (
          <span className="text-[11px] font-bold tracking-wider text-zinc-400 uppercase">
            Plan Rejected
          </span>
        ) : (
          <>
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
            </span>
            <span className="text-[11px] font-bold tracking-wider text-red-400 uppercase">
              Active Incident
            </span>
          </>
        )}
      </div>

      {/* Incident Details */}
      <div className="mt-1">
        <h2
          className={`text-base font-bold uppercase ${
            isResolved
              ? "text-emerald-300"
              : isRejected
              ? "text-zinc-300"
              : "text-red-300"
          }`}
        >
          {incident.type === "WEATHER" ? "⛈ Weather Risk" : incident.type}
        </h2>
        <p className="mt-2 text-sm text-zinc-300">{incident.detail}</p>
        <p className="mt-1 text-xs text-zinc-500">
          Scene {incident.scene_id} • Detected{" "}
          {new Date(incident.detected_at).toLocaleString()}
        </p>
      </div>

      {error && (
        <div className="mt-3 rounded border border-red-500/40 bg-red-950/40 p-3 text-xs text-red-300">
          Error: {error}
        </div>
      )}

      {/* Step 1: Start Analysis CTA */}
      {!analysis && (
        <div className="mt-4">
          <button
            id="start-analysis-btn"
            onClick={handleAnalyze}
            disabled={analyzing}
            className="cursor-pointer rounded bg-red-600 px-5 py-2.5 text-xs font-bold tracking-wider text-white uppercase shadow-lg transition-all hover:bg-red-500 hover:shadow-red-500/25 disabled:cursor-wait disabled:opacity-60"
          >
            {analyzing ? "Analyzing…" : "Start AI Impact Analysis"}
          </button>
        </div>
      )}

      {/* Step 2: Approval Gate (SPEC §9.9) */}
      {analysis && !analysis.decision && (
        <ApprovalPanel
          analysis={analysis}
          onApprove={handleApprove}
          onReject={handleReject}
          isSubmitting={isSubmitting}
        />
      )}

      {/* Step 3a: Execution Checklist after APPROVE (SPEC §9.10) */}
      {execution && <ExecutionChecklist execution={execution} />}

      {/* Step 3b: Rejected feedback */}
      {isRejected && (
        <div className="mt-4 rounded-lg border border-zinc-700 bg-zinc-900/60 p-4 text-xs text-zinc-300">
          <p className="font-semibold text-zinc-200">
            Plan rejected. Production state remains unchanged.
          </p>
          <p className="mt-1 text-zinc-400">
            Awaiting Producer manual intervention or revised replan options.
          </p>
        </div>
      )}
    </section>
  );
}
