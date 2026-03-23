export interface StoredAction {
  layers?: Record<string, boolean>;
  viewport?: { lat: number; lng: number; zoom: number };
  filters?: Record<string, string[]>;
  result_entities?: Array<{ type: string; id: string | number }>;
  highlight_entities?: Array<{ type: string; id: string | number }>;
}

export interface StoredMessage {
  role: "user" | "assistant";
  content: string;
  action?: StoredAction;
  timestamp: number;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updatedAt: number;
  messageCount: number;
}

export interface StoredConversation {
  id: string;
  title: string;
  messages: StoredMessage[];
  createdAt: number;
  updatedAt: number;
}
