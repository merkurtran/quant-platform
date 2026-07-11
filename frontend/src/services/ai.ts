import api from "@/lib/api";
import type { Conversation, AIMessage, SendMessageResponse } from "@/types";

export const aiService = {
  createConversation: () =>
    api.post<Conversation>("/ai/conversations", {}).then((r) => r.data),

  listConversations: () =>
    api.get<Conversation[]>("/ai/conversations").then((r) => r.data),

  listMessages: (conversationId: number, params?: { page?: number; page_size?: number }) =>
    api
      .get<AIMessage[]>(`/ai/conversations/${conversationId}/messages`, { params })
      .then((r) => r.data),

  sendMessage: (conversationId: number, content: string) =>
    api
      .post<SendMessageResponse>(`/ai/conversations/${conversationId}/messages`, {
        content,
      })
      .then((r) => r.data),
};
