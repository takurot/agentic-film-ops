"use client";

/**
 * ProductionHealth – four metric cards: Schedule, Budget, Scenes, Risk (SPEC §9.1).
 */

function formatBudget(usd: number): string {
  if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(1)}M`;
  if (usd >= 1_000) return `$${(usd / 1_000).toFixed(0)}K`;
  return `$${usd.toFixed(0)}`;
}

const riskColor: Record<string, string> = {
  LOW: "bg-emerald-500/20 text-emerald-400",
  MEDIUM: "bg-amber-500/20 text-amber-400",
  HIGH: "bg-red-500/20 text-red-400",
  CRITICAL: "bg-red-600/30 text-red-300",
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
    <div className="flex flex-col gap-1 rounded-lg border border-white/5 bg-zinc-900/80 px-5 py-4">
      <span className="text-[11px] font-medium tracking-wider text-zinc-500 uppercase">
        {label}
      </span>
      <div className="text-xl font-semibold text-white">{children}</div>
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
    <section aria-label="Production Health" className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Card label="Schedule">
        {schedulePercent}%
        <span className="ml-1 text-xs font-normal text-zinc-500">adherence</span>
      </Card>
      <Card label="Budget">
        {formatBudget(budgetSpent)}
        <span className="ml-1 text-xs font-normal text-zinc-500">
          / {formatBudget(budgetTotal)}
        </span>
      </Card>
      <Card label="Scenes">
        {scenesCompleted}
        <span className="ml-1 text-xs font-normal text-zinc-500">/ {scenesTotal}</span>
      </Card>
      <Card label="Risk">
        <span
          className={`inline-block rounded px-2 py-0.5 text-xs font-bold uppercase ${riskColor[risk] ?? riskColor.MEDIUM}`}
        >
          {risk}
        </span>
      </Card>
    </section>
  );
}
