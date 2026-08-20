"use client";

import { useMemo } from "react";
import type { AnalysisEvent, AgentEvent, AgentEventStatus } from "@/lib/eventStream";
import { isMCPCallEvent } from "@/lib/eventStream";

export interface AgentLiveViewProps {
  events: AnalysisEvent[];
  className?: string;
}

interface AgentNodeConfig {
  id: string; // Used for data-testid
  name: string;
  role: string;
  match: (e: AgentEvent) => boolean;
}

const AGENT_NODES: AgentNodeConfig[] = [
  {
    id: "ACT-001",
    name: "Emma",
    role: "Actor (ACT-001)",
    match: (e) =>
      e.agent === "ActorAgent" &&
      (e.resource === "ACT-001" || e.message.toLowerCase().includes("emma")),
  },
  {
    id: "ACT-002",
    name: "Daniel",
    role: "Actor (ACT-002)",
    match: (e) =>
      e.agent === "ActorAgent" &&
      (e.resource === "ACT-002" || e.message.toLowerCase().includes("daniel")),
  },
  {
    id: "EquipmentAgent",
    name: "Equipment",
    role: "Equipment Agent",
    match: (e) => e.agent === "EquipmentAgent" || e.agent.toLowerCase().includes("equipment"),
  },
  {
    id: "LocationAgent",
    name: "Location",
    role: "Location Agent",
    match: (e) => e.agent === "LocationAgent" || e.agent.toLowerCase().includes("location"),
  },
  {
    id: "BudgetAgent",
    name: "Budget",
    role: "Budget Agent",
    match: (e) => e.agent === "BudgetAgent" || e.agent.toLowerCase().includes("budget"),
  },
];

interface NodeState {
  status: AgentEventStatus | "IDLE";
  message: string;
  lastUpdated?: string;
}

