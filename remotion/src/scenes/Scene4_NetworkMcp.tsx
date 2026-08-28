import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { UIWrapper } from "../components/UIWrapper";
import { mockEvents } from "../data/demoScenario";

export const Scene4_NetworkMcp: React.FC = () => {
  const frame = useCurrentFrame();


  const pulseOffset = interpolate(frame % 90, [0, 90], [0, 100]);

  // Network Nodes for deterministic video layout
  const nodes = [
    { id: "weather", label: "🌧 Heavy Rain Alert", sub: "Shibuya Rooftop", x: 100, y: 80, color: "border-red-500 bg-red-950/80 text-red-300" },
    { id: "scene42", label: "🎬 Scene 42 (Ext)", sub: "Shibuya Tower", x: 320, y: 80, color: "border-amber-500 bg-amber-950/80 text-amber-300" },
    { id: "studiob", label: "🏢 Studio B (Int)", sub: "Soundstage", x: 320, y: 260, color: "border-emerald-500 bg-emerald-950/80 text-emerald-300" },
    { id: "actor", label: "🎭 Emma & Daniel", sub: "Principal Cast", x: 100, y: 260, color: "border-cyan-500 bg-cyan-950/80 text-cyan-300" },
    { id: "equipment", label: "💡 ARRI Alexa & Kit", sub: "Cinema Rental", x: 540, y: 170, color: "border-indigo-500 bg-indigo-950/80 text-indigo-300" },
    { id: "schedule", label: "📅 Master Schedule", sub: "Day 27 Slate", x: 540, y: 340, color: "border-emerald-400 bg-emerald-950/80 text-emerald-200" },
  ];


  const visibleEventsCount = Math.min(
    mockEvents.length,
    Math.floor(interpolate(frame, [0, 400], [2, mockEvents.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }))
  );

  return (
    <UIWrapper
      title="Resource Network & MCP Activity Stream"
      badge="MODEL CONTEXT PROTOCOL (JSON-RPC 2.0)"
    >
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-6 lg:grid-cols-12 h-[520px]">
        {/* Left Column: Resource Network Visualizer (7 cols) */}
        <div className="relative col-span-7 flex flex-col rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 backdrop-blur-md overflow-hidden">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-emerald-400">🕸</span>
              <h3 className="font-mono text-xs font-bold text-zinc-200 uppercase">
                Resource Dependency Graph & Propagation
              </h3>
            </div>
            <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] text-emerald-400">
              CASCADING IMPACT DETECTED
            </span>
          </div>

          {/* Graph Canvas */}
          <div className="relative flex-1 mt-2">
            {/* SVG Connecting Lines & Pulse Animations */}
            <svg className="absolute inset-0 h-full w-full pointer-events-none">
              {/* Storm -> Scene 42 */}
              <line x1="180" y1="110" x2="320" y2="110" stroke="#ef4444" strokeWidth="2" strokeDasharray="4 4" />
              {/* Scene 42 -> Stage 2 */}
              <line x1="380" y1="140" x2="380" y2="260" stroke="#10b981" strokeWidth="2" />
              {/* Actor -> Stage 2 */}
              <line x1="180" y1="290" x2="320" y2="290" stroke="#06b6d4" strokeWidth="2" />
              {/* Stage 2 -> Lighting */}
              <line x1="420" y1="280" x2="540" y2="200" stroke="#6366f1" strokeWidth="2" />
              {/* Stage 2 -> Schedule */}
              <line x1="420" y1="310" x2="540" y2="360" stroke="#10b981" strokeWidth="3" />

              {/* Animated Propagation Wave Ring */}
              <circle
                cx={380}
                cy={260}
                r={20 + (pulseOffset * 0.8)}
                fill="none"
                stroke="#10b981"
                strokeWidth="1.5"
                opacity={1 - pulseOffset / 100}
              />
            </svg>

            {/* Nodes */}
            {nodes.map((node) => (
              <div
                key={node.id}
                style={{ left: `${node.x}px`, top: `${node.y}px` }}
                className={`absolute w-44 rounded-xl border p-3 shadow-xl backdrop-blur-md ${node.color}`}
              >
                <p className="font-bold text-xs">{node.label}</p>
                <p className="font-mono text-[10px] opacity-80">{node.sub}</p>
                <div className="mt-2 flex items-center justify-between font-mono text-[9px] opacity-70">
                  <span>STATUS: SYNCED</span>
                  <span>MCP-OK</span>
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-zinc-800 pt-3 flex items-center justify-between font-mono text-[10px] text-zinc-500">
            <span>6 Resource Nodes • 5 Active Propagation Edges</span>
            <span className="text-emerald-400">Zero Deadlock Detected ✓</span>
          </div>
        </div>

        {/* Right Column: MCP Activity Stream (5 cols) */}
        <div className="col-span-5 flex flex-col rounded-xl border border-zinc-800 bg-zinc-950/80 p-5 backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
              <h3 className="font-mono text-xs font-bold text-cyan-300 uppercase">
                MCP Tool Stream Terminal
              </h3>
            </div>
            <span className="font-mono text-[10px] text-zinc-500">JSON-RPC 2.0</span>
          </div>

          {/* Log Items */}
          <div className="mt-3 flex-1 space-y-2.5 overflow-hidden font-mono text-[11px]">
            {mockEvents.slice(0, visibleEventsCount).map((evt) => (
              <div
                key={evt.event_id}
                className="rounded-lg border border-zinc-800/80 bg-zinc-900/50 p-2.5"
              >
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-zinc-400">{evt.timestamp}</span>
                  <span className="rounded bg-cyan-500/10 px-1.5 py-0.2 text-cyan-400">
                    {evt.agent}
                  </span>
                </div>
                <p className="mt-1 font-bold text-zinc-200">{evt.tool}</p>
                <p className="mt-0.5 text-[10px] text-zinc-400 line-clamp-2 leading-tight">
                  {evt.detail}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-2 border-t border-zinc-800 pt-2 flex items-center justify-between font-mono text-[10px] text-zinc-500">
            <span>Transport: Stdio / SSE</span>
            <span className="text-cyan-400">8 Tool Calls Completed</span>
          </div>
        </div>
      </div>
    </UIWrapper>
  );
};
