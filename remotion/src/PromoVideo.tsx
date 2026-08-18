import React from "react";
import { Sequence, AbsoluteFill } from "remotion";
import { Scene1_Logo } from "./scenes/Scene1_Logo";
import { Scene2_Dashboard } from "./scenes/Scene2_Dashboard";
import { Scene3_MultiAgent } from "./scenes/Scene3_MultiAgent";
import { Scene4_NetworkMcp } from "./scenes/Scene4_NetworkMcp";
import { Scene5_ManagerComms } from "./scenes/Scene5_ManagerComms";
import { Scene6_ReplanningOptions } from "./scenes/Scene6_ReplanningOptions";
import { Scene7_ApprovalExecution } from "./scenes/Scene7_ApprovalExecution";
import { Scene8_ResolvedSummary } from "./scenes/Scene8_ResolvedSummary";
import { Subtitles } from "./components/Subtitles";
import { AudioTrack } from "./components/AudioTrack";

export interface PromoVideoProps {
  enableAudio?: boolean;
}

export const PromoVideo: React.FC<PromoVideoProps> = ({ enableAudio = true }) => {
  return (
    <AbsoluteFill className="bg-zinc-950">
      {/* Scene 1: Logo & Concept Hook (0:00 - 0:05 / 150 frames) */}
      <Sequence from={0} durationInFrames={150} name="Scene 1: Logo">
        <Scene1_Logo />
      </Sequence>

      {/* Scene 2: Production Dashboard & Weather Alert (0:05 - 0:15 / 300 frames) */}
      <Sequence from={150} durationInFrames={300} name="Scene 2: Dashboard & Alert">
        <Scene2_Dashboard />
      </Sequence>

      {/* Scene 3: Multi-Agent Parallel Orchestration (0:15 - 0:30 / 450 frames) */}
      <Sequence from={450} durationInFrames={450} name="Scene 3: Multi-Agent Live View">
        <Scene3_MultiAgent />
      </Sequence>

      {/* Scene 4: MCP Activity & Resource Network Graph (0:30 - 0:45 / 450 frames) */}
      <Sequence from={900} durationInFrames={450} name="Scene 4: MCP & Resource Network">
        <Scene4_NetworkMcp />
      </Sequence>

      {/* Scene 5: External Communication Mock (0:45 - 0:55 / 300 frames) */}
      <Sequence from={1350} durationInFrames={300} name="Scene 5: Manager Negotiation">
        <Scene5_ManagerComms />
      </Sequence>

      {/* Scene 6: Replanning & Option Comparison (0:55 - 1:10 / 450 frames) */}
      <Sequence from={1650} durationInFrames={450} name="Scene 6: Replan Options">
        <Scene6_ReplanningOptions />
      </Sequence>

      {/* Scene 7: Producer Approval & Autonomous Execution (1:10 - 1:20 / 300 frames) */}
      <Sequence from={2100} durationInFrames={300} name="Scene 7: Approval & Execution">
        <Scene7_ApprovalExecution />
      </Sequence>

      {/* Scene 8: Incident Resolved Summary & Outro (1:20 - 1:30 / 300 frames) */}
      <Sequence from={2400} durationInFrames={300} name="Scene 8: Summary & Outro">
        <Scene8_ResolvedSummary />
      </Sequence>

      {/* Synchronized Subtitle Overlay (0:00 - 1:30 / 2700 frames) */}
      <Subtitles />

      {/* Audio Composition (BGM + Sound Design) */}
      <AudioTrack enableAudio={enableAudio} />
    </AbsoluteFill>
  );
};
