"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, Plus, Loader2, MessageSquare, Bot } from "lucide-react";
import { aiService } from "@/services/ai";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import type { AIMessage, Conversation } from "@/types";

export function AIPanel() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [extraMessages, setExtraMessages] = useState<AIMessage[]>([]);
  const [convOpen, setConvOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: conversations } = useQuery({
    queryKey: ["conversations"],
    queryFn: aiService.listConversations,
  });

  const activeConversationId = activeId ?? conversations?.[0]?.id ?? null;

  const { data: messages, isLoading: msgLoading } = useQuery({
    queryKey: ["messages", activeConversationId],
    queryFn: () => aiService.listMessages(activeConversationId!),
    enabled: activeConversationId !== null,
  });

  const displayMessages = useMemo(
    () => [...(messages ?? []), ...extraMessages],
    [messages, extraMessages]
  );

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayMessages]);

  const createConvMutation = useMutation({
    mutationFn: () => aiService.createConversation(),
    onSuccess: (conv) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setExtraMessages([]);
      setActiveId(conv.id);
      setConvOpen(false);
    },
  });

  const sendMutation = useMutation({
    mutationFn: () => aiService.sendMessage(activeConversationId!, input),
    onSuccess: (res) => {
      setExtraMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          conversation_id: activeConversationId!,
          role: "user",
          content: { text: input },
          created_at: new Date().toISOString(),
        },
        {
          id: Date.now() + 1,
          conversation_id: activeConversationId!,
          role: "assistant",
          content: { text: res.content },
          created_at: new Date().toISOString(),
        },
      ]);
      setInput("");
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: () => {
      toast.error("消息发送失败，请重试");
    },
    onSettled: () => {
      setSending(false);
    },
  });

  const handleSend = () => {
    if (!input.trim() || !activeConversationId) return;
    setSending(true);
    sendMutation.mutate();
  };

  return (
    <div className="flex h-full flex-col">
      {/* 顶栏 */}
      <div className="flex h-10 items-center justify-between px-3">
        <button
          onClick={() => setConvOpen((v) => !v)}
          className="flex items-center gap-1.5 text-xs font-semibold"
        >
          <Bot className="h-3.5 w-3.5" />
          AI 助手
          <MessageSquare className="h-3 w-3 text-muted-foreground" />
        </button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => createConvMutation.mutate()}
          disabled={createConvMutation.isPending}
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* 对话列表（可折叠） */}
      {convOpen && (
        <div className="max-h-32 overflow-y-auto bg-muted/30">
          {conversations?.map((conv: Conversation) => (
            <button
              key={conv.id}
              onClick={() => {
                setExtraMessages([]);
                setActiveId(conv.id);
                setConvOpen(false);
              }}
              className={cn(
                "flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors",
                activeConversationId === conv.id
                  ? "bg-primary/10 text-primary"
                  : "hover:bg-secondary"
              )}
            >
              <MessageSquare className="h-3 w-3 shrink-0" />
              <span className="truncate">
                {conv.title ?? `对话 ${conv.id}`}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* 消息列表 */}
      <div
        ref={scrollRef}
        className="flex-1 space-y-2 overflow-y-auto p-3"
      >
        {activeConversationId === null ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <Bot className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-xs text-muted-foreground">
              新建对话开始与 AI 交流
            </p>
          </div>
        ) : msgLoading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          displayMessages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[85%] rounded-lg px-3 py-1.5 text-xs",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : msg.role === "tool"
                    ? "bg-muted text-muted-foreground"
                    : "bg-secondary"
                )}
              >
                {msg.role === "tool" ? (
                  <details>
                    <summary className="cursor-pointer text-[10px]">
                      工具: {msg.content.tool_name}
                    </summary>
                    <pre className="mt-1 whitespace-pre-wrap wrap-break-word text-[10px]">
                      {JSON.stringify(msg.content.tool_result, null, 2)}
                    </pre>
                  </details>
                ) : (
                  <p className="whitespace-pre-wrap wrap-break-word">
                    {msg.content.text}
                  </p>
                )}
              </div>
            </div>
          ))
        )}
        {sending && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-secondary px-3 py-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}
      </div>

      {/* 输入框 */}
      <div className="bg-muted/30 p-2">
        <div className="flex gap-1.5">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入消息..."
            className="min-h-9 max-h-24 resize-none text-xs"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            size="icon"
            className="h-9 shrink-0"
          >
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
