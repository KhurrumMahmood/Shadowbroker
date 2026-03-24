import { useState, useCallback } from "react";
import type {
  StoredConversation,
  ConversationSummary,
} from "@/types/aiConversation";

export const INDEX_KEY = "sb-ai-conv-index";
export const CONV_PREFIX = "sb-ai-conv-";
export const MAX_CONVERSATIONS = 50;
export const MAX_MESSAGES = 100;

export function loadIndex(): ConversationSummary[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(INDEX_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ConversationSummary[];
  } catch {
    return [];
  }
}

function saveIndex(index: ConversationSummary[]) {
  localStorage.setItem(INDEX_KEY, JSON.stringify(index));
}

export function saveConversation(conv: StoredConversation): void {
  // Trim messages if over cap
  const trimmed: StoredConversation = {
    ...conv,
    messages:
      conv.messages.length > MAX_MESSAGES
        ? conv.messages.slice(-MAX_MESSAGES)
        : conv.messages,
  };

  localStorage.setItem(`${CONV_PREFIX}${conv.id}`, JSON.stringify(trimmed));

  // Update index
  let index = loadIndex().filter((e) => e.id !== conv.id);
  index.push({
    id: conv.id,
    title: conv.title,
    updatedAt: conv.updatedAt,
    messageCount: trimmed.messages.length,
  });
  index.sort((a, b) => b.updatedAt - a.updatedAt);

  // Evict oldest if over cap
  while (index.length > MAX_CONVERSATIONS) {
    const evicted = index.pop()!;
    localStorage.removeItem(`${CONV_PREFIX}${evicted.id}`);
  }

  saveIndex(index);
}

export function loadConversation(id: string): StoredConversation | null {
  try {
    const raw = localStorage.getItem(`${CONV_PREFIX}${id}`);
    if (!raw) return null;
    return JSON.parse(raw) as StoredConversation;
  } catch {
    return null;
  }
}

export function deleteConversation(id: string): void {
  localStorage.removeItem(`${CONV_PREFIX}${id}`);
  const index = loadIndex().filter((e) => e.id !== id);
  saveIndex(index);
}

export function clearAllConversations(): void {
  const index = loadIndex();
  for (const entry of index) {
    localStorage.removeItem(`${CONV_PREFIX}${entry.id}`);
  }
  localStorage.removeItem(INDEX_KEY);
}

export function useConversationStore() {
  const [index, setIndex] = useState<ConversationSummary[]>(loadIndex);

  const save = useCallback((conv: StoredConversation) => {
    saveConversation(conv);
    setIndex(loadIndex());
  }, []);

  const load = useCallback((id: string) => {
    return loadConversation(id);
  }, []);

  const remove = useCallback((id: string) => {
    deleteConversation(id);
    setIndex(loadIndex());
  }, []);

  const clearAll = useCallback(() => {
    clearAllConversations();
    setIndex([]);
  }, []);

  return { index, save, load, remove, clearAll };
}