export function AgentLiveView({ events, className = "" }: AgentLiveViewProps) {
  // Extract state for Orchestrator and each domain agent from events
  const { orchestratorState, nodeStates } = useMemo(() => {
    let orchStatus: AgentEventStatus | "IDLE" = "IDLE";
    let orchMessage = "Waiting for analysis to start...";
    let orchUpdated: string | undefined;

    const states: Record<string, NodeState> = {};
    for (const node of AGENT_NODES) {
      states[node.id] = { status: "IDLE", message: "Idle" };
    }

    // Process chronological events
    for (const event of events) {
      if (isMCPCallEvent(event)) {
        continue;
      }
      const agentEvent = event as AgentEvent;

      if (
        agentEvent.agent === "ProductionOrchestrator" ||
        agentEvent.agent === "Orchestrator" ||
        agentEvent.type.startsWith("ANALYSIS_")
      ) {
        orchStatus = agentEvent.status;
        orchMessage = agentEvent.message || agentEvent.status;
        orchUpdated = agentEvent.timestamp;
      }

      // Check domain agents
      for (const node of AGENT_NODES) {
        if (node.match(agentEvent)) {
          states[node.id] = {
            status: agentEvent.status,
            message: agentEvent.message,
            lastUpdated: agentEvent.timestamp,
          };
        }
      }
    }

    return {
      orchestratorState: {
        status: orchStatus,
        message: orchMessage,
        lastUpdated: orchUpdated,
      },
      nodeStates: states,
    };
  }, [events]);

  const isOrchActive =
    orchestratorState.status !== "IDLE" &&
    orchestratorState.status !== "COMPLETED" &&
    orchestratorState.status !== "FAILED";

  return (
    <div
      aria-label="Agent Live View"
      role="region"
      aria-live="polite"
      className={`rounded-lg border border-zinc-800 bg-zinc-950 p-5 shadow-2xl ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-100">
            AI COORDINATION — AGENT LIVE VIEW
          </h2>
        </div>
        <span className="text-[10px] text-zinc-400 uppercase tracking-widest font-mono">
          SPEC §9.2 • Real-time Multi-Agent Network
        </span>
      </div>

      {/* Main Orchestrator Tree Visual */}
      <div className="mt-6 flex flex-col items-center">
        {/* Orchestrator Node */}
        <div
          data-testid="orchestrator-node"
          data-state={isOrchActive ? "active" : "idle"}
          className={`w-full max-w-md rounded-lg border p-3.5 text-center transition-all ${
            isOrchActive
              ? "border-emerald-500/50 bg-emerald-950/20 shadow-lg shadow-emerald-950/40"
              : orchestratorState.status === "COMPLETED"
              ? "border-emerald-700/40 bg-zinc-900/60"
              : "border-zinc-800 bg-zinc-900/40"
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <span
              className={`text-sm ${
                isOrchActive
                  ? "text-emerald-400 animate-pulse"
                  : orchestratorState.status === "COMPLETED"
                  ? "text-emerald-500"
                  : "text-zinc-600"
              }`}
            >
              {isOrchActive || orchestratorState.status === "COMPLETED" ? "●" : "○"}
            </span>
            <span className="text-xs font-bold uppercase tracking-wide text-zinc-100">
              Production Orchestrator
            </span>
          </div>
          <p
            className={`mt-1.5 text-xs truncate ${
              isOrchActive ? "text-emerald-300" : "text-zinc-400"
            }`}
          >
            {orchestratorState.message}
          </p>
          {orchestratorState.lastUpdated && (
            <span className="mt-1 block text-[10px] text-zinc-600">
              Last event: {orchestratorState.lastUpdated}
            </span>
          )}
        </div>

        {/* Tree Connector Lines (SPEC §9.2 Layout) */}
        <div className="relative flex flex-col items-center w-full my-2">
          {/* Vertical stem */}
          <div className="h-5 w-px bg-zinc-700" />
          {/* Horizontal crossbar */}
          <div className="h-px w-[85%] bg-zinc-700 relative">
            <div className="absolute -top-1 left-1/2 -translate-x-1/2 text-zinc-600 text-[10px]">
              MCP / Agent Bus
            </div>
          </div>
          {/* Vertical connectors down to nodes */}
          <div className="w-[85%] flex justify-between">
            {AGENT_NODES.map((node) => (
              <div key={node.id} className="flex flex-col items-center">
                <div className="h-4 w-px bg-zinc-700" />
                <div className="text-zinc-500 text-[9px] -mt-1">↓</div>
              </div>
            ))}
          </div>
        </div>

        {/* Domain Agent Nodes Grid */}
        <div className="grid w-full grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-1">
          {AGENT_NODES.map((node) => {
            const state = nodeStates[node.id] || { status: "IDLE", message: "Idle" };
            const isActive =
              state.status !== "IDLE" &&
              state.status !== "COMPLETED" &&
              state.status !== "FAILED";
            const isCompleted = state.status === "COMPLETED";
            const isFailed = state.status === "FAILED";

            return (
              <div
                key={node.id}
                data-testid={`agent-node-${node.id}`}
                data-state={isActive ? "active" : "idle"}
                className={`flex flex-col justify-between rounded-md border p-3 transition-all ${
                  isActive
                    ? "border-cyan-500/50 bg-cyan-950/20 shadow-md shadow-cyan-950/30"
                    : isCompleted
                    ? "border-emerald-800/40 bg-zinc-900/60"
                    : isFailed
                    ? "border-red-800/40 bg-red-950/20"
                    : "border-zinc-800/80 bg-zinc-900/30"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-[10px] uppercase tracking-wider text-zinc-500">
                      {node.role}
                    </span>
                    <span
                      className={`text-xs ${
                        isActive
                          ? "text-cyan-400 animate-pulse"
                          : isCompleted
                          ? "text-emerald-400"
                          : isFailed
                          ? "text-red-400"
                          : "text-zinc-600"
                      }`}
                    >
                      {isActive || isCompleted ? "●" : isFailed ? "✗" : "○"}
                    </span>
                  </div>
                  <div className="mt-1 text-xs font-bold text-zinc-200">{node.name}</div>
                </div>

                <div className="mt-3 border-t border-zinc-800/60 pt-2">
                  <div
                    className={`text-[10px] leading-tight font-medium ${
                      isActive
                        ? "text-cyan-300"
                        : isCompleted
                        ? "text-emerald-300"
                        : isFailed
                        ? "text-red-300"
                        : "text-zinc-500"
                    }`}
                  >
                    {state.message}
                  </div>
                  {state.lastUpdated && (
                    <div className="mt-1 text-[9px] text-zinc-600">
                      {state.lastUpdated}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
