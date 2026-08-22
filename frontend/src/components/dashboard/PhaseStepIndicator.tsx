"use client";

export type ResolutionPhase = "ALERT" | "ANALYZING" | "OPTIONS" | "RESOLVED";

export interface PhaseStepIndicatorProps {
  currentPhase: ResolutionPhase;
  onSelectPhase?: (phase: ResolutionPhase) => void;
}

interface StepItem {
  id: ResolutionPhase;
  number: number;
  label: string;
  subLabel: string;
  targetId: string;
}

const STEPS: StepItem[] = [
  {
    id: "ALERT",
    number: 1,
    label: "Alert Detection",
    subLabel: "Scene 42 Weather",
    targetId: "incident-section",
  },
  {
    id: "ANALYZING",
    number: 2,
    label: "Agent Coordination",
    subLabel: "6 Domain Agents & MCP",
    targetId: "agent-orchestration-section",
  },
  {
    id: "OPTIONS",
    number: 3,
    label: "Option Evaluation",
    subLabel: "Pareto Replans (A/B/C)",
    targetId: "option-comparison-section",
  },
  {
    id: "RESOLVED",
    number: 4,
    label: "Execution & Resolved",
    subLabel: "Closed-loop Summary",
    targetId: "execution-summary-section",
  },
];

export function PhaseStepIndicator({
  currentPhase,
  onSelectPhase,
}: PhaseStepIndicatorProps) {
  const phaseOrder: Record<ResolutionPhase, number> = {
    ALERT: 1,
    ANALYZING: 2,
    OPTIONS: 3,
    RESOLVED: 4,
  };

  const currentOrder = phaseOrder[currentPhase];

  function handleClick(step: StepItem) {
    if (onSelectPhase) {
      onSelectPhase(step.id);
    }
    const targetElement = document.getElementById(step.targetId);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <nav
      aria-label="Incident Resolution Workflow"
      className="sticky top-2 z-30 mb-2 w-full rounded-xl border border-zinc-800/80 bg-zinc-950/90 p-2 shadow-xl backdrop-blur-md"
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {STEPS.map((step) => {
          const isCompleted = step.number < currentOrder;
          const isActive = step.number === currentOrder;
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => handleClick(step)}
              aria-current={isActive ? "step" : undefined}
              className={`group flex items-center gap-2.5 rounded-lg border px-3 py-2 text-left transition-all duration-200 ${
                isActive
                  ? "border-amber-500/60 bg-amber-950/30 text-amber-200 shadow-md shadow-amber-500/10 ring-1 ring-amber-400/40"
                  : isCompleted
                  ? "border-emerald-500/40 bg-emerald-950/20 text-emerald-200 hover:bg-emerald-950/30"
                  : "border-zinc-800/80 bg-zinc-900/40 text-zinc-500 hover:bg-zinc-800/40 hover:text-zinc-300"
              }`}
            >
              {/* Badge Icon / Number */}
              <div
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold transition-transform group-hover:scale-105 ${
                  isActive
                    ? "bg-amber-400 text-zinc-950 shadow-sm"
                    : isCompleted
                    ? "bg-emerald-500 text-zinc-950 font-black"
                    : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                }`}
              >
                {isCompleted ? "✓" : step.number}
              </div>

              {/* Step Labels */}
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-bold leading-tight">
                  {step.label}
                </div>
                <div
                  className={`truncate text-[10px] leading-tight ${
                    isActive
                      ? "text-amber-300/80"
                      : isCompleted
                      ? "text-emerald-300/80"
                      : "text-zinc-500"
                  }`}
                >
                  {step.subLabel}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
