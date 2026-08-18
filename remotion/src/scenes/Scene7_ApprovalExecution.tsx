import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import { UIWrapper } from "../components/UIWrapper";
import { mockExecution } from "../data/demoScenario";

export const Scene7_ApprovalExecution: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const isApproved = frame >= 50;

  const buttonGlow = interpolate(frame, [30, 50, 70], [1, 1.15, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const tasks = mockExecution.tasks;

  return (
    <UIWrapper
      title="Human-in-the-Loop Approval & Autonomous Execution"
      badge="STRICT PRODUCER OVERSIGHT (SPEC §9.9 / §9.10)"
    >
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        {/* Step 1: Producer Approval Gate Card */}
        <div className="flex items-center justify-between rounded-xl border border-emerald-500/40 bg-zinc-900/80 p-6 backdrop-blur-md">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-emerald-400 uppercase">
                HUMAN APPROVAL GATE
              </span>
              <span className="text-zinc-500">•</span>
              <span className="font-mono text-xs text-zinc-400">Target: Option A ($4,200 / +1.5h)</span>
            </div>
            <h3 className="mt-1 text-lg font-bold text-white">
              Authorize AI Autonomous Recovery Execution
            </h3>
            <p className="text-xs text-zinc-400">
              No production state is altered without explicit Producer confirmation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              style={{ transform: `scale(${buttonGlow})` }}
              className={`flex items-center gap-2 rounded-xl px-6 py-3 font-mono text-xs font-black tracking-wider uppercase shadow-xl transition-all ${
                isApproved
                  ? "bg-emerald-500 text-black ring-4 ring-emerald-500/30"
                  : "bg-emerald-600 text-white hover:bg-emerald-500"
              }`}
            >
              <span>{isApproved ? "✓ APPROVED BY PRODUCER" : "⚡ APPROVE OPTION A"}</span>
            </button>
          </div>
        </div>

        {/* Step 2: Automated Execution Checklist */}
        {isApproved && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-md">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping" />
                <h4 className="font-mono text-xs font-bold text-zinc-200 uppercase">
                  Multi-System Autonomous Execution Pipeline
                </h4>
              </div>
              <span className="font-mono text-xs text-emerald-400 font-bold">
                {frame > 220 ? "ALL TASKS COMPLETED (100%)" : "EXECUTING DISPATCH…"}
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {tasks.map((task, idx) => {
                const taskDone = frame >= 80 + idx * 40;
                const taskSpring = spring({
                  frame: frame - (80 + idx * 40),
                  fps,
                  config: { damping: 12 },
                });

                return (
                  <div
                    key={task.task_id}
                    style={{ transform: `scale(${taskDone ? taskSpring : 1})` }}
                    className={`flex items-center justify-between rounded-xl border p-4 font-mono text-xs transition-all ${
                      taskDone
                        ? "border-emerald-500/40 bg-emerald-950/20 text-zinc-100"
                        : "border-zinc-800 bg-zinc-950/40 text-zinc-500"
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className={`flex h-7 w-7 items-center justify-center rounded-lg font-bold ${
                          taskDone
                            ? "bg-emerald-500 text-black shadow-md shadow-emerald-500/30"
                            : "bg-zinc-800 text-zinc-500"
                        }`}
                      >
                        {taskDone ? "✓" : idx + 1}
                      </div>
                      <div>
                        <p className="font-bold text-sm text-white">{task.title}</p>
                        <p className="text-[11px] text-zinc-400 font-sans">{task.details}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <span className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">
                        {task.system}
                      </span>
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${
                          taskDone
                            ? "bg-emerald-500/20 text-emerald-300"
                            : "bg-zinc-800 text-zinc-500"
                        }`}
                      >
                        {taskDone ? "COMPLETED" : "WAITING"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 border-t border-zinc-800 pt-3 flex items-center justify-between font-mono text-[10px] text-zinc-500">
              <span>Audit Log: Signed & Timestamped by Orchestrator</span>
              <span className="text-emerald-400">Total Execution Elapsed: 4.8s</span>
            </div>
          </div>
        )}
      </div>
    </UIWrapper>
  );
};
