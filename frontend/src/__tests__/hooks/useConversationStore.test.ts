import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  loadIndex,
  saveConversation,
  loadConversation,
  deleteConversation,
  clearAllConversations,
  INDEX_KEY,
  CONV_PREFIX,
  MAX_CONVERSATIONS,
  MAX_MESSAGES,
} from "@/hooks/useConversationStore";
import type { StoredConversation, ConversationSummary } from "@/types/aiConversation";

function makeConversation(id: string, title: string, msgCount = 2, updatedAt = Date.now()): StoredConversation {
  const messages = Array.from({ length: msgCount }, (_, i) => ({
    role: (i % 2 === 0 ? "user" : "assistant") as "user" | "assistant",
    content: `msg ${i}`,
    timestamp: updatedAt - (msgCount - i) * 1000,
  }));
  return { id, title, messages, createdAt: updatedAt - 100000, updatedAt };
}

describe("conversation store", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("loadIndex", () => {
    it("returns empty array when nothing stored", () => {
      expect(loadIndex()).toEqual([]);
    });

    it("returns parsed index", () => {
      const idx: ConversationSummary[] = [
        { id: "a", title: "Hello", updatedAt: 1000, messageCount: 3 },
      ];
      localStorage.setItem(INDEX_KEY, JSON.stringify(idx));
      expect(loadIndex()).toEqual(idx);
    });

    it("returns empty array on corrupt JSON", () => {
      localStorage.setItem(INDEX_KEY, "not json{{{");
      expect(loadIndex()).toEqual([]);
    });
  });

  describe("saveConversation", () => {
    it("saves conversation body and updates index", () => {
      const conv = makeConversation("c1", "First chat");
      saveConversation(conv);

      const body = JSON.parse(localStorage.getItem(`${CONV_PREFIX}c1`)!);
      expect(body.id).toBe("c1");
      expect(body.title).toBe("First chat");

      const idx = loadIndex();
      expect(idx).toHaveLength(1);
      expect(idx[0].id).toBe("c1");
      expect(idx[0].messageCount).toBe(2);
    });

    it("updates existing conversation in index without duplicating", () => {
      const conv1 = makeConversation("c1", "Chat", 2, 1000);
      saveConversation(conv1);
      const conv1b = makeConversation("c1", "Chat", 4, 2000);
      saveConversation(conv1b);

      const idx = loadIndex();
      expect(idx).toHaveLength(1);
      expect(idx[0].messageCount).toBe(4);
      expect(idx[0].updatedAt).toBe(2000);
    });

    it("sorts index by updatedAt descending", () => {
      saveConversation(makeConversation("old", "Old", 1, 1000));
      saveConversation(makeConversation("new", "New", 1, 3000));
      saveConversation(makeConversation("mid", "Mid", 1, 2000));

      const idx = loadIndex();
      expect(idx.map(e => e.id)).toEqual(["new", "mid", "old"]);
    });

    it("evicts oldest when exceeding MAX_CONVERSATIONS", () => {
      for (let i = 0; i < MAX_CONVERSATIONS; i++) {
        saveConversation(makeConversation(`c${i}`, `Chat ${i}`, 1, i * 1000));
      }
      expect(loadIndex()).toHaveLength(MAX_CONVERSATIONS);

      // Add one more — oldest (c0) should be evicted
      saveConversation(makeConversation("overflow", "Overflow", 1, MAX_CONVERSATIONS * 1000));
      const idx = loadIndex();
      expect(idx).toHaveLength(MAX_CONVERSATIONS);
      expect(idx.find(e => e.id === "c0")).toBeUndefined();
      expect(idx[0].id).toBe("overflow");
      // Evicted conversation body should be removed
      expect(localStorage.getItem(`${CONV_PREFIX}c0`)).toBeNull();
    });

    it("trims messages to MAX_MESSAGES keeping most recent", () => {
      const conv = makeConversation("big", "Big", MAX_MESSAGES + 20);
      saveConversation(conv);

      const loaded = loadConversation("big");
      expect(loaded!.messages).toHaveLength(MAX_MESSAGES);
      // Should keep the last MAX_MESSAGES (most recent)
      expect(loaded!.messages[MAX_MESSAGES - 1].content).toBe(`msg ${MAX_MESSAGES + 19}`);
    });
  });

  describe("loadConversation", () => {
    it("returns null for nonexistent conversation", () => {
      expect(loadConversation("nope")).toBeNull();
    });

    it("returns null on corrupt JSON", () => {
      localStorage.setItem(`${CONV_PREFIX}bad`, "{{garbage");
      expect(loadConversation("bad")).toBeNull();
    });

    it("round-trips a saved conversation", () => {
      const conv = makeConversation("rt", "Round Trip", 5);
      saveConversation(conv);
      const loaded = loadConversation("rt");
      expect(loaded).not.toBeNull();
      expect(loaded!.id).toBe("rt");
      expect(loaded!.title).toBe("Round Trip");
      expect(loaded!.messages).toHaveLength(5);
    });
  });

  describe("deleteConversation", () => {
    it("removes conversation from index and localStorage", () => {
      saveConversation(makeConversation("d1", "Delete me"));
      saveConversation(makeConversation("d2", "Keep me"));
      expect(loadIndex()).toHaveLength(2);

      deleteConversation("d1");
      expect(loadIndex()).toHaveLength(1);
      expect(loadIndex()[0].id).toBe("d2");
      expect(localStorage.getItem(`${CONV_PREFIX}d1`)).toBeNull();
    });

    it("is a no-op for nonexistent id", () => {
      saveConversation(makeConversation("k1", "Keep"));
      deleteConversation("nonexistent");
      expect(loadIndex()).toHaveLength(1);
    });
  });

  describe("clearAllConversations", () => {
    it("removes all conversations and the index", () => {
      saveConversation(makeConversation("x1", "One"));
      saveConversation(makeConversation("x2", "Two"));
      expect(loadIndex()).toHaveLength(2);

      clearAllConversations();
      expect(loadIndex()).toEqual([]);
      expect(localStorage.getItem(`${CONV_PREFIX}x1`)).toBeNull();
      expect(localStorage.getItem(`${CONV_PREFIX}x2`)).toBeNull();
    });
  });
});
