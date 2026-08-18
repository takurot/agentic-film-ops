import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { subtitleTracks } from "../data/demoScenario";

export const Subtitles: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const currentTrack = subtitleTracks.find(
    (t) => frame >= t.startFrame && frame < t.endFrame
  );

  if (!currentTrack) return null;

  const localFrame = frame - currentTrack.startFrame;
  const duration = currentTrack.endFrame - currentTrack.startFrame;

  const opacity = interpolate(
    localFrame,
    [0, 10, duration - 10, duration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const translateY = interpolate(
    localFrame,
    [0, 12],
    [15, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
      className="pointer-events-none absolute bottom-8 left-1/2 -translate-x-1/2 z-50 flex max-w-5xl items-center gap-4 rounded-xl border border-zinc-700/80 bg-zinc-950/85 px-6 py-3 shadow-2xl backdrop-blur-xl"
    >
      <div className="flex items-center gap-2 border-r border-zinc-800 pr-4">
        <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="font-mono text-xs font-bold tracking-wider text-emerald-400 uppercase">
          {currentTrack.speaker}
        </span>
      </div>
      <p className="text-base font-medium text-zinc-100 drop-shadow-md">
        {currentTrack.text}
      </p>
    </div>
  );
};
