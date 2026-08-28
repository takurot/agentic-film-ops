"use client";

import { useEffect, useRef, useState } from "react";
import type { ActiveIncident, AnalysisData, ExecutionData, LiveApiClient } from "@/lib/api";
import { ApprovalPanel, ExecutionChecklist } from "@/components/approval";
import { BeforeAfterSummary } from "@/components/summary";
import {
  AgentLiveView,
  McpActivityMonitor,
  ExternalCommunicationMock,
} from "@/components/live";
import { ResourceNetworkView } from "@/components/network";
import { connectEventStream, type AgentEvent, type AnalysisEvent, type EventStreamState } from "@/lib/eventStream";
import { PhaseStepIndicator, type ResolutionPhase } from "./PhaseStepIndicator";
import {
  MOCK_ANALYSIS,
  MOCK_EXECUTION,
  MOCK_STREAM_EVENTS,
} from "@/lib/mockData";

const MAX_EVENTS = 200;
type IncidentErrorCode = "ANALYSIS_FAILED" | "BACKEND_TIMEOUT" | "BACKEND_UNAVAILABLE" | "EXECUTION_UNAVAILABLE" | "INVALID_BACKEND_RESPONSE" | "INVALID_EVENT_STREAM" | "REQUEST_REJECTED";
const ERROR_MESSAGES: Record<IncidentErrorCode, string> = {
  ANALYSIS_FAILED: "The AI analysis did not complete. Retry the analysis.",
  BACKEND_TIMEOUT: "The Live backend timed out. Retry when the service is responsive.",
  BACKEND_UNAVAILABLE: "The Live backend is unavailable. Retry the operation.",
  EXECUTION_UNAVAILABLE: "Approval succeeded, but execution status is unavailable. Retry status retrieval.",
  INVALID_BACKEND_RESPONSE: "The Live backend returned an invalid response. Retry or verify the deployment.",
  INVALID_EVENT_STREAM: "The Live event stream was invalid. Retry the event stream.",
  REQUEST_REJECTED: "The Live backend rejected this operation. Refresh the dashboard before retrying.",
};

function classifyError(error: unknown): IncidentErrorCode {
  if (!(error instanceof Error)) return "BACKEND_UNAVAILABLE";
  if (error.name === "TimeoutError") return "BACKEND_TIMEOUT";
  if (error.message === "INVALID_BACKEND_RESPONSE") return "INVALID_BACKEND_RESPONSE";
  if (/^BACKEND_UNAVAILABLE:4\d\d$/.test(error.message)) return "REQUEST_REJECTED";
  return "BACKEND_UNAVAILABLE";
}

function resolvePhase(isResolved: boolean, analysis: AnalysisData | null, analyzing: boolean): ResolutionPhase {
  if (isResolved) return "RESOLVED";
  if (analysis?.status === "COMPLETED" && !analysis.decision) return "OPTIONS";
  if (analysis?.status === "FAILED") return "ALERT";
  if (analyzing || analysis) return "ANALYZING";
  return "ALERT";
}

function isAgentEvent(event: AnalysisEvent): event is AgentEvent {
  return event.type !== "MCP_CALL" && "agent" in event;
}

function isSameEvent(a: AnalysisEvent, b: AnalysisEvent): boolean {
  if (isAgentEvent(a) && isAgentEvent(b)) {
    if (a.event_id && b.event_id) return a.event_id === b.event_id;
    return (
      a.timestamp === b.timestamp &&
      a.agent === b.agent &&
      a.type === b.type &&
      a.status === b.status &&
      a.message === b.message
    );
  }
  if (!isAgentEvent(a) && !isAgentEvent(b)) {
    if (a.call_id && b.call_id) return a.call_id === b.call_id && a.status === b.status;
    return (
      a.timestamp === b.timestamp &&
      a.server === b.server &&
      a.tool === b.tool &&
      a.status === b.status &&
      a.message === b.message
    );
  }
  return false;
}

/**
 * ActiveIncidentCard – Weather risk alert with AI analysis,
 * Agent Live View (SPEC §9.2), MCP Activity Monitor (SPEC §9.3),
 * External Communication Mock (SPEC §9.5), Human Approval (SPEC §9.9),
 * and Execution checklist (SPEC §9.10).
 */
