"use client";
import { useEffect, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { MessageSquare } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessage } from "./chat-message";
import { ChatInput } from "./chat-input";
import { useChatStore } from "@/stores/chat-store";
import { api } from "@/lib/api";
import type { SourceCitation } from "@/types";

export function ChatPanel() {
  const searchParams = useSearchParams();
  const convId = searchParams.get("c");
  const bottomRef = useRef<HTMLDivElement>(null);
  const {
    conversationId, messages, setConversationId, addMessage,
    updateLastAssistant, finishStream, setStreaming, clearChat, setMessages,
  } = useChatStore();

  // Load conversation from URL
  useEffect(() => {
    if (convId && convId !== conversationId) {
      (async () => {
        try {
          const conv = await api.getConversation(convId);
          setConversationId(conv.id);
          setMessages(
            conv.messages.map((m) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              sources: m.sources ? JSON.parse(m.sources) : undefined,
              feedback: m.feedback,
            }))
          );
        } catch {
          clearChat();
        }
      })();
    } else if (!convId) {
      clearChat();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [convId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async (query: string) => {
    const userMsgId = crypto.randomUUID();
    addMessage({ id: userMsgId, role: "user", content: query });
    addMessage({ id: crypto.randomUUID(), role: "assistant", content: "", streaming: true });
    setStreaming(true);

    try {
      const res = await api.chatStream(query, conversationId || undefined);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = "";
      let sources: SourceCitation[] = [];

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            const eventType = line.slice(7).trim();
            continue;
          }
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            // Try to parse as JSON for sources/done events
            try {
              const parsed = JSON.parse(data);
              if (Array.isArray(parsed)) {
                sources = parsed;
              } else if (parsed.content) {
                fullContent = parsed.content;
              }
            } catch {
              // It's a token
              fullContent += data;
              updateLastAssistant(fullContent);
            }
          }
        }
      }

      // Extract conversation ID from first response if new
      if (!conversationId) {
        // Re-fetch conversations to get the new one
        const convs = await api.listConversations(0, 1);
        if (convs.conversations.length > 0) {
          setConversationId(convs.conversations[0].id);
        }
      }

      finishStream(sources);
    } catch (err) {
      updateLastAssistant("Sorry, something went wrong. Please try again.");
      finishStream();
    }
  }, [conversationId, addMessage, updateLastAssistant, finishStream, setStreaming, setConversationId]);

  return (
    <div className="flex flex-col h-full">
      {messages.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
              <MessageSquare className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-2xl font-semibold">DocMind</h2>
            <p className="text-muted-foreground max-w-md">
              Upload documents and ask questions. Get accurate, cited answers powered by your local LLM.
            </p>
          </div>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <div className="max-w-3xl mx-auto py-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} msg={msg} onFollowUp={handleSend} />
            ))}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      )}
      <ChatInput onSend={handleSend} />
    </div>
  );
}
