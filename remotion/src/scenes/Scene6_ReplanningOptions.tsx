import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { UIWrapper } from "../components/UIWrapper";
import { mockAnalysis } from "../data/demoScenario";

export const Scene6_ReplanningOptions: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const options = mockAnalysis.options;

  return (
    <UIWrapper
      title="Constraint Solver — Explainable Replan Evaluation"
      badge="PARETO MULTI-OBJECTIVE OPTIMIZATION"
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-5">
        {/* Header Indicator */}
        <div className="flex items-center justify-between border-b border-zinc-800 pb-2 font-mono text-xs">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="font-bold text-zinc-200">SOLVER SYNTHESIS COMPLETE: 3 CANDIDATE REPLANS</span>
          </div>
          <span className="text-zinc-400">Optimization Goal: Min(Cost, Wrap Drift, Safety Risk)</span>
        </div>

        {/* 3 Option Cards */}
        <div className="grid grid-cols-3 gap-5">
          {options.map((opt, i) => {
            const cardScale = spring({
              frame: frame - i * 15,
              fps,
              config: { damping: 12, mass: 0.8 },
            });

            return (
              <div
                key={opt.option_id}
                style={{ transform: `scale(${cardScale})` }}
                className={`relative flex flex-col justify-between rounded-xl border p-5 backdrop-blur-md transition-all ${
                  opt.recommended
                    ? "border-emerald-500 bg-gradient-to-b from-emerald-950/40 via-zinc-900/90 to-emerald-950/30 shadow-2xl shadow-emerald-500/20 ring-1 ring-emerald-500/40"
                    : "border-zinc-800 bg-zinc-900/70"
                }`}
              >
                {opt.recommended && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-emerald-500 px-3 py-0.5 font-mono text-[10px] font-black text-black tracking-wider uppercase shadow-md">
                    ★ RECOMMENDED BY GEMINI SOLVER
                  </div>
                )}

                <div>
                  <div className="flex items-start justify-between">
                    <h3 className="text-sm font-bold text-white leading-snug">{opt.name}</h3>
                    <span
                      className={`font-mono text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        opt.risk_level === "LOW"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : opt.risk_level === "MEDIUM"
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {opt.risk_level} RISK
                    </span>
                  </div>

                  {/* Key Metrics */}
                  <div className="mt-4 grid grid-cols-3 gap-2 rounded-lg bg-zinc-950/80 p-2.5 font-mono text-center border border-zinc-800">
                    <div>
                      <p className="text-[9px] text-zinc-500">COST DELTA</p>
                      <p
                        className={`text-xs font-bold ${
                          opt.recommended ? "text-emerald-400" : "text-zinc-200"
                        }`}
                      >
                        +${opt.cost_delta_usd.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-[9px] text-zinc-500">SCHEDULE</p>
                      <p
                        className={`text-xs font-bold ${
                          opt.schedule_delta_days === 0 ? "text-emerald-400" : "text-amber-400"
                        }`}
                      >
                        {opt.schedule_delta_days === 0 ? "0 Days (On Track)" : `+${opt.schedule_delta_days} Day`}
                      </p>
                    </div>
                    <div>
                      <p className="text-[9px] text-zinc-500">SET DELAY</p>
                      <p className="text-xs font-bold text-cyan-400">+{opt.delay_hours}h</p>
                    </div>
                  </div>

                  <p className="mt-3 text-xs text-zinc-300 leading-relaxed font-sans">
                    {opt.summary}
                  </p>

                  {/* Pros / Cons bullets */}
                  <div className="mt-3 space-y-1 text-[11px]">
                    {opt.pros.map((p, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-emerald-300">
                        <span>✓</span>
                        <span className="truncate">{p}</span>
                      </div>
                    ))}
                    {opt.cons.map((c, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-zinc-400">
                        <span>⚠</span>
                        <span className="truncate">{c}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-4 border-t border-zinc-800/80 pt-3 flex items-center justify-between font-mono text-[10px]">
                  <span className="text-zinc-500">Confidence: {(opt.confidence * 100).toFixed(0)}%</span>
                  {opt.explainability && (
                    <span className="text-emerald-400 font-bold">
                      Tradeoff Score: {opt.explainability.tradeoff_score}/10
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Explainability Banner */}
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-bold text-emerald-400 uppercase">
              💡 Explainability Rationale:
            </span>
            <p className="text-xs text-zinc-200">
              {mockAnalysis.options[0].explainability?.rationale}
            </p>
          </div>
        </div>
      </div>
    </UIWrapper>
  );
};
