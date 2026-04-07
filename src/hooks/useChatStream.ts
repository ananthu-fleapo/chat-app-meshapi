import { useCallback } from "react";
import { useChatStore } from "@/store/chatStore";
import { useModels } from "@/hooks/useModels";
import type { ChatMessage, ResponseUsage } from "@/lib/types";

/**
 * Reads an SSE stream from /api/chat and calls onChunk/onUsage as data arrives.
 * The server proxies the upstream API, so no auth headers or upstream URL needed here.
 */
async function streamChat(
  modelId: string,
  messages: Array<{ role: "user" | "assistant"; content: string }>,
  onChunk: (delta: string) => void,
  onUsage: (usage: ResponseUsage) => void,
): Promise<void> {
  console.log("[streamChat] Sending to /api/chat:", { modelId, messageCount: messages.length });

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: modelId, messages }),
  });

  console.log("[streamChat] Response status:", res.status, res.statusText);

  if (!res.ok) throw new Error(`Chat API error: ${res.status} ${res.statusText}`);
  if (!res.body) throw new Error("No response body from /api/chat");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let totalChunks = 0;
  let totalDeltas = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      console.log(`[streamChat] Reader done. chunks=${totalChunks} deltas=${totalDeltas}`);
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by double newlines
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? ""; // keep any incomplete trailing event

    for (const part of parts) {
      for (const line of part.split("\n")) {
        if (!line.startsWith("data: ")) continue;

        const payload = line.slice(6).trim();
        if (payload === "[DONE]") {
          console.log(`[streamChat] [DONE] received. deltas=${totalDeltas}`);
          return;
        }

        let chunk: Record<string, unknown>;
        try {
          chunk = JSON.parse(payload);
        } catch {
          console.warn("[streamChat] Failed to parse SSE line:", line);
          continue;
        }

        totalChunks++;

        // API-level error — propagate so the UI shows the message
        if (chunk.error) throw new Error(chunk.error as string);

        const delta = (chunk.choices as Array<{ delta?: { content?: string } }>)?.[0]?.delta?.content;
        if (delta) {
          totalDeltas++;
          if (totalDeltas <= 3) console.log(`[streamChat] delta #${totalDeltas}:`, JSON.stringify(delta));
          onChunk(delta);
        }

        if (chunk.usage) {
          const u = chunk.usage as Record<string, unknown>;
          console.log("[streamChat] usage:", u);
          onUsage({
            prompt_tokens: (u.prompt_tokens as number) ?? 0,
            completion_tokens: (u.completion_tokens as number) ?? 0,
            total_tokens: (u.total_tokens as number) ?? 0,
            cost: u.cost as number | undefined,
          });
        }
      }
    }
  }
}

export function useChatStream() {
  const store = useChatStore();
  const { data: availableModels } = useModels();

  const sendMessage = useCallback(
    async (content: string) => {
      if (store.isStreaming) return;

      // Fall back to first available model if none are selected
      const effectiveModels =
        store.selectedModelIds.length > 0
          ? store.selectedModelIds
          : availableModels && availableModels.length > 0
          ? [availableModels[0].id]
          : ["openai/gpt-4o-mini"];

      let roomId = store.activeRoomId;
      if (!roomId) {
        roomId = store.createRoom();
      }

      const messageId = store.addUserMessage(content);
      store.setStreaming(true);

      // Snapshot history before the new message was added
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

      // Initialise response slots
      for (const modelId of effectiveModels) {
        store.initModelResponse(messageId, modelId);
      }

      // Fire all model streams in parallel
      const streamPromises = effectiveModels.map(async (modelId) => {
        let usage: ResponseUsage | undefined;
        try {
          await streamChat(
            modelId,
            apiMessages,
            (delta) => store.appendModelContent(messageId, modelId, delta),
            (u) => { usage = u; },
          );
          store.finalizeModelResponse(messageId, modelId, undefined, usage);
        } catch (err) {
          store.finalizeModelResponse(
            messageId,
            modelId,
            err instanceof Error ? err.message : "Unknown error",
          );
        }
      });

      await Promise.allSettled(streamPromises);
      store.setStreaming(false);
    },
    [store, availableModels],
  );

  return { sendMessage, isStreaming: store.isStreaming };
}
