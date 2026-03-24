"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Send, Bot, User, Loader2, ChevronLeft, ChevronRight, XCircle, Plus, Trash2, ArrowLeft, Zap } from "lucide-react";
import { validateAssistantResponse, extractStoredAction, type AssistantResponse } from "@/lib/assistantTypes";
import type { DashboardData } from "@/types/dashboard";
import type { AIResultState } from "@/hooks/useAIResultCycler";
import { findEntityInData } from "@/hooks/useAIResultCycler";
import { toSelectedEntity } from "@/hooks/useCategoryCycler";
import {
  useConversationStore,
  saveConversation as saveConv,
} from "@/hooks/useConversationStore";
import type { StoredMessage, StoredAction, StoredConversation } from "@/types/aiConversation";

function generateId(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "yesterday";
  return `${days}d ago`;
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
  data: DashboardData;
}

type PanelMode = "chat" | "history" | "actions";

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
  data,
}: AIAssistantPanelProps) {
  const [messages, setMessages] = useState<StoredMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [progressText, setProgressText] = useState<string | null>(null);
  const [mode, setMode] = useState<PanelMode>("chat");
  const [conversationId, setConversationId] = useState<string>(generateId);
  const [flashEntity, setFlashEntity] = useState<string | null>(null);
  const [expandedReasoning, setExpandedReasoning] = useState<Set<number>>(new Set());
  const [prevMode, setPrevMode] = useState<PanelMode>("chat");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const store = useConversationStore();

  useEffect(() => {
    if (isOpen && mode === "chat") inputRef.current?.focus();
  }, [isOpen, mode]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Save conversation to localStorage whenever messages change
  const saveCurrentConversation = useCallback(
    (msgs: StoredMessage[]) => {
      if (msgs.length === 0) return;
      const firstUserMsg = msgs.find((m) => m.role === "user");
      const title = firstUserMsg
        ? firstUserMsg.content.slice(0, 60)
        : "New conversation";
      const now = Date.now();
      store.save({
        id: conversationId,
        title,
        messages: msgs,
        createdAt: msgs[0]?.timestamp ?? now,
        updatedAt: now,
      });
    },
    [conversationId, store],
  );

  const applyAction = useCallback(
    (action: StoredAction) => {
      if (action.layers) onApplyLayers(action.layers);
      if (action.viewport) onFlyTo(action.viewport.lat, action.viewport.lng, action.viewport.zoom);
      if (action.filters && onApplyFilters) onApplyFilters(action.filters);
      if (action.result_entities && action.result_entities.length > 0 && onSetAIResults) {
        onSetAIResults(action.result_entities);
      } else {
        // Clear stale AI results so the results bar and dimming don't persist
        onAIResultClear?.();
        if (action.highlight_entities && action.highlight_entities.length > 0) {
          onSelectEntity(action.highlight_entities[0]);
        }
      }
    },
    [onApplyLayers, onFlyTo, onSelectEntity, onApplyFilters, onSetAIResults, onAIResultClear],
  );

  const applyResponse = useCallback(
    (resp: AssistantResponse) => {
      if (resp.layers) onApplyLayers(resp.layers);
      if (resp.viewport) onFlyTo(resp.viewport.lat, resp.viewport.lng, resp.viewport.zoom);
      if (resp.filters && onApplyFilters) onApplyFilters(resp.filters);

      if (resp.result_entities?.length > 0 && onSetAIResults) {
        onSetAIResults(resp.result_entities);
      } else {
        onAIResultClear?.();
        if (resp.highlight_entities?.length > 0) {
          onSelectEntity(resp.highlight_entities[0]);
        }
      }
    },
    [onApplyLayers, onFlyTo, onSelectEntity, onApplyFilters, onSetAIResults, onAIResultClear],
  );

  const handleSend = async () => {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");
    const userMsg: StoredMessage = { role: "user", content: query, timestamp: Date.now() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setLoading(true);
    setProgressText("Connecting...");

    try {
      // Filter out error exchanges — sending them back to the LLM causes
      // self-reinforcing refusals. Drop both the error and the user msg that caused it.
      const ERROR_MARKERS = ["Cannot reach", "LLM service unavailable", "Query filtered", "Connection error"];
      const conversation: { role: string; content: string }[] = [];
      for (let i = 0; i < messages.length; i++) {
        const m = messages[i];
        if (m.role === "assistant" && ERROR_MARKERS.some((e) => m.content.includes(e))) {
          if (conversation.length > 0 && conversation[conversation.length - 1].role === "user") {
            conversation.pop();
          }
          continue;
        }
        conversation.push({ role: m.role, content: m.content });
      }

      const resp = await fetch("/api/assistant/query/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, viewport, conversation }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: "Request failed" }));
        let errorContent: string;
        if (resp.status === 502) {
          errorContent = "Cannot reach the backend server.";
        } else if (err.error_type === "content_filter") {
          errorContent = `Query filtered: ${err.error || "The LLM provider declined this request."}`;
        } else if (err.error_type === "connection" || resp.status === 503) {
          errorContent = `LLM service unavailable: ${err.error || "Try again in a moment."}`;
        } else {
          errorContent = err.error || `Error: ${resp.status}`;
        }
        const errMsg: StoredMessage = {
          role: "assistant",
          content: errorContent,
          timestamp: Date.now(),
        };
        const updated = [...newMessages, errMsg];
        setMessages(updated);
        saveCurrentConversation(updated);
        return;
      }

      // Read SSE stream for real-time progress
      const reader = resp.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }
      const decoder = new TextDecoder();
      let buffer = "";
      let handled = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events (delimited by double newline)
        let boundary: number;
        while ((boundary = buffer.indexOf("\n\n")) !== -1) {
          const chunk = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);

          // Parse SSE: "event: <type>\ndata: <json>"
          let eventType = "";
          let eventData = "";
          for (const line of chunk.split("\n")) {
            if (line.startsWith("event: ")) eventType = line.slice(7);
            else if (line.startsWith("data: ")) eventData = line.slice(6);
          }
          if (!eventType || !eventData) continue;

          if (eventType === "status") {
            try {
              const status = JSON.parse(eventData);
              setProgressText(status.detail || "Working...");
            } catch { /* ignore parse errors */ }
          } else if (eventType === "result") {
            try {
              const raw = JSON.parse(eventData);
              const validated = validateAssistantResponse(raw);
              const action = extractStoredAction(validated);
              const assistantMsg: StoredMessage = {
                role: "assistant",
                content: validated.summary,
                action,
                reasoning_steps: validated.reasoning_steps,
                duration_ms: validated.duration_ms,
                provider: validated.provider,
                timestamp: Date.now(),
              };
              const updated = [...newMessages, assistantMsg];
              setMessages(updated);
              saveCurrentConversation(updated);
              applyResponse(validated);
              handled = true;
            } catch { /* ignore parse errors */ }
          } else if (eventType === "error") {
            try {
              const err = JSON.parse(eventData);
              let errorContent: string;
              if (err.error_type === "content_filter") {
                errorContent = `Query filtered: ${err.error || "The LLM provider declined this request."}`;
              } else {
                errorContent = `LLM service unavailable: ${err.error || "Try again in a moment."}`;
              }
              const errMsg: StoredMessage = {
                role: "assistant",
                content: errorContent,
                timestamp: Date.now(),
              };
              const updated = [...newMessages, errMsg];
              setMessages(updated);
              saveCurrentConversation(updated);
              handled = true;
            } catch { /* ignore parse errors */ }
          }
        }
      }

      if (!handled) {
        const errMsg: StoredMessage = {
          role: "assistant",
          content: "Connection lost before receiving a response.",
          timestamp: Date.now(),
        };
        const updated = [...newMessages, errMsg];
        setMessages(updated);
        saveCurrentConversation(updated);
      }
    } catch {
      const errMsg: StoredMessage = {
        role: "assistant",
        content: "Connection error — is the backend running?",
        timestamp: Date.now(),
      };
      const updated = [...newMessages, errMsg];
      setMessages(updated);
      saveCurrentConversation(updated);
    } finally {
      setLoading(false);
      setProgressText(null);
    }
  };

  const handleClear = useCallback(() => {
    if (messages.length > 0) {
      saveCurrentConversation(messages);
    }
    setConversationId(generateId());
    setMessages([]);
    onAIResultClear?.();
  }, [messages, saveCurrentConversation, onAIResultClear]);

  const handleLoadConversation = useCallback(
    (id: string) => {
      const conv = store.load(id);
      if (!conv) return;
      // Save current conversation before switching
      if (messages.length > 0) {
        saveCurrentConversation(messages);
      }
      setConversationId(conv.id);
      setMessages(conv.messages);
      setMode("chat");
      onAIResultClear?.();
    },
    [store, messages, saveCurrentConversation, onAIResultClear],
  );

  const handleNewChat = useCallback(() => {
    if (messages.length > 0) {
      saveCurrentConversation(messages);
    }
    setConversationId(generateId());
    setMessages([]);
    setMode("chat");
    onAIResultClear?.();
  }, [messages, saveCurrentConversation, onAIResultClear]);

  const handleTrackEntity = useCallback(
    (type: string, id: string | number) => {
      const found = findEntityInData(type, id, data);
      if (found) {
        const entity = toSelectedEntity(found.item, found.entityType);
        const lat = found.item.lat ?? found.item.geometry?.coordinates?.[1];
        const lng = found.item.lng ?? found.item.lon ?? found.item.geometry?.coordinates?.[0];
        if (lat != null && lng != null) onFlyTo(lat, lng);
        onSelectEntity(entity);
      } else {
        const key = `${type}:${id}`;
        setFlashEntity(key);
        setTimeout(() => setFlashEntity(null), 1500);
      }
    },
    [data, onFlyTo, onSelectEntity],
  );

  const hasActions = useMemo(
    () => messages.some((m) => m.action),
    [messages],
  );

  const actionMessages = useMemo(
    () => messages.filter((m) => m.action),
    [messages],
  );

  if (!isOpen) return null;

  const chipClass =
    "text-[9px] font-mono px-2 py-0.5 rounded border border-cyan-800/40 text-cyan-400 hover:bg-cyan-950/30 cursor-pointer transition-colors inline-flex items-center gap-1";

  const formatLayerLabel = (layers: Record<string, boolean>) => {
    const on = Object.entries(layers).filter(([, v]) => v).map(([k]) => k.replace(/_/g, " ").toUpperCase());
    if (on.length === 0) return "HIDE LAYERS";
    if (on.length <= 2) return on.join(", ") + " ON";
    return `${on.length} LAYERS ON`;
  };

  const renderActionChips = (action: StoredAction) => (
    <div className="mt-1.5 pt-1.5 border-t border-cyan-800/30 flex flex-wrap gap-1">
      {action.viewport && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onFlyTo(action.viewport!.lat, action.viewport!.lng, action.viewport!.zoom); }}
          className={chipClass}
        >
          {action.viewport_label ? `GO TO ${action.viewport_label.toUpperCase()}` : `FLY TO ${action.viewport.lat.toFixed(1)}, ${action.viewport.lng.toFixed(1)}`}
        </button>
      )}
      {action.layers && (
        <button type="button" onClick={(e) => { e.stopPropagation(); onApplyLayers(action.layers!); }} className={chipClass}>
          {formatLayerLabel(action.layers)}
        </button>
      )}
      {action.filters && (
        <button type="button" onClick={(e) => { e.stopPropagation(); onApplyFilters?.(action.filters!); }} className={chipClass}>
          {Object.keys(action.filters).length === 0 ? "CLEAR FILTERS" : "APPLY FILTERS"}
        </button>
      )}
      {action.result_entities && action.result_entities.length > 0 && (
        <button type="button" onClick={(e) => { e.stopPropagation(); onSetAIResults?.(action.result_entities!); }} className={chipClass}>
          SHOW {action.result_entities.length} RESULTS
        </button>
      )}
      {action.highlight_entities?.map((e, i) => {
        const key = `${e.type}:${e.id}`;
        return (
          <button
            type="button"
            key={i}
            onClick={(ev) => { ev.stopPropagation(); handleTrackEntity(e.type, e.id); }}
            className={`${chipClass} ${flashEntity === key ? "border-red-500/60 text-red-400" : ""}`}
          >
            {flashEntity === key ? "NOT IN RANGE" : `${e.type.toUpperCase()} ${e.id}`}
          </button>
        );
      })}
    </div>
  );

  const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 80 : -80, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -80 : 80, opacity: 0 }),
  };

  // Direction for transitions: history < chat < actions
  const modeOrder: Record<PanelMode, number> = { history: 0, chat: 1, actions: 2 };
  const direction = modeOrder[mode] - modeOrder[prevMode];

  const switchMode = (next: PanelMode) => {
    setPrevMode(mode);
    setMode(next);
  };

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
            {mode === "chat" && (
              <button
                type="button"
                onClick={() => switchMode("history")}
                className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors"
                title="Conversation history"
              >
                <ArrowLeft size={14} />
              </button>
            )}
            {mode === "actions" && (
              <button
                type="button"
                onClick={() => switchMode("chat")}
                className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors"
              >
                <ArrowLeft size={14} />
              </button>
            )}
            <Bot size={14} className="text-cyan-400" />
            <span className="text-[10px] text-cyan-400 font-mono tracking-[0.2em] font-bold">
              {mode === "actions" ? "ACTIONS" : "AI ANALYST"}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            {mode === "chat" && hasActions && (
              <button
                type="button"
                onClick={() => switchMode("actions")}
                className="text-[9px] font-mono px-2 py-0.5 rounded border border-cyan-800/40 text-cyan-500/70 hover:text-cyan-400 hover:bg-cyan-950/30 transition-colors"
                title="View past actions"
              >
                <Zap size={10} />
              </button>
            )}
            {mode === "chat" && messages.length > 0 && (
              <button
                type="button"
                onClick={handleClear}
                className="text-[9px] font-mono px-2 py-0.5 rounded border border-cyan-800/40 text-cyan-500/70 hover:text-cyan-400 hover:bg-cyan-950/30 transition-colors"
              >
                CLEAR
              </button>
            )}
            {mode === "history" && (
              <button
                type="button"
                onClick={handleNewChat}
                className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors"
                title="New chat"
              >
                <Plus size={14} />
              </button>
            )}
            <button type="button" onClick={onClose} className="text-[var(--text-muted)] hover:text-cyan-400 transition-colors">
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Content area with mode transitions */}
        <AnimatePresence mode="wait" custom={direction}>
          {mode === "chat" && (
            <motion.div
              key="chat"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.15 }}
              className="flex flex-col flex-1 min-h-0"
            >
              {/* Messages */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto styled-scrollbar px-4 py-3 space-y-3 min-h-[200px] max-h-[350px]">
                {messages.length === 0 && (
                  <div className="text-[10px] text-[var(--text-muted)] font-mono text-center py-8">
                    Ask me about anything on the dashboard.
                    <br />
                    <span className="text-cyan-500/60">
                      &quot;Show military flights near Ukraine&quot;
                      <br />
                      &quot;What ships are in the Mediterranean?&quot;
                      <br />
                      &quot;Brief me on current hotspots&quot;
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
                      {msg.role === "assistant" && msg.duration_ms != null && (
                        <div className="mt-1 text-[7px] font-mono text-cyan-600/40">
                          {(msg.duration_ms / 1000).toFixed(1)}s{msg.provider ? ` · ${msg.provider}` : ""}
                        </div>
                      )}
                      {msg.reasoning_steps && msg.reasoning_steps.length > 0 && (
                        <div className="mt-1.5">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedReasoning((prev) => {
                                const next = new Set(prev);
                                next.has(i) ? next.delete(i) : next.add(i);
                                return next;
                              });
                            }}
                            className="text-[8px] font-mono text-cyan-500/50 hover:text-cyan-400 transition-colors"
                          >
                            {expandedReasoning.has(i) ? "HIDE" : "SHOW"} REASONING ({msg.reasoning_steps.length} steps)
                          </button>
                          {expandedReasoning.has(i) && (
                            <div className="mt-1 pl-2 border-l border-cyan-800/30 space-y-1">
                              {msg.reasoning_steps.map((step, si) => (
                                <div key={si} className="text-[8px] font-mono leading-snug">
                                  <span className={
                                    step.type === "thinking" ? "text-amber-400/70" :
                                    step.type === "tool_call" ? "text-blue-400/70" :
                                    step.type === "tool_result" ? "text-green-400/70" :
                                    "text-cyan-400/70"
                                  }>
                                    {step.type.toUpperCase()}
                                  </span>
                                  <span className="text-[var(--text-muted)] ml-1">
                                    {step.content.length > 300 ? step.content.slice(0, 300) + "…" : step.content}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      {msg.action && renderActionChips(msg.action)}
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
                    <span className="text-[9px] text-cyan-400/60 font-mono">{progressText || "Analyzing..."}</span>
                  </div>
                )}
              </div>

              {/* AI Result Navigation Bar */}
              {aiResultState?.active && (
                <div className="px-3 py-2 border-t border-cyan-800/40 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-cyan-400 font-mono tracking-wider">RESULTS</span>
                    <button type="button" onClick={onAIResultPrev} className="p-0.5 text-cyan-400 hover:text-cyan-300">
                      <ChevronLeft size={12} />
                    </button>
                    <span className="text-[10px] text-[var(--text-primary)] font-mono">
                      {aiResultState.index + 1} / {aiResultState.total}
                    </span>
                    <button type="button" onClick={onAIResultNext} className="p-0.5 text-cyan-400 hover:text-cyan-300">
                      <ChevronRight size={12} />
                    </button>
                  </div>
                  <button type="button" onClick={onAIResultClear} className="p-0.5 text-[var(--text-muted)] hover:text-cyan-400">
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
                    type="button"
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="p-1.5 rounded border border-cyan-800/40 text-cyan-400 hover:bg-cyan-950/30 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <Send size={12} />
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {mode === "history" && (
            <motion.div
              key="history"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.15 }}
              className="flex-1 overflow-y-auto styled-scrollbar min-h-[200px] max-h-[400px]"
            >
              {store.index.length === 0 ? (
                <div className="text-[10px] text-[var(--text-muted)] font-mono text-center py-12">
                  No past conversations.
                </div>
              ) : (
                <div className="py-1">
                  {store.index.map((entry) => (
                    <div
                      key={entry.id}
                      className={`group flex items-center justify-between px-4 py-2.5 cursor-pointer hover:bg-cyan-950/20 transition-colors border-b border-cyan-800/20 ${
                        entry.id === conversationId ? "bg-cyan-950/30" : ""
                      }`}
                      onClick={() => handleLoadConversation(entry.id)}
                    >
                      <div className="flex-1 min-w-0 mr-3">
                        <div className="text-[10px] font-mono text-[var(--text-primary)] truncate">
                          {entry.title}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[8px] font-mono text-[var(--text-muted)]">
                            {relativeTime(entry.updatedAt)}
                          </span>
                          <span className="text-[8px] font-mono text-cyan-500/50">
                            {entry.messageCount} msgs
                          </span>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          store.remove(entry.id);
                          // If we deleted the active conversation, reset to a fresh one
                          if (entry.id === conversationId) {
                            setConversationId(generateId());
                            setMessages([]);
                            onAIResultClear?.();
                          }
                        }}
                        className="opacity-0 group-hover:opacity-100 text-[var(--text-muted)] hover:text-red-400 transition-all p-1"
                        title="Delete conversation"
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {mode === "actions" && (
            <motion.div
              key="actions"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.15 }}
              className="flex-1 overflow-y-auto styled-scrollbar px-4 py-3 space-y-2 min-h-[200px] max-h-[400px]"
            >
              {actionMessages.length === 0 ? (
                <div className="text-[10px] text-[var(--text-muted)] font-mono text-center py-12">
                  No actions in this conversation.
                </div>
              ) : (
                actionMessages.map((msg, i) => (
                  <div
                    key={i}
                    className="bg-[var(--bg-secondary)]/40 border border-cyan-800/30 rounded-lg px-3 py-2"
                  >
                    <div className="text-[10px] font-mono text-[var(--text-primary)] leading-relaxed line-clamp-2">
                      {msg.content}
                    </div>
                    {msg.action && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {msg.action.viewport && (
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); onFlyTo(msg.action!.viewport!.lat, msg.action!.viewport!.lng, msg.action!.viewport!.zoom); }}
                            className={chipClass}
                          >
                            {msg.action.viewport_label ? `GO TO ${msg.action.viewport_label.toUpperCase()}` : `FLY TO ${msg.action.viewport.lat.toFixed(1)}, ${msg.action.viewport.lng.toFixed(1)}`}
                          </button>
                        )}
                        {msg.action.layers && (
                          <button type="button" onClick={(e) => { e.stopPropagation(); onApplyLayers(msg.action!.layers!); }} className={chipClass}>
                            {formatLayerLabel(msg.action.layers)}
                          </button>
                        )}
                        {msg.action.filters && (
                          <button type="button" onClick={(e) => { e.stopPropagation(); onApplyFilters?.(msg.action!.filters!); }} className={chipClass}>
                            {Object.keys(msg.action.filters).length === 0 ? "CLEAR FILTERS" : "APPLY FILTERS"}
                          </button>
                        )}
                        {msg.action.result_entities && msg.action.result_entities.length > 0 && (
                          <button type="button" onClick={(e) => { e.stopPropagation(); onSetAIResults?.(msg.action!.result_entities!); }} className={chipClass}>
                            SHOW {msg.action.result_entities.length} RESULTS
                          </button>
                        )}
                        <button type="button" onClick={(e) => { e.stopPropagation(); applyAction(msg.action!); }} className={`${chipClass} border-cyan-600/50 text-cyan-300`}>
                          REPLAY ALL
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
