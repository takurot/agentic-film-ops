import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { UIWrapper } from "../components/UIWrapper";
import { initialHealth, activeIncident } from "../data/demoScenario";

export const Scene2_Dashboard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const isAlertActive = frame > 80;
  const isAnalysisStarting = frame > 200;

  const alertScale = isAlertActive
    ? spring({
        frame: frame - 80,
        fps,
        config: { damping: 10, mass: 0.6 },
      })
    : 1;

  const buttonPulse = interpolate(frame, [200, 240, 280], [1, 1.05, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <UIWrapper>
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        {/* Production Health Top Metrics */}
        <div className="grid grid-cols-4 gap-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 backdrop-blur-md">
            <p className="font-mono text-xs text-zinc-400">SCHEDULE ADHERENCE</p>
            <p className="mt-2 font-mono text-3xl font-extrabold text-emerald-400">
              {initialHealth.schedule_adherence_percent}%
            </p>
            <p className="mt-1 text-xs text-zinc-500">Day 12 of 30 • On Schedule</p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 backdrop-blur-md">
            <p className="font-mono text-xs text-zinc-400">BUDGET TRACKING</p>
            <p className="mt-2 font-mono text-3xl font-extrabold text-zinc-100">
              ${(initialHealth.budget_spent_usd / 1000).toFixed(0)}k
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              of ${(initialHealth.budget_total_usd / 1000).toFixed(0)}k Allocated
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 backdrop-blur-md">
            <p className="font-mono text-xs text-zinc-400">SCENES PROGRESS</p>
            <p className="mt-2 font-mono text-3xl font-extrabold text-cyan-400">
              {initialHealth.scenes_completed} / {initialHealth.scenes_total}
            </p>
            <p className="mt-1 text-xs text-zinc-500">3 Scenes Scheduled Today</p>
          </div>

          <div
            className={`rounded-xl border p-5 backdrop-blur-md transition-colors ${
              isAlertActive
                ? "border-red-500/80 bg-red-950/40 shadow-lg shadow-red-500/20"
                : "border-zinc-800 bg-zinc-900/70"
            }`}
          >
            <p className="font-mono text-xs text-zinc-400">OVERALL RISK</p>
            <p
              className={`mt-2 font-mono text-3xl font-extrabold ${
                isAlertActive ? "text-red-400 animate-pulse" : "text-emerald-400"
              }`}
            >
              {isAlertActive ? "HIGH RISK" : "NOMINAL"}
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              {isAlertActive ? "Incident Detected" : "Zero Critical Blockers"}
            </p>
          </div>
        </div>

        {/* Active Incident Alert Card */}
        {isAlertActive && (
          <div
            style={{ transform: `scale(${alertScale})` }}
            className="relative overflow-hidden rounded-xl border-2 border-red-500/70 bg-gradient-to-r from-red-950/60 via-zinc-900/80 to-red-950/60 p-6 shadow-2xl backdrop-blur-xl"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-600/30 border border-red-500 text-2xl">
                  ⛈
                </div>
                <div>
                  <div className="flex items-center gap-3">
                    <span className="rounded bg-red-500/20 border border-red-500/50 px-2.5 py-0.5 font-mono text-xs font-bold text-red-400 uppercase">
                      CRITICAL WEATHER ALERT
                    </span>
                    <span className="font-mono text-xs text-zinc-400">
                      ID: {activeIncident.incident_id}
                    </span>
                  </div>
                  <h3 className="mt-2 text-xl font-bold text-white">
                    Heavy Thunderstorm Detected at Cliffside Vista (Scene 42)
                  </h3>
                  <p className="mt-1 text-sm text-zinc-300">
                    {activeIncident.detail}
                  </p>
                </div>
              </div>

              <div className="flex flex-col items-end gap-2">
                <span className="flex items-center gap-2 font-mono text-xs text-red-400">
                  <span className="h-2.5 w-2.5 rounded-full bg-red-500 animate-ping" />
                  IMPACT: +4.5h DELAY / +$84k
                </span>
              </div>
            </div>

            {/* Action CTA */}
            <div className="mt-6 flex items-center justify-between border-t border-red-500/20 pt-4">
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <span>Domain Agents on Standby:</span>
                <span className="font-mono text-zinc-200 font-bold">
                  Weather • Script • Location • Actor • Equipment • Budget • Solver
                </span>
              </div>

              <button
                style={{ transform: `scale(${buttonPulse})` }}
                className="cursor-pointer flex items-center gap-2 rounded-lg bg-red-600 px-6 py-2.5 font-mono text-xs font-bold tracking-wider text-white uppercase shadow-lg shadow-red-600/30"
              >
                <span>⚡</span>
                <span>{isAnalysisStarting ? "INITIALIZING AI RECOVERY ORCHESTRATION…" : "TRIGGER AI IMPACT ANALYSIS"}</span>
              </button>
            </div>
          </div>
        )}

        {/* Today's Schedule Overview */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5">
          <div className="flex items-center justify-between">
            <h4 className="font-mono text-xs font-bold tracking-wider text-zinc-400 uppercase">
              DAY 12 SHOOTING SLATE
            </h4>
            <span className="font-mono text-xs text-zinc-500">Call Time: 06:30 PST</span>
          </div>
          <div className="mt-4 space-y-2">
            {initialHealth.today_scenes?.map((s) => (
              <div
                key={s.scene_id}
                className={`flex items-center justify-between rounded-lg border p-3 font-mono text-xs ${
                  s.scene_id === "42" && isAlertActive
                    ? "border-red-500/60 bg-red-950/30 text-red-300"
                    : s.status === "COMPLETED"
                    ? "border-zinc-800 bg-zinc-900/40 text-zinc-400"
                    : "border-zinc-800 bg-zinc-900/60 text-zinc-200"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="font-bold">SCENE {s.scene_id}</span>
                  <span className="text-zinc-300">{s.name}</span>
                </div>
                <span
                  className={`rounded px-2 py-0.5 font-bold uppercase ${
                    s.scene_id === "42" && isAlertActive
                      ? "bg-red-500/20 text-red-400"
                      : s.status === "COMPLETED"
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-zinc-800 text-zinc-400"
                  }`}
                >
                  {s.scene_id === "42" && isAlertActive ? "THREATENED" : s.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </UIWrapper>
  );
};
