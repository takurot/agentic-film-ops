import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const Scene1_Logo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({
    frame,
    fps,
    config: { damping: 12, mass: 0.8 },
  });

  const badgeOpacity = interpolate(frame, [25, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const taglineOpacity = interpolate(frame, [40, 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const gridOffset = interpolate(frame, [0, 150], [0, 60]);

  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center bg-zinc-950 text-white overflow-hidden">
      {/* Background Animated Matrix Grid */}
      <div
        className="pointer-events-none absolute inset-0 opacity-20"
        style={{
          backgroundImage: `linear-gradient(to right, #27272a 1px, transparent 1px), linear-gradient(to bottom, #27272a 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
          backgroundPosition: `0px ${gridOffset}px`,
        }}
      />

      {/* Radiant Aura */}
      <div className="pointer-events-none absolute h-[500px] w-[700px] rounded-full bg-gradient-to-tr from-emerald-500/20 via-cyan-500/20 to-indigo-500/10 blur-3xl animate-pulse" />

      {/* Main Logo & Typography */}
      <div
        style={{ transform: `scale(${titleScale})` }}
        className="relative z-10 flex flex-col items-center text-center px-8"
      >
        <div className="mb-6 flex h-24 w-24 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 via-teal-500 to-cyan-600 p-0.5 shadow-2xl shadow-emerald-500/30">
          <div className="flex h-full w-full items-center justify-center rounded-2xl bg-zinc-950/90">
            <span className="font-mono text-5xl">🎬</span>
          </div>
        </div>

        <h1 className="bg-gradient-to-r from-emerald-300 via-teal-100 to-cyan-300 bg-clip-text text-6xl font-black tracking-tight text-transparent uppercase drop-shadow-lg">
          AGENTIC FILM OPS
        </h1>

        <div
          style={{ opacity: taglineOpacity }}
          className="mt-4 text-2xl font-semibold text-zinc-300 tracking-wide"
        >
          Autonomous Production Disruption Recovery
        </div>

        <div
          style={{ opacity: badgeOpacity }}
          className="mt-8 flex items-center gap-3 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-6 py-2 shadow-inner"
        >
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
          <span className="font-mono text-xs font-bold text-emerald-300 tracking-widest uppercase">
            Gemini 2.5 • Google ADK • Model Context Protocol (MCP)
          </span>
        </div>
      </div>
    </div>
  );
};
