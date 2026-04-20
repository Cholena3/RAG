"use client";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import { motion } from "framer-motion";
import { Copy, Check, ThumbsUp, ThumbsDown, User, Bot, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/stores/chat-store";

export function ChatMessage({ msg, onFollowUp }: { msg: ChatMessageType; onFollowUp?: (query: string) => void }) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(msg.feedback ?? null);
  const isUser = msg.role === "user";

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFeedback = async (value: number) => {
    setFeedback(value);
    try {
      await api.submitFeedback(msg.id, value);
    } catch { /* ignore */ }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-3 px-4 py-4", isUser ? "justify-end" : "")}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
          <Bot className="h-4 w-4 text-primary" />
        </div>
      )}
      <div className={cn("max-w-[75%] space-y-2", isUser ? "order-first" : "")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm",
            isUser
              ? "bg-primary text-primary-foreground ml-auto"
              : "bg-muted"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{msg.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                {msg.content}
              </ReactMarkdown>
              {msg.streaming && <span className="inline-block w-2 h-4 bg-foreground/50 animate-pulse ml-1" />}
            </div>
          )}
        </div>

        {/* Sources */}
        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {msg.sources.map((s, i) => (
              <Badge key={i} variant="secondary" className="gap-1 text-xs">
                <FileText className="h-3 w-3" />
                {s.document_name}
                {s.page_number && ` p.${s.page_number}`}
              </Badge>
            ))}
          </div>
        )}

        {/* Actions */}
        {!isUser && !msg.streaming && (
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 px-2" aria-label="Copy response">
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleFeedback(1)}
              className={cn("h-7 px-2", feedback === 1 && "text-green-600")}
              aria-label="Thumbs up"
            >
              <ThumbsUp className="h-3 w-3" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleFeedback(-1)}
              className={cn("h-7 px-2", feedback === -1 && "text-red-600")}
              aria-label="Thumbs down"
            >
              <ThumbsDown className="h-3 w-3" />
            </Button>
          </div>
        )}

        {/* Follow-up suggestions */}
        {!isUser && msg.followUps && msg.followUps.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {msg.followUps.map((q, i) => (
              <button
                key={i}
                onClick={() => onFollowUp?.(q)}
                className="text-xs border rounded-full px-3 py-1 hover:bg-accent transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
          <User className="h-4 w-4" />
        </div>
      )}
    </motion.div>
  );
}
