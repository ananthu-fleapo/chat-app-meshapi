import { useCallback } from "react";
import { meshClient } from "@/lib/api";
import { useChatStore } from "@/store/chatStore";
import { useModels } from "@/hooks/useModels";
import type { ChatMessage, ResponseUsage } from "@/lib/types";

export function useChatStream() {
  const store = useChatStore();
  const { data: availableModels } = useModels();

  const sendMessage = useCallback(
    async (content: string) => {
      if (store.isStreaming) return;

      // Use selected models, or fall back to first available model
      const effectiveModels =
        store.selectedModelIds.length > 0
          ? store.selectedModelIds
          : availableModels && availableModels.length > 0
          ? [availableModels[0].id]
          : ["openai/gpt-4o-mini"];

      // Ensure there's an active room
      let roomId = store.activeRoomId;
      if (!roomId) {
        roomId = store.createRoom();
      }

      const messageId = store.addUserMessage(content);
      store.setStreaming(true);

      // Build the messages array for the API (use current state snapshot)
      const snapshot = useChatStore.getState();
      const activeRoom = snapshot.rooms.find((r) => r.id === roomId);
      const history: ChatMessage[] = activeRoom
        ? activeRoom.messages.filter((m) => m.id !== messageId)
        : [];

      const apiMessages = [
        ...history.flatMap((msg) => {
          const turns: Array<{ role: "user" | "assistant"; content: string }> = [
            { role: "user", content: msg.content },
          ];
          const firstResponse = Object.values(msg.responses).find((r) => r.content);
          if (firstResponse) {
            turns.push({ role: "assistant", content: firstResponse.content });
          }
          return turns;
        }),
        { role: "user" as const, content },
      ];

      // Initialize response slots for all effective models
      for (const modelId of effectiveModels) {
        store.initModelResponse(messageId, modelId);
      }

      // Fire all model streams in parallel
      const streamPromises = effectiveModels.map(async (modelId) => {
        try {
          const stream = meshClient.chat.completions.stream({
            model: modelId,
            messages: apiMessages,
            stream: true,
          });

          let usage: ResponseUsage | undefined;

          for await (const chunk of stream) {
            const delta = chunk.choices?.[0]?.delta?.content;
            if (delta) {
              // Plain store update — no flushSync (breaks React 19 concurrent renderer)
              store.appendModelContent(messageId, modelId, delta);
            }

            // Capture usage whenever the API sends it (overwrite with latest)
            if (chunk.usage) {
              usage = {
                prompt_tokens: chunk.usage.prompt_tokens ?? 0,
                completion_tokens: chunk.usage.completion_tokens ?? 0,
                total_tokens: chunk.usage.total_tokens ?? 0,
                cost: (chunk.usage as unknown as Record<string, unknown>).cost as number | undefined,
              };
            }
          }

          // Also try the SDK's finalUsage helper as a fallback
          if (!usage) {
            try {
              const finalMsg = await stream.finalMessage() as unknown as Record<string, unknown>;
              const u = finalMsg.usage as Record<string, number> | undefined;
              if (u) {
                usage = {
                  prompt_tokens: u.prompt_tokens ?? 0,
                  completion_tokens: u.completion_tokens ?? 0,
                  total_tokens: u.total_tokens ?? 0,
                };
              }
            } catch {
              // finalMessage may throw if stream already consumed — ignore
            }
          }

          store.finalizeModelResponse(messageId, modelId, undefined, usage);
        } catch (err) {
          const error = err instanceof Error ? err.message : "Unknown error";
          store.finalizeModelResponse(messageId, modelId, error);
        }
      });

      await Promise.allSettled(streamPromises);
      store.setStreaming(false);
    },
    [store, availableModels]
  );

  return { sendMessage, isStreaming: store.isStreaming };
}
