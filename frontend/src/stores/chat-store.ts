import { create } from "zustand";
import type { SourceCitation } from "@/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  followUps?: string[];
  feedback?: number | null;
  streaming?: boolean;
}

interface ChatState {
  conversationId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  setConversationId: (id: string | null) => void;
  addMessage: (msg: ChatMessage) => void;
  updateLastAssistant: (content: string) => void;
  finishStream: (sources?: SourceCitation[], followUps?: string[]) => void;
  setStreaming: (v: boolean) => void;
  clearChat: () => void;
  setMessages: (msgs: ChatMessage[]) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversationId: null,
  messages: [],
  isStreaming: false,
  setConversationId: (id) => set({ conversationId: id }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastAssistant: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content };
      }
      return { messages: msgs };
    }),
  finishStream: (sources, followUps) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, streaming: false, sources, followUps };
      }
      return { messages: msgs, isStreaming: false };
    }),
  setStreaming: (v) => set({ isStreaming: v }),
  clearChat: () => set({ conversationId: null, messages: [], isStreaming: false }),
  setMessages: (msgs) => set({ messages: msgs }),
}));
