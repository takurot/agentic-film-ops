"use client";

import { useEffect, useState } from "react";
import {
  Header,
  ProductionHealth,
  ActiveIncidentCard,
  TodayProgress,
} from "@/components/dashboard";
import {
  fetchProductionHealth,
  fetchActiveIncidents,
  type ProductionHealth as HealthData,
  type ActiveIncident,
} from "@/lib/api";

export default function Home() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [incidents, setIncidents] = useState<ActiveIncident[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [h, inc] = await Promise.all([
          fetchProductionHealth(),
          fetchActiveIncidents(),
        ]);
        if (!cancelled) {
          setHealth(h);
          setIncidents(inc);
        }
      } catch (err) {
        if (!cancelled) setError(String(err));
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 p-8 text-red-400">
        <p>Failed to load dashboard: {error}</p>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 p-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-emerald-400" />
        <p className="mt-3 text-xs text-zinc-500">Loading production data…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-zinc-950 font-sans">
      <Header
        dayCurrent={health.production_day_current}
        dayTotal={health.production_day_total}
      />

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-6">
        <ProductionHealth
          schedulePercent={health.schedule_adherence_percent}
          budgetSpent={health.budget_spent_usd}
          budgetTotal={health.budget_total_usd}
          scenesCompleted={health.scenes_completed}
          scenesTotal={health.scenes_total}
          risk={health.overall_risk}
        />

        {incidents.map((inc) => (
          <ActiveIncidentCard key={inc.incident_id} incident={inc} />
        ))}

        <TodayProgress scenes={health.today_scenes} />
      </main>

      <footer className="border-t border-white/5 py-4 text-center text-[10px] text-zinc-600">
        Agentic FilmOps — Powered by AI Agents
      </footer>
    </div>
  );
}
