"use client";

import { useMemo, useRef, useEffect } from "react";
import type { AnalysisEvent, MCPCallEvent, AgentEvent } from "@/lib/eventStream";
import { isMCPCallEvent } from "@/lib/eventStream";

export interface McpActivityMonitorProps {
  events: AnalysisEvent[];
  className?: string;
  maxEntries?: number;
}

interface McpLogItem {
  id: string;
  timestamp: string;
  kind: "call" | "response" | "wait" | "error";
  text: string;
}

export function McpActivityMonitor({
  events,
  className = "",
  maxEntries = 100,
}: McpActivityMonitorProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Transform events into formatted SPEC §9.3 log entries
  const logs = useMemo(() => {
    const items: McpLogItem[] = [];

    events.forEach((event, index) => {
      if (isMCPCallEvent(event)) {
        const mcpEvent = event as MCPCallEvent;
        if (mcpEvent.status === "QUERYING_MCP") {
          const args = mcpEvent.resource ? mcpEvent.resource : "";
          items.push({
            id: `mcp-${index}-call`,
            timestamp: mcpEvent.timestamp,
            kind: "call",
            text: `→ ${mcpEvent.server}.${mcpEvent.tool}(${args})`,
          });
        } else if (mcpEvent.status === "RESPONSE_RECEIVED") {
          items.push({
            id: `mcp-${index}-res`,
            timestamp: mcpEvent.timestamp,
            kind: "response",
            text: `← ${mcpEvent.message}`,
          });
        } else if (mcpEvent.status === "FAILED") {
          items.push({
            id: `mcp-${index}-err`,
            timestamp: mcpEvent.timestamp,
            kind: "error",
            text: `✗ ${mcpEvent.message}`,
          });
        }
      } else {
        const agentEvent = event as AgentEvent;
        if (agentEvent.status === "WAITING_EXTERNAL") {
          items.push({
            id: `mcp-${index}-wait`,
            timestamp: agentEvent.timestamp,
            kind: "wait",
            text: `⏳ ${agentEvent.message}`,
          });
        }
      }
    });

    return items.slice(-maxEntries);
  }, [events, maxEntries]);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs.length]);

  return (
    <div
      aria-label="MCP Activity Monitor"
      className={`flex flex-col rounded-lg border border-zinc-800 bg-zinc-950/90 font-mono text-xs shadow-xl ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800/80 px-4 py-3 bg-zinc-900/40">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
          <h2 className="font-bold uppercase tracking-wider text-zinc-100 text-xs">
            LIVE MCP ACTIVITY
          </h2>
        </div>
        <span className="rounded bg-zinc-800/80 px-2 py-0.5 text-[10px] text-zinc-400">
          {logs.length} calls
        </span>
      </div>

      {/* Terminal Log Area */}
      <div
        ref={scrollRef}
        tabIndex={0}
        aria-label="MCP Log Stream"
        className="flex-1 overflow-y-auto p-4 space-y-3 max-h-96 min-h-[160px] select-text focus:outline-none"
      >
        {logs.length === 0 ? (
          <div className="flex h-full min-h-[120px] flex-col items-center justify-center text-center text-zinc-600">
            <span className="text-sm">⏳</span>
            <p className="mt-1 text-[11px]">Awaiting MCP tool calls…</p>
            <p className="text-[10px] text-zinc-700">
              Tool invocations across servers will appear in real time
            </p>
          </div>
        ) : (
          logs.map((item) => (
            <div key={item.id} className="leading-tight animate-fadeIn">
              <div className="text-[10px] text-zinc-600 select-none">
                {item.timestamp}
              </div>
              <div
                className={`text-xs font-semibold ${
                  item.kind === "call"
                    ? "text-cyan-300"
                    : item.kind === "response"
                    ? "text-emerald-300"
                    : item.kind === "wait"
                    ? "text-amber-300 animate-pulse"
                    : "text-red-400"
                }`}
              >
                {item.text}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer / Protocol Notice */}
      <div className="border-t border-zinc-800/60 bg-zinc-900/20 px-4 py-2 text-[10px] text-zinc-600 flex justify-between">
        <span>SPEC §9.3 • Model Context Protocol</span>
        <span>Standardized Tool Bus</span>
      </div>
    </div>
  );
}
