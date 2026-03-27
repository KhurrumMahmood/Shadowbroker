"use client";

import { Bot, User, Send } from "lucide-react";
import { FAKE_CONVERSATIONS, DEFAULT_CONVERSATION } from "./fakeChatData";

interface FakeChatPanelProps {
  selectedArtifact: string | null;
}

export default function FakeChatPanel({ selectedArtifact }: FakeChatPanelProps) {
  const messages = (selectedArtifact && FAKE_CONVERSATIONS[selectedArtifact]) || DEFAULT_CONVERSATION;

  return (
    <div className="flex flex-col h-full bg-black/90">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cyan-800/40 flex items-center gap-2">
        <Bot size={12} className="text-cyan-400" />
        <span className="text-[9px] font-mono tracking-[0.2em] text-cyan-500 uppercase">
          AI Analyst
        </span>
        <span className="text-[6px] font-mono tracking-[0.15em] text-yellow-600 bg-yellow-900/20 border border-yellow-800/30 px-1.5 py-0.5 rounded ml-auto uppercase">
          Demo
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto styled-scrollbar p-3 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-2 ${msg.role === "user" ? "justify-end" : ""}`}>
            {msg.role === "assistant" && (
              <Bot size={12} className="text-cyan-400 mt-1 flex-shrink-0" />
            )}
            <div
              className={`text-[10px] font-mono leading-relaxed max-w-[85%] px-3 py-2 rounded-lg ${
                msg.role === "user"
                  ? "bg-cyan-950/40 border border-cyan-800/40 text-[var(--text-secondary)]"
                  : "bg-[var(--bg-secondary)]/60 border border-[var(--border-primary)] text-[var(--text-primary)]"
              }`}
            >
              {msg.content}
              {msg.role === "assistant" && msg.duration_ms != null && (
                <div className="mt-1 text-[7px] font-mono text-cyan-600/40">
                  {(msg.duration_ms / 1000).toFixed(1)}s{msg.provider ? ` · ${msg.provider}` : ""}
                </div>
              )}
            </div>
            {msg.role === "user" && (
              <User size={12} className="text-[var(--text-muted)] mt-1 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>

      {/* Disabled input bar */}
      <div className="px-3 py-2 border-t border-cyan-800/40">
        <div className="flex items-center gap-2 bg-cyan-950/20 border border-cyan-800/30 rounded-lg px-3 py-2 opacity-50">
          <span className="text-[9px] font-mono text-cyan-700 flex-1">
            Type your query...
          </span>
          <Send size={10} className="text-cyan-700" />
        </div>
      </div>
    </div>
  );
}
