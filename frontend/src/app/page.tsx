"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Header, ProductionHealth, ActiveIncidentCard, TodayProgress } from "@/components/dashboard";
import { createLiveApiClient, isVerifiedLiveRuntime, type ActiveIncident, type LiveApiClient, type ProductionHealth as HealthData } from "@/lib/api";
import { getPublicRuntimeConfig } from "@/lib/runtimeConfig";
import { MOCK_HEALTH, MOCK_INCIDENTS } from "@/lib/mockData";
import { DemoTimeline } from "@/components/demo";
import { VideoModal } from "@/components/video";

type DashboardState =
  | { kind: "REPLAY_READY"; health: HealthData; incidents: ActiveIncident[] }
  | { kind: "LOADING_LIVE" }
  | { kind: "LIVE_READY"; health: HealthData; incidents: ActiveIncident[] }
  | { kind: "LIVE_ERROR"; code: "BACKEND_UNAVAILABLE" | "RUNTIME_MISMATCH" };

const runtimeConfig = getPublicRuntimeConfig();

export default function Home() {
  const client = useMemo<LiveApiClient | null>(() =>
    runtimeConfig.mode === "LIVE_GEMINI" ? createLiveApiClient(runtimeConfig) : null, []);
  const [state, setState] = useState<DashboardState>(() => runtimeConfig.mode === "RECORDED_REPLAY"
    ? { kind: "REPLAY_READY", health: MOCK_HEALTH, incidents: MOCK_INCIDENTS }
    : { kind: "LOADING_LIVE" });
  const [showTimeline, setShowTimeline] = useState(true);
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const requestGeneration = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const mounted = useRef(true);

  const loadLive = useCallback(async () => {
    if (!client) return;
    const generation = ++requestGeneration.current;
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const timeout = setTimeout(() => controller.abort(), 8_000);
    try {
      const runtime = await client.fetchRuntimeInfo(controller.signal);
      if (!isVerifiedLiveRuntime(runtime)) {
        if (generation === requestGeneration.current) setState({ kind: "LIVE_ERROR", code: "RUNTIME_MISMATCH" });
        return;
      }
      const [health, incidents] = await Promise.all([
        client.fetchProductionHealth(controller.signal),
        client.fetchActiveIncidents(controller.signal),
      ]);
      if (generation !== requestGeneration.current) return;
      setState({ kind: "LIVE_READY", health, incidents });
    } catch {
      controller.abort();
      if (generation === requestGeneration.current) {
        setState({ kind: "LIVE_ERROR", code: "BACKEND_UNAVAILABLE" });
      }
    } finally {
      clearTimeout(timeout);
      if (generation === requestGeneration.current) activeRequest.current = null;
    }
  }, [client]);

  const retryLive = useCallback(() => {
    setState({ kind: "LOADING_LIVE" });
    void loadLive();
  }, [loadLive]);

  useEffect(() => {
    mounted.current = true;
    const timer = runtimeConfig.mode === "LIVE_GEMINI"
      ? setTimeout(() => void loadLive(), 0)
      : null;
    return () => {
      if (timer) clearTimeout(timer);
      mounted.current = false;
      requestGeneration.current += 1;
      activeRequest.current?.abort();
    };
  }, [loadLive]);

  async function handleReset() {
    setResetting(true);
    if (runtimeConfig.mode === "RECORDED_REPLAY") {
      window.location.reload();
      return;
    }
    try {
      const controller = new AbortController();
      activeRequest.current = controller;
      await client?.resetDemoState(controller.signal);
      if (!mounted.current) return;
      await loadLive();
    } catch {
      if (mounted.current) setState({ kind: "LIVE_ERROR", code: "BACKEND_UNAVAILABLE" });
    } finally {
      if (mounted.current) setResetting(false);
    }
  }

  if (state.kind === "LOADING_LIVE") {
    return <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 p-8" role="status">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-400" />
      <p className="mt-3 text-xs text-zinc-400">LIVE MODE — VERIFYING</p>
    </div>;
  }
  if (state.kind === "LIVE_ERROR") {
    return <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 p-8 text-center">
      <p className="text-sm font-bold text-red-300" role="alert">{state.code}</p>
      <p className="mt-2 max-w-md text-xs text-zinc-400">Live backend verification failed. No sample results were substituted.</p>
      <button onClick={retryLive} className="mt-5 rounded bg-red-600 px-5 py-2 text-xs font-bold text-white">Retry</button>
    </main>;
  }

  const { health, incidents } = state;
  const replay = state.kind === "REPLAY_READY";
  return <div className="flex min-h-screen flex-col bg-zinc-950 font-sans">
    <Header dayCurrent={health.production_day_current} dayTotal={health.production_day_total}
      onToggleTimeline={() => setShowTimeline((value) => !value)} onReset={handleReset}
      resetting={resetting} showTimeline={showTimeline}
      runtimeLabel={replay ? "RECORDED REPLAY / SAMPLE DATA" : "LIVE GEMINI + MCP STDIO"} />
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 p-6">
      {replay && <div data-testid="runtime-mode-banner" role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-amber-950/20 px-4 py-3 text-xs text-amber-200">
        <strong>RECORDED REPLAY / SAMPLE DATA — NO LIVE API CALLS</strong>
        <button type="button" onClick={() => setIsVideoModalOpen(true)} className="rounded-lg border border-amber-500/40 px-3 py-1 font-bold">🎬 Watch Promo Video (90s)</button>
      </div>}
      <ProductionHealth schedulePercent={health.schedule_adherence_percent} budgetSpent={health.budget_spent_usd}
        budgetTotal={health.budget_total_usd} scenesCompleted={health.scenes_completed} scenesTotal={health.scenes_total} risk={health.overall_risk} />
      {incidents.map((incident) => replay
        ? <ActiveIncidentCard key={incident.incident_id} incident={incident} runtimeMode="RECORDED_REPLAY" client={null} />
        : <ActiveIncidentCard key={incident.incident_id} incident={incident} runtimeMode="LIVE_GEMINI" client={client!} />)}
      <TodayProgress scenes={health.today_scenes} />
    </main>
    <footer className="border-t border-white/5 py-4 text-center text-[10px] text-zinc-500">
      {replay ? "Agentic FilmOps — Scenario Replay / Sample Data illustrating the Gemini + MCP workflow" : "Agentic FilmOps — Powered by Gemini + MCP"}
    </footer>
    <DemoTimeline visible={showTimeline} onClose={() => setShowTimeline(false)} replay={replay} />
    <VideoModal isOpen={isVideoModalOpen} onClose={() => setIsVideoModalOpen(false)} />
  </div>;
}
