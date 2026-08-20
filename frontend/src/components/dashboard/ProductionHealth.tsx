"use client";

/**
 * ProductionHealth – four metric cards: Schedule, Budget, Scenes, Risk (SPEC §9.1).
 * Responsive 2x2 grid on mobile (< 640px) and 4-column layout on desktop.
 */

function formatBudget(usd: number): string {
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(1)}M`;
  if (usd >= 1_000) return `$${(usd / 1_000).toFixed(0)}K`;
  return `$${usd.toFixed(0)}`;
}

const riskColor: Record<string, string> = {
  LOW: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
  MEDIUM: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
  HIGH: "bg-red-500/20 text-red-400 border border-red-500/30",
  CRITICAL: "bg-red-600/30 text-red-300 border border-red-600/40",
};

interface Props {
  schedulePercent: number;
  budgetSpent: number;
  budgetTotal: number;
  scenesCompleted: number;
  scenesTotal: number;
  risk: string;
}

function Card({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-white/10 bg-zinc-900/90 px-4 py-3.5 sm:px-5 sm:py-4 shadow-lg backdrop-blur-sm transition-all hover:border-zinc-700">
      <span className="text-[11px] font-bold tracking-wider text-zinc-400 uppercase">
        {label}
      </span>
      <div className="text-lg sm:text-xl font-bold text-white">{children}</div>
    </div>
  );
}

export function ProductionHealth({
  schedulePercent,
  budgetSpent,
  budgetTotal,
  scenesCompleted,
  scenesTotal,
  risk,
}: Props) {
  return (
    <section
      aria-label="Production Health"
      className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4"
    >
      <Card label="Schedule">
        {schedulePercent}%
        <span className="ml-1 text-xs font-normal text-zinc-400">adherence</span>
      </Card>
      <Card label="Budget">
        {formatBudget(budgetSpent)}
        <span className="ml-1 text-xs font-normal text-zinc-400">
          / {formatBudget(budgetTotal)}
        </span>
      </Card>
      <Card label="Scenes">
        {scenesCompleted}
        <span className="ml-1 text-xs font-normal text-zinc-400">/ {scenesTotal}</span>
      </Card>
      <Card label="Risk">
        <span
          className={`inline-block rounded px-2.5 py-0.5 text-xs font-bold uppercase ${
            riskColor[risk] ?? riskColor.MEDIUM
          }`}
        >
          {risk}
        </span>
      </Card>
    </section>
  );
}
