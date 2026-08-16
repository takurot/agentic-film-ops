"use client";

export interface ChatMessage {
  time: string;
  sender: string;
  message: string;
}

export interface AiInterpretation {
  status: "AVAILABLE" | "UNAVAILABLE" | "UNKNOWN";
  window?: string;
  constraints?: string[];
}

export interface ExternalCommunicationMockProps {
  agentTitle?: string;
  subjectName?: string;
  request?: ChatMessage;
  reply?: ChatMessage;
  interpretation?: AiInterpretation;
  className?: string;
}

const DEFAULT_REQUEST: ChatMessage = {
  time: "14:03",
  sender: "AI → Manager",
  message: "Production schedule change request:\nCould Emma move Scene 42\nto Wednesday 16:00–20:00?",
};

const DEFAULT_REPLY: ChatMessage = {
  time: "14:07",
  sender: "Manager → AI",
  message: "She can make it after 4 PM,\nbut must finish by 8 PM.",
};

const DEFAULT_INTERPRETATION: AiInterpretation = {
  status: "AVAILABLE",
  window: "16:00–20:00",
  constraints: ["Hard stop 20:00"],
};

export function ExternalCommunicationMock({
  agentTitle = "ACTOR AGENT",
  subjectName = "Emma Carter",
  request = DEFAULT_REQUEST,
  reply = DEFAULT_REPLY,
  interpretation = DEFAULT_INTERPRETATION,
  className = "",
}: ExternalCommunicationMockProps) {
  return (
    <div
      aria-label="External Communication Mock"
      className={`rounded-lg border border-zinc-800 bg-zinc-950/90 font-mono text-xs shadow-xl ${className}`}
    >
      {/* Header */}
      <div className="border-b border-zinc-800/80 bg-zinc-900/40 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2 w-2 rounded-full bg-violet-400 animate-pulse" />
            <h2 className="font-bold uppercase tracking-wider text-zinc-100 text-xs">
              EXTERNAL COMMUNICATION
            </h2>
          </div>
          <span className="text-[10px] text-zinc-500 uppercase tracking-widest">
            SPEC §9.5 • LLM Structuring
          </span>
        </div>
        <div className="mt-1 text-[11px] text-zinc-400">
          <span className="font-semibold text-zinc-300">{agentTitle}</span>
          <span className="mx-1 text-zinc-600">•</span>
          <span className="text-zinc-200">{subjectName}</span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Step 1: AI -> Manager Request */}
        <div className="rounded border border-zinc-800/80 bg-zinc-900/40 p-3">
          <div className="text-[10px] font-semibold text-cyan-400">
            {request.time} {request.sender}
          </div>
          <div className="mt-1.5 whitespace-pre-line text-zinc-300 leading-relaxed text-xs">
            {request.message}
          </div>
        </div>

        {/* Step 2: Manager -> AI Reply */}
        <div className="rounded border border-zinc-800/80 bg-zinc-900/40 p-3">
          <div className="text-[10px] font-semibold text-purple-400">
            {reply.time} {reply.sender}
          </div>
          <div className="mt-1.5 whitespace-pre-line text-zinc-200 leading-relaxed text-xs">
            {reply.message}
          </div>
        </div>

        {/* Step 3: AI Interpretation Box */}
        <div className="rounded-md border border-emerald-500/40 bg-emerald-950/20 p-3 shadow-inner">
          <div className="flex items-center justify-between">
            <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
              AI Interpretation
            </div>
            <span
              className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
                interpretation.status === "AVAILABLE"
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  : interpretation.status === "UNAVAILABLE"
                  ? "bg-red-500/20 text-red-300 border border-red-500/40"
                  : "bg-zinc-800 text-zinc-300"
              }`}
            >
              {interpretation.status}
            </span>
          </div>

          <div className="mt-2 space-y-1 text-xs">
            {interpretation.window && (
              <div className="text-zinc-200">
                <span className="text-zinc-400">Window: </span>
                <span className="font-semibold text-emerald-300">{interpretation.window}</span>
              </div>
            )}
            {interpretation.constraints && interpretation.constraints.length > 0 && (
              <div className="text-zinc-200">
                {interpretation.constraints.map((c, i) => (
                  <div key={i} className="text-zinc-300">
                    <span className="text-zinc-400">Constraint: </span>
                    <span className="text-amber-300">{c}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-zinc-800/60 bg-zinc-900/20 px-4 py-2 text-[10px] text-zinc-600 flex justify-between">
        <span>Unstructured Free Text → Structured Constraint</span>
        <span>Zero Human Re-entry</span>
      </div>
    </div>
  );
}
