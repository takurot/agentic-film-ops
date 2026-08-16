"use client";

import { useState } from "react";
import type { ActiveIncident } from "@/lib/api";
import { startAnalysis } from "@/lib/api";

/**
 * ActiveIncidentCard – Weather risk alert with "START AI IMPACT ANALYSIS" CTA (SPEC §9.1).
 */
export function ActiveIncidentCard({
  incident,
}: {
  incident: ActiveIncident;
}) {
  const [loading, setLoading] = useState(false);
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  async function handleAnalyze() {
    setLoading(true);
    try {
      const result = await startAnalysis(incident.incident_id);
      setAnalysisId(result.analysis_id);
    } catch {
      // In production we'd show a toast; for now keep the button actionable.
      setLoading(false);
    }
  }

  return (
    <section
      aria-label="Active Incident"
      className="relative overflow-hidden rounded-lg border border-red-500/30 bg-red-950/20 p-5"
    >
      {/* Pulse indicator */}
      <div className="absolute top-5 right-5 flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
        </span>
        <span className="text-[11px] font-bold tracking-wider text-red-400 uppercase">
          Active Incident
        </span>
      </div>

      <div className="mt-1">
        <h2 className="text-base font-bold text-red-300 uppercase">
          {incident.type === "WEATHER" ? "⛈ Weather Risk" : incident.type}
        </h2>
        <p className="mt-2 text-sm text-zinc-300">{incident.detail}</p>
        <p className="mt-1 text-xs text-zinc-500">
          Scene {incident.scene_id} • Detected{" "}
          {new Date(incident.detected_at).toLocaleString()}
        </p>
      </div>

      <div className="mt-4">
        {analysisId ? (
          <span className="inline-flex items-center gap-2 rounded bg-emerald-600/20 px-4 py-2 text-xs font-semibold text-emerald-400">
            ✓ Analysis started — {analysisId}
          </span>
        ) : (
          <button
            id="start-analysis-btn"
            onClick={handleAnalyze}
            disabled={loading}
            className="cursor-pointer rounded bg-red-600 px-5 py-2.5 text-xs font-bold tracking-wider text-white uppercase shadow-lg transition-all hover:bg-red-500 hover:shadow-red-500/25 disabled:cursor-wait disabled:opacity-60"
          >
            {loading ? "Analyzing…" : "Start AI Impact Analysis"}
          </button>
        )}
      </div>
    </section>
  );
}