export function ActiveIncidentCard({
  incident,
  runtimeMode,
  client,
}: { incident: ActiveIncident } & (
  | { runtimeMode: "LIVE_GEMINI"; client: LiveApiClient }
  | { runtimeMode: "RECORDED_REPLAY"; client: null }
)) {
  const [analyzing, setAnalyzing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [execution, setExecution] = useState<ExecutionData | null>(null);
  const [events, setEvents] = useState<AnalysisEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [streamState, setStreamState] = useState<EventStreamState | null>(null);
  const [streamGeneration, setStreamGeneration] = useState(0);
  const [executionRetryId, setExecutionRetryId] = useState<string | null>(null);
  const operationController = useRef<AbortController | null>(null);

  useEffect(() => () => {
    const operation = operationController.current;
    operationController.current = null;
    operation?.abort();
  }, []);

  // Subscribe to SSE stream whenever an analysis is created

  useEffect(() => {
    if (runtimeMode !== "LIVE_GEMINI" || !client || !analysis?.analysis_id || analysis.decision) return;

    const streamUrl = `${client.apiBase}/api/analyses/${encodeURIComponent(analysis.analysis_id)}/events/stream`;
    const unsubscribe = connectEventStream(
      streamUrl,
      (event) => {
        setEvents((prev) => {
          if (prev.some((existing) => isSameEvent(existing, event))) return prev;
          return [...prev, event].slice(-MAX_EVENTS);
        });

        // Trigger analysis refresh when completion/failure event arrives
        if (
          event.type === "ANALYSIS_COMPLETED" ||
          (isAgentEvent(event) && (event.agent === "Orchestrator" || event.agent === "ProductionOrchestrator") && event.status === "COMPLETED")
        ) {
          client.fetchAnalysis(analysis.analysis_id).then((completedData) => {
            if (completedData.status === "COMPLETED" || completedData.status === "FAILED") {
              setAnalysis(completedData);
              setAnalyzing(false);
              if (completedData.status === "FAILED") {
                setError("ANALYSIS_FAILED");
              }
            }
          }).catch(() => {
            setError("ANALYSIS_FAILED");
            setAnalyzing(false);
          });
        } else if (
          event.type === "ANALYSIS_FAILED" ||
          (isAgentEvent(event) && (event.agent === "Orchestrator" || event.agent === "ProductionOrchestrator") && event.status === "FAILED")
        ) {
          setError("ANALYSIS_FAILED");
          setAnalyzing(false);
        }

      },
      { onStateChange: setStreamState, onProtocolError: () => setError("INVALID_EVENT_STREAM") }
    );

    return () => {
      unsubscribe();
    };
  }, [analysis?.analysis_id, analysis?.decision, client, runtimeMode, streamGeneration]);


  // Polling fallback while analyzing in LIVE mode
  useEffect(() => {
    if (runtimeMode !== "LIVE_GEMINI" || !client || !analysis?.analysis_id || !analyzing || analysis.decision) return;
    if (analysis.status !== "QUEUED" && analysis.status !== "ANALYZING") return;

    const interval = setInterval(async () => {
      try {
        const latest = await client.fetchAnalysis(analysis.analysis_id);
        if (latest.status === "COMPLETED") {
          setAnalysis(latest);
          setAnalyzing(false);
        } else if (latest.status === "FAILED") {
          setAnalysis(latest);
          setError("ANALYSIS_FAILED");
          setAnalyzing(false);
        }
      } catch {
        // Continue polling or let SSE / timeout handle
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [analysis?.analysis_id, analysis?.status, analysis?.decision, analyzing, client, runtimeMode]);

  function beginOperation(): AbortController {
    operationController.current?.abort();
    const controller = new AbortController();
    operationController.current = controller;
    return controller;
  }

  async function handleAnalyze() {
    setAnalyzing(true);
    setError(null);
    setEvents([]);
    setAnalysis(null);
    setExecution(null);
    setExecutionRetryId(null);
    if (runtimeMode === "RECORDED_REPLAY") {
      setAnalysis(MOCK_ANALYSIS);
      setEvents(MOCK_STREAM_EVENTS.slice(-MAX_EVENTS));
      setAnalyzing(false);
      return;
    }
    let operation: AbortController | null = null;
    try {
      operation = beginOperation();
      const { analysis_id } = await client.startAnalysis(incident.incident_id, operation.signal);
      const analysisData = await client.fetchAnalysis(analysis_id, operation.signal);
      if (operationController.current !== operation) return;
      setAnalysis(analysisData);
      if (analysisData.status === "FAILED") {
        setError("ANALYSIS_FAILED");
        setAnalyzing(false);
      } else if (analysisData.status === "COMPLETED") {
        setAnalyzing(false);
      }
    } catch (caught) {
      if (operation && operationController.current === operation) {
        setError(classifyError(caught));
        setAnalyzing(false);
      }
    }
  }

  async function handleApprove(optionId: string) {

    if (!analysis) return;
    setIsSubmitting(true);
    setError(null);
    if (runtimeMode === "RECORDED_REPLAY") {
      setAnalysis({
        ...analysis,
        decision: "APPROVE",
        decided_option_id: optionId,
        execution_status: "COMPLETED",
      });
      setExecution(MOCK_EXECUTION);
      setIsSubmitting(false);
      return;
    }
    let operation: AbortController | null = null;
    try {
      operation = beginOperation();
      const updated = await client.submitDecision(
        analysis.analysis_id,
        "APPROVE",
        optionId,
        operation.signal
      );
      if (operationController.current !== operation) return;
      setAnalysis(updated);
      try {
        const execData = await client.fetchExecution(analysis.analysis_id, operation.signal);
        if (operationController.current !== operation) return;
        setExecution(execData);
        setExecutionRetryId(null);
      } catch {
        if (operationController.current === operation) {
          setExecutionRetryId(analysis.analysis_id);
          setError("EXECUTION_UNAVAILABLE");
        }
      }
    } catch (caught) {
      if (operation && operationController.current === operation) setError(classifyError(caught));
    } finally {
      if (!operation || operationController.current === operation) setIsSubmitting(false);
    }
  }

  async function handleReject() {
    if (!analysis) return;
    setIsSubmitting(true);
    setError(null);
    if (runtimeMode === "RECORDED_REPLAY") {
      setAnalysis({
        ...analysis,
        decision: "REJECT",
        decided_option_id: null,
      });
      setIsSubmitting(false);
      return;
    }
    let operation: AbortController | null = null;
    try {
      operation = beginOperation();
      const updated = await client.submitDecision(
        analysis.analysis_id,
        "REJECT",
        undefined,
        operation.signal
      );

      if (operationController.current !== operation) return;
      setAnalysis(updated);
    } catch (caught) {
      if (operation && operationController.current === operation) setError(classifyError(caught));
    } finally {
      if (!operation || operationController.current === operation) setIsSubmitting(false);
    }
  }

  async function retryExecution() {
    if (!client || !analysis) return;
    setIsSubmitting(true);
    setError(null);
    let operation: AbortController | null = null;
    try {
      operation = beginOperation();
      if (executionRetryId) {
        const executionData = await client.fetchExecution(executionRetryId, operation.signal);
        if (operationController.current !== operation) return;
        setExecution(executionData);
        setExecutionRetryId(null);
        return;
      }
      const optionId = analysis.decided_option_id || undefined;
      const updated = await client.submitDecision(
        analysis.analysis_id,
        "APPROVE",
        optionId,
        operation.signal
      );
      if (operationController.current !== operation) return;
      setAnalysis(updated);
      try {
        const executionData = await client.fetchExecution(analysis.analysis_id, operation.signal);
        if (operationController.current !== operation) return;
        setExecution(executionData);
        setExecutionRetryId(null);
      } catch {
        if (operationController.current === operation) {
          setExecutionRetryId(analysis.analysis_id);
          setError("EXECUTION_UNAVAILABLE");
        }
      }
    } catch (caught) {
      if (operation && operationController.current === operation) setError(classifyError(caught));
    } finally {
      if (!operation || operationController.current === operation) setIsSubmitting(false);
    }
  }



  const isResolved = incident.resolved || execution?.status === "COMPLETED";
  const isRejected = analysis?.decision === "REJECT";

  const currentPhase = resolvePhase(isResolved, analysis, analyzing);

  return (
    <section
      id="incident-section"
      aria-label="Active Incident"
      className={`relative overflow-hidden rounded-xl border p-5 transition-colors ${
        isResolved
          ? "border-emerald-500/30 bg-emerald-950/10"
          : isRejected
          ? "border-zinc-700 bg-zinc-900/40"
          : "border-red-500/30 bg-red-950/20"
      }`}
    >
      {/* 4-Phase Progress Step Indicator (Issue #74) */}
      <PhaseStepIndicator currentPhase={currentPhase} />

      {/* Pulse indicator / Status badge */}
      <div className="absolute top-5 right-5 hidden sm:flex items-center gap-2">
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
      <div className="mt-3">
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
        <p className="mt-1 text-xs text-zinc-400">
          Scene {incident.scene_id} • Detected{" "}
          {new Date(incident.detected_at).toLocaleString("en-US", { timeZone: "UTC" })} UTC
        </p>
      </div>

      {error && (
        <div role="alert" data-error-code={error} className="mt-3 rounded border border-red-500/40 bg-red-950/40 p-3 text-xs text-red-300">
          {ERROR_MESSAGES[error as IncidentErrorCode] ?? ERROR_MESSAGES.BACKEND_UNAVAILABLE}
        </div>
      )}
      {analysis?.status === "FAILED" && (
        <button type="button" onClick={() => void handleAnalyze()} disabled={analyzing} className="mt-3 rounded border border-red-500/50 px-3 py-2 text-xs font-bold text-red-200">
          Retry analysis
        </button>
      )}
      {executionRetryId && (
        <button type="button" onClick={() => void retryExecution()} disabled={isSubmitting} className="mt-3 rounded border border-red-500/50 px-3 py-2 text-xs font-bold text-red-200">
          Retry execution status
        </button>
      )}

      {/* Step 1: Start Analysis CTA */}
      {!analysis && (
        <div className="mt-4">
          <button
            id="start-analysis-btn"
            onClick={handleAnalyze}
            disabled={analyzing}
            className="cursor-pointer rounded-lg bg-red-600 px-5 py-2.5 text-xs font-bold tracking-wider text-white uppercase shadow-lg transition-all hover:bg-red-500 hover:shadow-red-500/25 disabled:cursor-wait disabled:opacity-60"
          >
            {analyzing ? "Analyzing…" : runtimeMode === "RECORDED_REPLAY" ? "Play Recorded Analysis" : "Start AI Impact Analysis"}
          </button>
        </div>
      )}

      {/* Live Coordination, Activity Monitor & Communication Views */}
      {(analysis || analyzing) && (
        <div id="agent-orchestration-section" className="mt-6 space-y-4">
          {runtimeMode === "LIVE_GEMINI" && streamState && <div className="flex items-center gap-2"><p className="text-[10px] font-mono text-zinc-400" role="status">EVENT STREAM: {streamState}</p>{streamState === "FAILED" && <button type="button" onClick={() => { setError(null); setStreamGeneration((value) => value + 1); }} className="text-[10px] font-bold text-cyan-300 underline">Retry event stream</button>}</div>}
          {/* Resource Network View (SPEC §9.4 Flagship Screen) */}
          <ResourceNetworkView events={events} />

          {/* Agent Live View (SPEC §9.2) */}
          <AgentLiveView events={events} replay={runtimeMode === "RECORDED_REPLAY"} />

          {/* 2-Column Grid: Communication Mock (SPEC §9.5) & MCP Activity Monitor (SPEC §9.3) */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ExternalCommunicationMock />
            <McpActivityMonitor events={events} replay={runtimeMode === "RECORDED_REPLAY"} />
          </div>
        </div>
      )}

      {/* Step 2: Approval Gate (SPEC §9.9) */}
      {analysis?.status === "COMPLETED" && !analysis.decision && (
        <div id="option-comparison-section" className="mt-6">
          <ApprovalPanel
            analysis={analysis}
            onApprove={handleApprove}
            onReject={handleReject}
            isSubmitting={isSubmitting}
          />
        </div>
      )}

      {/* Step 3 & 4: Execution Checklist & Summary (SPEC §9.10 / §9.11) */}
      <div id="execution-summary-section" className="space-y-4">
        {execution && (
          <div className="mt-6">
            <ExecutionChecklist
              execution={execution}
              onRetry={retryExecution}
              retrying={isSubmitting}
            />
          </div>
        )}

        {isResolved && (
          <div className="mt-6">
            <BeforeAfterSummary
              incident={incident}
              analysis={analysis}
              execution={execution}
              events={events}
              runtimeMode={runtimeMode}
            />
          </div>
        )}
      </div>

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
