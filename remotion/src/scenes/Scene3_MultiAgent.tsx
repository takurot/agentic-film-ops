import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { UIWrapper } from "../components/UIWrapper";

interface AgentCard {
  name: string;
  role: string;
  tool: string;
  status: "ACTIVE" | "COMPLETED" | "STANDBY";
  latency: string;
  log: string;
  icon: string;
}

export const Scene3_MultiAgent: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const agents: AgentCard[] = [
    {
      name: "Weather Agent",
      role: "Atmospheric Telemetry & Forecasts",
      tool: "weather_mcp.get_hourly_radar",
      status: frame > 60 ? "COMPLETED" : "ACTIVE",
      latency: "142ms",
      log: frame > 60 ? "Precipitation 92% confirmed at 16:30. Outdoor filming hazardous." : "Polling Doppler radar stations near Cliffside Vista...",
      icon: "🌤",
    },
    {
      name: "Script Agent",
      role: "Scene Breakdown & Character Mapping",
      tool: "script_mcp.get_scene_breakdown",
      status: frame > 180 ? "COMPLETED" : "ACTIVE",
      latency: "280ms",
      log: frame > 180 ? "Identified Scene 58 (Stage 2 Interior) shares exact cast (Marcus & Elena)." : "Extracting character presence & lighting specs for Day 12 scenes...",
      icon: "📜",
    },
    {
      name: "Location Agent",
      role: "Permits & Studio Stage Booking",
      tool: "location_mcp.check_stage_availability",
      status: frame > 240 ? "COMPLETED" : "ACTIVE",
      latency: "190ms",
      log: frame > 240 ? "Stage 2 Soundstage confirmed free from 15:00. Facility hold placed." : "Checking soundstage calendars and studio lot permits...",
      icon: "📍",
    },
    {
      name: "Actor Agent",
      role: "Talent Availability & Guild Rules",
      tool: "actor_mcp.query_talent_availability",
      status: frame > 300 ? "COMPLETED" : "ACTIVE",
      latency: "310ms",
      log: frame > 300 ? "SAG-AFTRA 12hr turnaround valid. Talent ready for Stage 2 call." : "Negotiating schedule adjustment with Vance Management...",
      icon: "🎭",
    },
    {
      name: "Equipment Agent",
      role: "Camera, Lighting & Grip Logistics",
      tool: "equipment_mcp.reallocate_lighting",
      status: frame > 360 ? "COMPLETED" : "ACTIVE",
      latency: "215ms",
      log: frame > 360 ? "CineRent Lighting Package B re-routed to Stage 2. Truck in transit." : "Querying rental inventory and staging truck locations...",
      icon: "🎥",
    },
    {
      name: "Budget Agent & Solver",
      role: "Cost Modeling & Constraint Solver",
      tool: "solver.generate_pareto_replans",
      status: frame > 400 ? "COMPLETED" : "ACTIVE",
      latency: "450ms",
      log: frame > 400 ? "Generated 3 validated replan candidates. Option A Pareto-optimal (Score 9.6)." : "Evaluating combinatorial cost deltas and wrap date constraints...",
      icon: "📊",
    },
  ];

  return (
    <UIWrapper
      title="Agent Live View — Parallel Multi-Agent Orchestration"
      badge="GEMINI 2.5 FLASH + MCP ORCHESTRATOR"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-5">
        {/* Top Coordinator Banner */}
        <div className="flex items-center justify-between rounded-xl border border-emerald-500/40 bg-gradient-to-r from-emerald-950/40 via-zinc-900/60 to-cyan-950/40 p-4 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <span className="flex h-3 w-3 relative">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
            </span>
            <span className="font-mono text-xs font-bold text-emerald-300 uppercase tracking-wide">
              Production Orchestrator: 6 Domain Agents Running in Parallel
            </span>
          </div>

          <div className="flex items-center gap-4 font-mono text-xs text-zinc-400">
            <span>TOTAL TOKENS: 14,280</span>
            <span className="text-zinc-600">•</span>
            <span>AVG LATENCY: 264ms</span>
            <span className="text-zinc-600">•</span>
            <span className="text-emerald-400 font-bold">ALL PROTOCOLS ONLINE</span>
          </div>
        </div>

        {/* 6 Agent Grid */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          {agents.map((agent, i) => {
            const cardSpring = spring({
              frame: frame - i * 15,
              fps,
              config: { damping: 12, mass: 0.7 },
            });

            return (
              <div
                key={agent.name}
                style={{ transform: `scale(${cardSpring})` }}
                className={`relative flex flex-col justify-between rounded-xl border p-5 backdrop-blur-md transition-all ${
                  agent.status === "COMPLETED"
                    ? "border-emerald-500/50 bg-emerald-950/20 shadow-md shadow-emerald-500/10"
                    : "border-cyan-500/40 bg-zinc-900/80 shadow-lg shadow-cyan-500/10"
                }`}
              >
                <div>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{agent.icon}</span>
                      <div>
                        <h4 className="text-sm font-bold text-white uppercase">{agent.name}</h4>
                        <p className="text-[11px] text-zinc-400">{agent.role}</p>
                      </div>
                    </div>
                    <span
                      className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase ${
                        agent.status === "COMPLETED"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 animate-pulse"
                      }`}
                    >
                      {agent.status}
                    </span>
                  </div>

                  {/* Tool info */}
                  <div className="mt-4 rounded-lg bg-zinc-950/80 p-2.5 border border-zinc-800">
                    <p className="font-mono text-[10px] text-zinc-500">MCP TOOL CALL</p>
                    <p className="font-mono text-xs text-cyan-300 truncate">{agent.tool}</p>
                  </div>

                  {/* Activity Log */}
                  <p className="mt-3 text-xs text-zinc-300 leading-relaxed font-sans min-h-[38px]">
                    {agent.log}
                  </p>
                </div>

                <div className="mt-4 flex items-center justify-between border-t border-zinc-800/80 pt-3 font-mono text-[10px] text-zinc-500">
                  <span>Latency: {agent.latency}</span>
                  <span className="text-emerald-400">Validated ✓</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </UIWrapper>
  );
};
