import React from "react";
import { useCurrentFrame, spring, useVideoConfig } from "remotion";
import { UIWrapper } from "../components/UIWrapper";


export const Scene5_ManagerComms: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const msg1Spring = spring({ frame: frame, fps, config: { damping: 12 } });
  const msg2Spring = spring({ frame: frame - 40, fps, config: { damping: 12 } });
  const parseSpring = spring({ frame: frame - 80, fps, config: { damping: 12 } });

  return (
    <UIWrapper
      title="External Communication Mock — Automated Talent Negotiation"
      badge="GEMINI MULTIMODAL & STRUCTURED OUTPUT"
    >
      <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 lg:grid-cols-12 h-[520px]">
        {/* Left Column: Chat Dialogue (7 cols) */}
        <div className="col-span-7 flex flex-col justify-between rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 backdrop-blur-md">
          <div>
            <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-cyan-500/20 text-cyan-400 font-bold">
                  🎭
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Talent Agency Management</h4>
                  <p className="font-mono text-xs text-zinc-400">Agent Rep for Emma Carter (ACT-001)</p>
                </div>
              </div>
              <span className="flex items-center gap-1.5 font-mono text-[10px] text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                ACTIVE DISPATCH
              </span>
            </div>

            {/* Chat Bubbles */}
            <div className="mt-6 space-y-4">
              {/* Outgoing Message from Actor Agent */}
              <div
                style={{ transform: `scale(${msg1Spring})` }}
                className="flex flex-col items-end"
              >
                <div className="max-w-md rounded-2xl rounded-tr-none bg-emerald-600 px-4 py-3 text-xs text-white shadow-lg">
                  <p className="font-mono text-[10px] text-emerald-200 uppercase font-bold mb-1">
                    ACTOR AGENT (AUTOMATED OUTREACH)
                  </p>
                  <p>
                    Production schedule contingency request: Could Emma Carter shift Scene 42 filming to Wednesday 16:00–20:00 at Studio B?
                  </p>
                </div>
                <span className="mt-1 font-mono text-[10px] text-zinc-500">14:03 PST • Delivered</span>
              </div>

              {/* Incoming Message from Talent Manager */}
              {frame >= 40 && (
                <div
                  style={{ transform: `scale(${msg2Spring})` }}
                  className="flex flex-col items-start"
                >
                  <div className="max-w-md rounded-2xl rounded-tl-none bg-zinc-800 border border-zinc-700 px-4 py-3 text-xs text-zinc-200 shadow-lg">
                    <p className="font-mono text-[10px] text-cyan-400 uppercase font-bold mb-1">
                      TALENT AGENCY MANAGER
                    </p>
                    <p>
                      Confirmed: Emma is available starting 16:00. Studio B location accepted. SAG-AFTRA turnaround rules compliant.
                    </p>
                  </div>
                  <span className="mt-1 font-mono text-[10px] text-zinc-500">14:07 PST • Received</span>
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-zinc-800/80 pt-3 font-mono text-[11px] text-zinc-500 flex justify-between">
            <span>Response Latency: 14 seconds</span>
            <span className="text-emerald-400">Zero Human Friction</span>
          </div>
        </div>

        {/* Right Column: LLM Parsing & Extraction (5 cols) */}
        <div className="col-span-5 flex flex-col justify-between rounded-xl border border-zinc-800 bg-zinc-950/80 p-6 backdrop-blur-md">
          <div>
            <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
              <h4 className="font-mono text-xs font-bold text-emerald-400 uppercase">
                LLM Structured Extraction
              </h4>
              <span className="font-mono text-[10px] text-zinc-500">Pydantic Schema</span>
            </div>

            {frame >= 80 && (
              <div
                style={{ transform: `scale(${parseSpring})` }}
                className="mt-5 space-y-3 font-mono text-xs"
              >
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3">
                  <span className="text-zinc-400">talent_available:</span>{" "}
                  <span className="font-bold text-emerald-400">true</span>
                </div>
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3">
                  <span className="text-zinc-400">call_time_agreed:</span>{" "}
                  <span className="font-bold text-cyan-300">"16:00 PST"</span>
                </div>
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3">
                  <span className="text-zinc-400">location_confirmed:</span>{" "}
                  <span className="font-bold text-zinc-200">"Studio B Soundstage"</span>
                </div>
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3">
                  <span className="text-zinc-400">sag_turnaround_compliant:</span>{" "}
                  <span className="font-bold text-emerald-400">true</span>
                </div>
              </div>
            )}

          </div>

          <div className="mt-4 rounded-lg bg-zinc-900 border border-zinc-800 p-3 font-mono text-[10px] text-zinc-400 flex items-center justify-between">
            <span>Gemini Extraction Latency:</span>
            <span className="text-emerald-400 font-bold">185ms (High Fidelity)</span>
          </div>
        </div>
      </div>
    </UIWrapper>
  );
};
