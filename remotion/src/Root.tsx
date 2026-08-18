import React from "react";
import { Composition } from "remotion";
import { PromoVideo } from "./PromoVideo";
import { Scene1_Logo } from "./scenes/Scene1_Logo";
import { Scene2_Dashboard } from "./scenes/Scene2_Dashboard";
import { Scene3_MultiAgent } from "./scenes/Scene3_MultiAgent";
import { Scene4_NetworkMcp } from "./scenes/Scene4_NetworkMcp";
import { Scene5_ManagerComms } from "./scenes/Scene5_ManagerComms";
import { Scene6_ReplanningOptions } from "./scenes/Scene6_ReplanningOptions";
import { Scene7_ApprovalExecution } from "./scenes/Scene7_ApprovalExecution";
import { Scene8_ResolvedSummary } from "./scenes/Scene8_ResolvedSummary";
import "./styles/globals.css";

export const Root: React.FC = () => {
  return (
    <>
      {/* Master 90-second Promo Video (Full Cut) */}
      <Composition
        id="PromoVideo"
        component={PromoVideo}
        durationInFrames={2700}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          enableAudio: true,
        }}
      />

      {/* Individual Scene Compositions for preview/testing */}
      <Composition
        id="Scene1-Logo"
        component={Scene1_Logo}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Scene2-Dashboard"
        component={Scene2_Dashboard}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Scene3-MultiAgent"
        component={Scene3_MultiAgent}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Scene4-NetworkMcp"
        component={Scene4_NetworkMcp}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Scene5-ManagerComms"
        component={Scene5_ManagerComms}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Scene6-ReplanningOptions"
        component={Scene6_ReplanningOptions}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Scene7-ApprovalExecution"
        component={Scene7_ApprovalExecution}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="Scene8-ResolvedSummary"
        component={Scene8_ResolvedSummary}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
