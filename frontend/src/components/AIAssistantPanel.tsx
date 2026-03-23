"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Send, Bot, User, Loader2 } from "lucide-react";
import { validateAssistantResponse, type AssistantResponse } from "@/lib/assistantTypes";
import type { ActiveLayers } from "@/types/dashboard";
import type { AIResultState } from "@/hooks/useAIResultCycler";
import { ChevronLeft, ChevronRight, XCircle } from "lucide-react";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  response?: AssistantResponse;
}

interface AIAssistantPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyLayers: (layers: Record<string, boolean>) => void;
  onFlyTo: (lat: number, lng: number, zoom?: number) => void;
  onSelectEntity: (entity: { type: string; id: string | number } | null) => void;
  onApplyFilters?: (filters: Record<string, string[]>) => void;
  onSetAIResults?: (entities: Array<{ type: string; id: string | number }>) => void;
  aiResultState?: AIResultState;
  onAIResultNext?: () => void;
  onAIResultPrev?: () => void;
  onAIResultClear?: () => void;
  viewport?: { south: number; west: number; north: number; east: number } | null;
}

export default function AIAssistantPanel({
  isOpen,
  onClose,
  onApplyLayers,
  onFlyTo,
  onSelectEntity,
  onApplyFilters,
  onSetAIResults,
  aiResultState,
  onAIResultNext,
  onAIResultPrev,
  onAIResultClear,
  viewport,
}: AIAssistantPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) inputRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const applyResponse = useCallback(
    (resp: AssistantResponse) => {
      if (resp.layers) onApplyLayers(resp.layers);
      if (resp.viewport) onFlyTo(resp.viewport.lat, resp.viewport.lng, resp.viewport.zoom);
      if (resp.filters && onApplyFilters) onApplyFilters(resp.filters);

      // If AI returned a result set, use that for cycling (takes priority over highlight_entities)
      if (resp.result_entities?.length > 0 && onSetAIResults) {
        onSetAIResults(resp.result_entities);
      } else if (resp.highlight_entities?.length > 0) {
        onSelectEntity(resp.highlight_entities[0]);
      }
    },
    [onApplyLayers, onFlyTo, onSelectEntity, onApplyFilters, onSetAIResults],
  );

  const handleSend = async () => {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);

    try {
      const conversation = messages.map((m) => ({
        role: m.role,
        content: m.role === "assistant" ? (m.response?.summary || m.content) : m.content,
      }));

      const resp = await fetch("/api/assistant/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, viewport, conversation }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: "Request failed" }));
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: err.error || `Error: ${resp.status}` },
        ]);
        return;
      }

      const raw = await resp.json();
      const validated = validateAssistantResponse(raw);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: validated.summary, response: validated },
      ]);
      applyResponse(validated);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Connection error — is the backend running?" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="absolute bottom-24 right-8 z-[400] w-96 pointer-events-auto"
    >
      <div className="bg-black/90 backdrop-blur-md border border-cyan-800/60 rounded-xl shadow-[0_4px_30px_rgba(0,0,0,0.5)] flex flex-col max-h-[500px]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-cyan-800/40">
          <div className="flex items-center gap-2">
            <Bot size={14} className="text-cyan-400" />
            <span className="text-[10px] text-cyan-400 font-mono tracking-[0.2em] font-bold">
              AI ANALYST
            </span>
          </div>
          <button onClick={onClose} className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors">
            <X size={14} />
          </button>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto styled-scrollbar px-4 py-3 space-y-3 min-h-[200px] max-h-[350px]">
          {messages.length === 0 && (
            <div className="text-[10px] text-[var(--text-muted)] font-mono text-center py-8">
              Ask me about anything on the dashboard.
              <br />
              <span className="text-cyan-500/60">
                "Show military flights near Ukraine"
                <br />
                "What ships are in the Mediterranean?"
                <br />
                "Brief me on current hotspots"
              </span>
            </div>
          )}
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
                {msg.response?.layers && (
                  <div className="mt-1.5 pt-1.5 border-t border-cyan-800/30 text-[9px] text-cyan-500/70">
                    Layers updated: {Object.entries(msg.response.layers).map(([k, v]) => `${k}:${v ? "ON" : "OFF"}`).join(", ")}
                  </div>
                )}
                {msg.response?.viewport && (
                  <div className="text-[9px] text-cyan-500/70">
                    Camera: {msg.response.viewport.lat.toFixed(1)}, {msg.response.viewport.lng.toFixed(1)} z{msg.response.viewport.zoom}
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <User size={12} className="text-[var(--text-muted)] mt-1 flex-shrink-0" />
              )}
            </div>
          ))}
          {loading && (
            <div className="flex gap-2 items-center">
              <Bot size={12} className="text-cyan-400" />
              <Loader2 size={12} className="text-cyan-400 animate-spin" />
              <span className="text-[9px] text-cyan-400/60 font-mono">Analyzing...</span>
            </div>
          )}
        </div>

        {/* AI Result Navigation Bar */}
        {aiResultState?.active && (
          <div className="px-3 py-2 border-t border-cyan-800/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-cyan-400 font-mono tracking-wider">RESULTS</span>
              <button onClick={onAIResultPrev} className="p-0.5 text-cyan-400 hover:text-cyan-300">
                <ChevronLeft size={12} />
              </button>
              <span className="text-[10px] text-[var(--text-primary)] font-mono">
                {aiResultState.index + 1} / {aiResultState.total}
              </span>
              <button onClick={onAIResultNext} className="p-0.5 text-cyan-400 hover:text-cyan-300">
                <ChevronRight size={12} />
              </button>
            </div>
            <button onClick={onAIResultClear} className="p-0.5 text-[var(--text-muted)] hover:text-cyan-400">
              <XCircle size={12} />
            </button>
          </div>
        )}

        {/* Input */}
        <div className="px-3 py-2.5 border-t border-cyan-800/40">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }}
              placeholder="Ask the analyst..."
              disabled={loading}
              className="flex-1 bg-transparent text-[10px] text-[var(--text-primary)] font-mono tracking-wider outline-none placeholder:text-[var(--text-muted)] disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="p-1.5 rounded border border-cyan-800/40 text-cyan-400 hover:bg-cyan-950/30 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <Send size={12} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
