"use client";

import type { TodaySceneProgress } from "@/lib/api";

/**
 * TodayProgress – Today's scene progress list (SPEC §9.1).
 */

const statusStyle: Record<string, { badge: string; bar: string }> = {
  COMPLETED: {
    badge: "bg-emerald-500/20 text-emerald-400",
    bar: "bg-emerald-500",
  },
  SHOOTING: {
    badge: "bg-amber-500/20 text-amber-400",
    bar: "bg-amber-500",
  },
  SCHEDULED: {
    badge: "bg-zinc-700/50 text-zinc-400",
    bar: "bg-zinc-600",
  },
};

export function TodayProgress({ scenes }: { scenes: TodaySceneProgress[] }) {
  if (scenes.length === 0) return null;

  return (
    <section aria-label="Today's Scenes">
      <h2 className="mb-3 text-xs font-semibold tracking-wider text-zinc-500 uppercase">
        Today&apos;s Scenes
      </h2>
      <div className="space-y-2">
        {scenes.map((scene) => {
          const style = statusStyle[scene.status] ?? statusStyle.SCHEDULED;
          return (
            <div
              key={scene.scene_id}
              className="flex items-center gap-3 rounded-lg border border-white/5 bg-zinc-900/60 px-4 py-3"
            >
              <span className="min-w-[56px] font-mono text-xs text-zinc-400">
                {scene.scene_id.replace("SC-0", "Scene ")}
              </span>
              <span className="flex-1 text-sm text-zinc-200 truncate">
                {scene.name}
              </span>
              {/* Progress bar */}
              <div className="hidden h-1.5 w-20 overflow-hidden rounded-full bg-zinc-800 sm:block">
                <div
                  className={`h-full rounded-full transition-all ${style.bar}`}
                  style={{ width: `${scene.progress_percent}%` }}
                />
              </div>
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${style.badge}`}
              >
                {scene.status}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
