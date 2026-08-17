"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  type Node,
  type Edge,
} from "reactflow";
import "reactflow/dist/style.css";
import type { AnalysisEvent } from "@/lib/eventStream";

interface ResourceNetworkViewProps {
  events?: AnalysisEvent[];
}

interface NodeData {
  label: string;
  subLabel?: string;
  type: "orchestrator" | "mcp" | "scene" | "agent" | "resource" | "external";
  status: "idle" | "active" | "completed" | "waiting";
}

/**
 * Custom Node View for Resource Network
 */
function CustomResourceNode({ data }: { data: NodeData }) {
  const statusStyles = {
    idle: "border-zinc-800 bg-zinc-900/80 text-zinc-400 shadow-sm",
    active:
      "border-amber-400 bg-amber-950/60 text-amber-200 shadow-lg shadow-amber-500/20 ring-2 ring-amber-400/50 animate-pulse",
    completed:
      "border-emerald-500 bg-emerald-950/40 text-emerald-200 shadow-md shadow-emerald-500/20",
    waiting:
      "border-cyan-400 bg-cyan-950/60 text-cyan-200 shadow-lg shadow-cyan-500/20 ring-2 ring-cyan-400/40 animate-pulse",
  }[data.status];

  const typeBadges = {
    orchestrator: "bg-purple-900/60 text-purple-300 border-purple-700/50",
    mcp: "bg-blue-900/60 text-blue-300 border-blue-700/50",
    scene: "bg-rose-900/60 text-rose-300 border-rose-700/50",
    agent: "bg-emerald-900/60 text-emerald-300 border-emerald-700/50",
    resource: "bg-amber-900/60 text-amber-300 border-amber-700/50",
    external: "bg-cyan-900/60 text-cyan-300 border-cyan-700/50",
  }[data.type];

  return (
    <div
      className={`min-w-[140px] rounded-lg border px-3 py-2.5 backdrop-blur-sm transition-all duration-300 ${statusStyles}`}
    >
      <div className="flex items-center justify-between gap-1.5 pb-1">
        <span
          className={`rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${typeBadges}`}
        >
          {data.type}
        </span>
        <span
          className={`h-2 w-2 rounded-full ${
            data.status === "active"
              ? "bg-amber-400 animate-ping"
              : data.status === "waiting"
              ? "bg-cyan-400 animate-pulse"
              : data.status === "completed"
              ? "bg-emerald-400"
              : "bg-zinc-600"
          }`}
        />
      </div>
      <div className="text-xs font-bold leading-tight">{data.label}</div>
      {data.subLabel && (
        <div className="mt-0.5 text-[10px] text-zinc-400 leading-none">
          {data.subLabel}
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  resourceNode: CustomResourceNode,
};

export function ResourceNetworkView({ events = [] }: ResourceNetworkViewProps) {
  // Determine active/completed statuses from stream events
  const agentStatuses = useMemo(() => {
    const map = new Map<string, "idle" | "active" | "completed" | "waiting">();

    for (const ev of events) {
      if ("agent" in ev && ev.agent) {
        const agent = ev.agent.toLowerCase();
        if (ev.status === "COMPLETED") {
          map.set(agent, "completed");
        } else if (
          ev.status === "WAITING_EXTERNAL" ||
          ev.type === "EXTERNAL_REQUEST"
        ) {
          map.set(agent, "waiting");
        } else if (
          ev.status === "QUERYING_MCP" ||
          ev.status === "THINKING" ||
          ev.status === "ANALYZING"
        ) {
          map.set(agent, "active");
        }
      }
    }
    return map;
  }, [events]);

  // Build initial graph nodes layout matching SPEC §9.4
  const nodes: Node[] = useMemo(() => {
    const hasActor = agentStatuses.has("actoragent");
    const hasEquipment = agentStatuses.has("equipmentagent");
    const hasLocation = agentStatuses.has("locationagent");
    const hasScript = agentStatuses.has("scriptagent");

    return [
      // Top Center: Gemini Orchestrator
      {
        id: "orchestrator",
        type: "resourceNode",
        position: { x: 380, y: 30 },
        data: {
          label: "Gemini Orchestrator",
          subLabel: "Production Control Tower",
          type: "orchestrator",
          status: events.length > 0 ? "active" : "idle",
        },
      },
      // Center: MCP Gateway
      {
        id: "mcp-gateway",
        type: "resourceNode",
        position: { x: 395, y: 130 },
        data: {
          label: "MCP Connective Layer",
          subLabel: "stdio transport bus",
          type: "mcp",
          status: events.length > 0 ? "completed" : "idle",
        },
      },
      // Scene 42 Root
      {
        id: "scene-42",
        type: "resourceNode",
        position: { x: 60, y: 130 },
        data: {
          label: "Scene 42",
          subLabel: "Rooftop Confrontation",
          type: "scene",
          status: events.length > 0 ? "active" : "idle",
        },
      },
      // Weather MCP / Agent
      {
        id: "weather-node",
        type: "resourceNode",
        position: { x: 60, y: 230 },
        data: {
          label: "Weather Agent",
          subLabel: "92% Rain Risk",
          type: "agent",
          status: agentStatuses.get("weatheragent") ?? (events.length > 0 ? "completed" : "idle"),
        },
      },
      // Script Agent
      {
        id: "script-node",
        type: "resourceNode",
        position: { x: 220, y: 230 },
        data: {
          label: "Script Agent",
          subLabel: "Continuity Valid",
          type: "agent",
          status: agentStatuses.get("scriptagent") ?? (hasScript ? "completed" : "idle"),
        },
      },
      // Actor Agent & Resource & Manager
      {
        id: "actor-node",
        type: "resourceNode",
        position: { x: 380, y: 230 },
        data: {
          label: "Actor Agent",
          subLabel: "Emma Carter / Daniel",
          type: "agent",
          status: agentStatuses.get("actoragent") ?? (hasActor ? "active" : "idle"),
        },
      },
      {
        id: "actor-emma",
        type: "resourceNode",
        position: { x: 380, y: 330 },
        data: {
          label: "Emma Carter",
          subLabel: "Principal Cast (ACT-001)",
          type: "resource",
          status: hasActor ? "active" : "idle",
        },
      },
      {
        id: "actor-manager",
        type: "resourceNode",
        position: { x: 380, y: 430 },
        data: {
          label: "Talent Agency Mgr",
          subLabel: "Confirmed: Avail after 4PM",
          type: "external",
          status:
            agentStatuses.get("actoragent") === "waiting"
              ? "waiting"
              : hasActor
              ? "completed"
              : "idle",
        },
      },
      // Equipment Agent & Resource & Rental
      {
        id: "equipment-node",
        type: "resourceNode",
        position: { x: 550, y: 230 },
        data: {
          label: "Equipment Agent",
          subLabel: "ARRI Alexa 35 Package",
          type: "agent",
          status:
            agentStatuses.get("equipmentagent") ?? (hasEquipment ? "active" : "idle"),
        },
      },
      {
        id: "equipment-alexa",
        type: "resourceNode",
        position: { x: 550, y: 330 },
        data: {
          label: "ARRI Alexa 35",
          subLabel: "Camera Kit (EQ-001)",
          type: "resource",
          status: hasEquipment ? "active" : "idle",
        },
      },
      {
        id: "equipment-vendor",
        type: "resourceNode",
        position: { x: 550, y: 430 },
        data: {
          label: "Cinema Rental Tokyo",
          subLabel: "Vendor: Extension OK",
          type: "external",
          status:
            agentStatuses.get("equipmentagent") === "waiting"
              ? "waiting"
              : hasEquipment
              ? "completed"
              : "idle",
        },
      },
      // Location Agent & Resource & Owner
      {
        id: "location-node",
        type: "resourceNode",
        position: { x: 720, y: 230 },
        data: {
          label: "Location Agent",
          subLabel: "Shibuya Rooftop / Studio B",
          type: "agent",
          status:
            agentStatuses.get("locationagent") ?? (hasLocation ? "active" : "idle"),
        },
      },
      {
        id: "location-rooftop",
        type: "resourceNode",
        position: { x: 720, y: 330 },
        data: {
          label: "Rooftop Shibuya",
          subLabel: "Location (LOC-003)",
          type: "resource",
          status: hasLocation ? "active" : "idle",
        },
      },
      {
        id: "location-owner",
        type: "resourceNode",
        position: { x: 720, y: 430 },
        data: {
          label: "Building Manager",
          subLabel: "Owner: Rain contingency",
          type: "external",
          status:
            agentStatuses.get("locationagent") === "waiting"
              ? "waiting"
              : hasLocation
              ? "completed"
              : "idle",
        },
      },
    ];
  }, [events.length, agentStatuses]);

  // Edges connecting nodes with dynamic animated propagation
  const edges: Edge[] = useMemo(() => {
    const hasWeather = agentStatuses.has("weatheragent");
    const hasActor = agentStatuses.has("actoragent");
    const hasEquipment = agentStatuses.has("equipmentagent");
    const hasLocation = agentStatuses.has("locationagent");
    const hasScript = agentStatuses.has("scriptagent");

    return [
      {
        id: "e-orch-mcp",
        source: "orchestrator",
        target: "mcp-gateway",
        animated: events.length > 0,
        style: { stroke: "#a855f7", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#a855f7" },
      },
      {
        id: "e-scene-weather",
        source: "scene-42",
        target: "weather-node",
        animated: events.length > 0,
        style: { stroke: "#f43f5e", strokeWidth: 2 },
      },
      {
        id: "e-mcp-weather",
        source: "mcp-gateway",
        target: "weather-node",
        animated: hasWeather,
        style: { stroke: "#3b82f6", strokeWidth: 1.5 },
      },
      {
        id: "e-mcp-script",
        source: "mcp-gateway",
        target: "script-node",
        animated: hasScript,
        style: { stroke: "#3b82f6", strokeWidth: 1.5 },
      },
      {
        id: "e-mcp-actor",
        source: "mcp-gateway",
        target: "actor-node",
        animated: hasActor,
        style: { stroke: "#10b981", strokeWidth: 2 },
      },
      {
        id: "e-actor-emma",
        source: "actor-node",
        target: "actor-emma",
        animated: hasActor,
        style: { stroke: "#10b981", strokeWidth: 1.5 },
      },
      {
        id: "e-emma-mgr",
        source: "actor-emma",
        target: "actor-manager",
        animated: hasActor,
        style: { stroke: "#06b6d4", strokeWidth: 2 },
      },
      {
        id: "e-mcp-equipment",
        source: "mcp-gateway",
        target: "equipment-node",
        animated: hasEquipment,
        style: { stroke: "#10b981", strokeWidth: 2 },
      },
      {
        id: "e-equipment-alexa",
        source: "equipment-node",
        target: "equipment-alexa",
        animated: hasEquipment,
        style: { stroke: "#10b981", strokeWidth: 1.5 },
      },
      {
        id: "e-alexa-vendor",
        source: "equipment-alexa",
        target: "equipment-vendor",
        animated: hasEquipment,
        style: { stroke: "#06b6d4", strokeWidth: 2 },
      },
      {
        id: "e-mcp-location",
        source: "mcp-gateway",
        target: "location-node",
        animated: hasLocation,
        style: { stroke: "#10b981", strokeWidth: 2 },
      },
      {
        id: "e-location-rooftop",
        source: "location-node",
        target: "location-rooftop",
        animated: hasLocation,
        style: { stroke: "#10b981", strokeWidth: 1.5 },
      },
      {
        id: "e-rooftop-owner",
        source: "location-rooftop",
        target: "location-owner",
        animated: hasLocation,
        style: { stroke: "#06b6d4", strokeWidth: 2 },
      },
    ];
  }, [events.length, agentStatuses]);

  return (
    <section
      aria-label="Resource Network Graph"
      className="rounded-lg border border-purple-500/30 bg-zinc-950 p-4 shadow-xl"
    >
      {/* Header */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-zinc-800 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-purple-400 ring-2 ring-purple-500/30 animate-pulse" />
          <h3 className="text-xs font-bold tracking-wider text-purple-300 uppercase">
            Production Resource Network
          </h3>
          <span className="rounded bg-purple-950/80 px-2 py-0.5 text-[10px] font-semibold text-purple-400 border border-purple-800/40">
            SPEC §9.4 Flagship View
          </span>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-[10px] text-zinc-400">
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-purple-400" />
            <span>Orchestrator</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-blue-400" />
            <span>MCP</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span>Agent</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-cyan-400" />
            <span>External</span>
          </div>
        </div>
      </div>

      {/* Propagation Path Caption */}
      <div className="mb-3 rounded bg-zinc-900/60 px-3 py-1.5 text-[11px] text-zinc-400 border border-zinc-800/80 flex items-center justify-between">
        <span>
          <strong className="text-zinc-200">Incident Propagation:</strong> Scene 42 → Weather Alert → Orchestrator → Domain Agents → External Contacts
        </span>
        <span className="text-[10px] text-purple-400 font-mono">
          {events.length} stream events synchronized
        </span>
      </div>

      {/* React Flow Container */}
      <div className="h-[460px] w-full rounded border border-zinc-900 bg-zinc-950/90">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-right"
          proOptions={{ hideAttribution: true }}
          minZoom={0.5}
          maxZoom={1.5}
        >
          <Background color="#27272a" gap={16} size={1} />
          <Controls className="bg-zinc-900 border-zinc-800 fill-zinc-300" />
        </ReactFlow>
      </div>
    </section>
  );
}
