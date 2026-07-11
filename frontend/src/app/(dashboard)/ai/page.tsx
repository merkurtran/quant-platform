"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bot, Send, Plus, Loader2, MessageSquare } from "lucide-react";
import { aiService } from "@/services/ai";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/layout/empty-state";
import { cn } from "@/lib/utils";
import type { AIMessage, Conversation } from "@/types";

export default function AIPage() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [extraMessages, setExtraMessages] = useState<AIMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: conversations } = useQuery({
    queryKey: ["conversations"],
    queryFn: aiService.listConversations,
  });

  const { data: messages, isLoading: msgLoading } = useQuery({
    queryKey: ["messages", activeId],
    queryFn: () => aiService.listMessages(activeId!),
    enabled: activeId !== null,
  });

  // 合并服务端消息和本地追加的消息
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
      setActiveId(conv.id);
    },
  });

  const sendMutation = useMutation({
    mutationFn: () => aiService.sendMessage(activeId!, input),
    onSuccess: (res) => {
      // 添加用户消息 + AI 回复到本地
      setExtraMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          conversation_id: activeId!,
          role: "user",
          content: { text: input },
          created_at: new Date().toISOString(),
        },
        {
          id: Date.now() + 1,
          conversation_id: activeId!,
          role: "assistant",
          content: { text: res.content },
          created_at: new Date().toISOString(),
        },
      ]);
      setInput("");
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: () => {
      setSending(false);
    },
    onSettled: () => {
      setSending(false);
    },
  });

  const handleSend = () => {
    if (!input.trim() || !activeId) return;
    setSending(true);
    sendMutation.mutate();
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-4">
      {/* 对话列表 */}
      <div className="w-64 shrink-0 space-y-2 overflow-y-auto">
        <Button
          className="w-full"
          onClick={() => createConvMutation.mutate()}
          disabled={createConvMutation.isPending}
        >
          <Plus className="h-4 w-4" />
          新建对话
        </Button>
        {conversations?.map((conv: Conversation) => (
          <button
            key={conv.id}
            onClick={() => setActiveId(conv.id)}
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
              activeId === conv.id
                ? "bg-primary/10 text-primary"
                : "hover:bg-secondary text-muted-foreground"
            )}
          >
            <MessageSquare className="h-4 w-4 shrink-0" />
            <span className="truncate">
              {conv.title ?? `对话 ${conv.id}`}
            </span>
          </button>
        ))}
      </div>

      {/* 聊天区 */}
      <div className="flex flex-1 flex-col">
        {activeId === null ? (
          <Card className="flex flex-1 items-center justify-center">
            <EmptyState
              icon={Bot}
              title="AI 量化助手"
              description="新建一个对话，开始与 AI 助手交流。可以生成策略代码、解读回测结果、查询持仓。"
              action={
                <Button
                  onClick={() => createConvMutation.mutate()}
                  disabled={createConvMutation.isPending}
                >
                  <Plus className="h-4 w-4" />
                  新建对话
                </Button>
              }
            />
          </Card>
        ) : (
          <>
            {/* 消息列表 */}
            <div
              ref={scrollRef}
              className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-border bg-background p-4"
            >
              {msgLoading ? (
                <div className="flex h-full items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
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
                        "max-w-[70%] rounded-lg px-4 py-2 text-sm",
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : msg.role === "tool"
                          ? "bg-secondary text-muted-foreground text-xs"
                          : "bg-secondary"
                      )}
                    >
                      {msg.role === "tool" ? (
                        <details>
                          <summary className="cursor-pointer">
                            工具调用: {msg.content.tool_name}
                          </summary>
                          <pre className="mt-2 whitespace-pre-wrap break-all">
                            {JSON.stringify(msg.content.tool_result, null, 2)}
                          </pre>
                        </details>
                      ) : (
                        <p className="whitespace-pre-wrap break-words">
                          {msg.content.text}
                        </p>
                      )}
                    </div>
                  </div>
                ))
              )}
              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-lg bg-secondary px-4 py-2">
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  </div>
                </div>
              )}
            </div>

            {/* 输入框 */}
            <div className="mt-4 flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="输入消息...（Shift+Enter 换行）"
                className="min-h-[44px] max-h-32 resize-none"
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
                className="h-auto"
              >
                {sending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
