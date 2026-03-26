"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Send, Bot, User, Loader2, ChevronLeft, ChevronRight, XCircle, Plus, Trash2, ArrowLeft, Zap, Layers } from "lucide-react";
import { validateAssistantResponse, extractStoredAction } from "@/lib/assistantTypes";
import type { DashboardData } from "@/types/dashboard";
import type { AIResultState } from "@/hooks/useAIResultCycler";
import { findEntityInData } from "@/hooks/useAIResultCycler";
import { toSelectedEntity } from "@/hooks/useCategoryCycler";
import { useConversationStore } from "@/hooks/useConversationStore";
import type { StoredMessage, StoredAction } from "@/types/aiConversation";
import ArtifactPanel from "@/components/ArtifactPanel";
import ArtifactBrowser from "@/components/ArtifactBrowser";

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

function tryParseJSON<T>(json: string): T | null {
  try {
    return JSON.parse(json) as T;
  } catch {
    return null;
  }
}

type PanelMode = "chat" | "history" | "actions" | "artifacts";

const STEP_TYPE_COLORS: Record<string, string> = {
  thinking: "text-amber-400/70",
  tool_call: "text-blue-400/70",
  tool_result: "text-green-400/70",
};

const MODE_TITLES: Record<PanelMode, string> = {
  history: "AI ANALYST",
  chat: "AI ANALYST",
  actions: "ACTIONS",
  artifacts: "ARTIFACTS",
};

/** Error markers that identify failed exchanges to strip from conversation history */
const ERROR_MARKERS = ["Cannot reach", "LLM service unavailable", "Query filtered", "Connection error", "Connection lost"];

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
  const [activeArtifact, setActiveArtifact] = useState<{ id: string; title?: string; registryName?: string; version?: number } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const store = useConversationStore();

  useEffect(() => {
    if (isOpen && mode === "chat") inputRef.current?.focus();
  }, [isOpen, mode]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Cancel in-flight SSE stream on unmount
  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

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
      if (action.filters) onApplyFilters?.(action.filters);
      if (action.result_entities && action.result_entities.length > 0 && onSetAIResults) {
        onSetAIResults(action.result_entities);
      } else {
        onAIResultClear?.();
        if (action.highlight_entities && action.highlight_entities.length > 0) {
          onSelectEntity(action.highlight_entities[0]);
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

    function appendAssistantMsg(msg: StoredMessage): void {
      const updated = [...newMessages, msg];
      setMessages(updated);
      saveCurrentConversation(updated);
    }

    function appendError(content: string): void {
      appendAssistantMsg({ role: "assistant", content, timestamp: Date.now() });
    }

    try {
      // Filter out error exchanges -- sending them back to the LLM causes
      // self-reinforcing refusals. Drop both the error and the user msg that caused it.
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

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const resp = await fetch("/api/assistant/query/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          viewport,
          conversation,
          ...(activeArtifact?.registryName ? { active_artifact: { name: activeArtifact.registryName } } : {}),
        }),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ error: "Request failed" }));
        if (resp.status === 502) {
          appendError("Cannot reach the backend server.");
        } else if (err.error_type === "content_filter") {
          appendError(`Query filtered: ${err.error || "The LLM provider declined this request."}`);
        } else if (err.error_type === "connection" || resp.status === 503) {
          appendError(`LLM service unavailable: ${err.error || "Try again in a moment."}`);
        } else {
          appendError(err.error || `Error: ${resp.status}`);
        }
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
            const status = tryParseJSON<{ detail?: string }>(eventData);
            if (status) setProgressText(status.detail || "Working...");
          } else if (eventType === "plan") {
            const plan = tryParseJSON<{ sub_tasks?: unknown[] }>(eventData);
            if (plan) setProgressText(`Analyzing across ${plan.sub_tasks?.length || 0} domains...`);
          } else if (eventType === "sub_result") {
            const sub = tryParseJSON<{ summary?: string }>(eventData);
            if (sub?.summary) {
              setProgressText(sub.summary.slice(0, 80) + (sub.summary.length > 80 ? "..." : ""));
            }
          } else if (eventType === "artifact") {
            const art = tryParseJSON<{ artifact_id?: string; title?: string; registry_name?: string; version?: number }>(eventData);
            if (art?.artifact_id) {
              setActiveArtifact({
                id: art.artifact_id,
                title: art.title,
                registryName: art.registry_name,
                version: art.version,
              });
            }
          } else if (eventType === "result") {
            const raw = tryParseJSON<unknown>(eventData);
            if (raw) {
              const validated = validateAssistantResponse(raw);
              const action = extractStoredAction(validated);
              appendAssistantMsg({
                role: "assistant",
                content: validated.summary,
                action,
                reasoning_steps: validated.reasoning_steps,
                duration_ms: validated.duration_ms,
                provider: validated.provider,
                timestamp: Date.now(),
              });
              if (action) applyAction(action);
              handled = true;
            }
          } else if (eventType === "error") {
            const err = tryParseJSON<{ error_type?: string; error?: string }>(eventData);
            if (err) {
              if (err.error_type === "content_filter") {
                appendError(`Query filtered: ${err.error || "The LLM provider declined this request."}`);
              } else {
                appendError(`LLM service unavailable: ${err.error || "Try again in a moment."}`);
              }
              handled = true;
            }
          }
        }
      }

      if (!handled) {
        appendError("Connection lost before receiving a response.");
      }
    } catch {
      appendError("Connection error — is the backend running?");
    } finally {
      setLoading(false);
      setProgressText(null);
    }
  };

  const resetConversation = useCallback(() => {
    if (messages.length > 0) {
      saveCurrentConversation(messages);
    }
    setConversationId(generateId());
    setMessages([]);
    setActiveArtifact(null);
    onAIResultClear?.();
  }, [messages, saveCurrentConversation, onAIResultClear]);

  const handleLoadConversation = useCallback(
    (id: string) => {
      const conv = store.load(id);
      if (!conv) return;
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
    resetConversation();
    setMode("chat");
  }, [resetConversation]);

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

  const renderCoreChips = (action: StoredAction) => (
    <>
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
    </>
  );

  const renderChatActionChips = (action: StoredAction) => (
    <div className="mt-1.5 pt-1.5 border-t border-cyan-800/30 flex flex-wrap gap-1">
      {renderCoreChips(action)}
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
  const modeOrder: Record<PanelMode, number> = { history: 0, chat: 1, actions: 2, artifacts: 3 };
  const direction = modeOrder[mode] - modeOrder[prevMode];

  const switchMode = (next: PanelMode) => {
    setPrevMode(mode);
    setMode(next);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, width: 400 }}
      animate={{ opacity: 1, y: 0, width: activeArtifact ? 900 : 400 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{
        opacity: { duration: 0.2 },
        y: { duration: 0.2 },
        width: { type: "spring", stiffness: 300, damping: 30 },
      }}
      className="fixed bottom-20 right-6 z-[600] pointer-events-auto max-w-[calc(100vw-3rem)]"
    >
      <div className="bg-black/90 backdrop-blur-md border border-cyan-800/60 rounded-xl shadow-[0_4px_30px_rgba(0,0,0,0.5)] flex flex-row h-[600px] overflow-hidden">
        {/* LEFT: Artifact pane (only when active) */}
        <AnimatePresence>
          {activeArtifact && mode !== "artifacts" && (
            <motion.div
              key="artifact-pane"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 520, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="border-r border-cyan-800/40 flex flex-col overflow-hidden flex-shrink-0 h-full"
            >
              <ArtifactPanel
                artifactId={activeArtifact.id}
                artifactTitle={activeArtifact.title}
                artifactVersion={activeArtifact.version}
                registryName={activeArtifact.registryName}
                onClose={() => setActiveArtifact(null)}
                sidePaneMode
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* RIGHT: Chat pane */}
        <div className="flex-1 flex flex-col min-w-0">
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
            {(mode === "actions" || mode === "artifacts") && (
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
              {MODE_TITLES[mode]}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            {mode === "chat" && (
              <button
                type="button"
                onClick={() => switchMode("artifacts")}
                className="text-[9px] font-mono px-2 py-0.5 rounded border border-cyan-800/40 text-cyan-500/70 hover:text-cyan-400 hover:bg-cyan-950/30 transition-colors"
                title="Browse artifacts"
              >
                <Layers size={10} />
              </button>
            )}
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
                onClick={resetConversation}
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
              <div ref={scrollRef} className="flex-1 overflow-y-auto styled-scrollbar px-4 py-3 space-y-3 min-h-0">
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
                                  <span className={STEP_TYPE_COLORS[step.type] || "text-cyan-400/70"}>
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
                      {msg.action && renderChatActionChips(msg.action)}
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
              className="flex-1 overflow-y-auto styled-scrollbar min-h-0"
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
              className="flex-1 overflow-y-auto styled-scrollbar px-4 py-3 space-y-2 min-h-0"
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
                        {renderCoreChips(msg.action)}
                        {msg.action.artifact_id && (
                          <button type="button" onClick={(e) => { e.stopPropagation(); setActiveArtifact({ id: msg.action!.artifact_id!, title: msg.action!.artifact_title }); }} className={`${chipClass} border-purple-600/50 text-purple-300`}>
                            VIEW ARTIFACT
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

          {mode === "artifacts" && (
            <motion.div
              key="artifacts"
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.15 }}
              className="flex-1 overflow-y-auto styled-scrollbar min-h-0"
            >
              <ArtifactBrowser
                onSelect={(artifact) => {
                  setActiveArtifact({
                    id: `registry:${artifact.name}`,
                    title: artifact.title,
                    registryName: artifact.name,
                    version: artifact.version,
                  });
                  switchMode("chat");
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
        </div>{/* end chat pane */}
      </div>{/* end flex-row */}
    </motion.div>
  );
}
