import { useCallback } from "react";
import { useChatStore } from "@/store/chatStore";
import { useModels } from "@/hooks/useModels";
import type { Attachment, ChatMessage, ContentPart, ResponseUsage } from "@/lib/types";

interface ImageOptions {
  n?: number;
  size?: string;
  quality?: string;
  response_format?: "url" | "b64_json";
}

interface StreamChatOptions {
  modalities?: string[];
  audio?: { voice: string; format: string };
  image?: ImageOptions;
}

interface StreamChatCallbacks {
  onChunk: (delta: string) => void;
  onUsage: (usage: ResponseUsage) => void;
  onAudio?: (data: string, format: string) => void;
  onImageUrl?: (url: string) => void;
}

async function streamChat(
  modelId: string,
  messages: Array<{ role: "user" | "assistant"; content: unknown }>,
  callbacks: StreamChatCallbacks,
  options: StreamChatOptions = {},
): Promise<void> {
  console.log("[streamChat] Sending to /api/chat:", { modelId, messageCount: messages.length, options });

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: modelId, messages, ...options }),
  });

  if (!res.ok) throw new Error(`Chat API error: ${res.status} ${res.statusText}`);
  if (!res.body) throw new Error("No response body from /api/chat");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      for (const line of part.split("\n")) {
        if (!line.startsWith("data: ")) continue;

        const payload = line.slice(6).trim();
        if (payload === "[DONE]") return;

        let chunk: Record<string, unknown>;
        try {
          chunk = JSON.parse(payload);
        } catch {
          console.warn("[streamChat] Failed to parse SSE line:", line);
          continue;
        }

        if (chunk.error) throw new Error(chunk.error as string);

        // Text/Image delta
        const deltaObj = (chunk.choices as Array<{ delta?: { content?: unknown } }>)?.[0]?.delta;
        if (deltaObj?.content) {
          if (typeof deltaObj.content === "string") {
            callbacks.onChunk(deltaObj.content);
          } else if (Array.isArray(deltaObj.content)) {
            for (const part of deltaObj.content) {
              if (part?.type === "text" && typeof part.text === "string") {
                callbacks.onChunk(part.text);
              } else if (part?.type === "image_url" && typeof part.image_url?.url === "string") {
                if (callbacks.onImageUrl) {
                  callbacks.onImageUrl(part.image_url.url);
                }
              }
            }
          }
        }

        // Audio response (non-streaming path)
        if (chunk.audio) {
          const a = chunk.audio as { data?: string; format?: string };
          if (a.data && callbacks.onAudio) {
            callbacks.onAudio(a.data, a.format ?? "mp3");
          }
        }

        // Image URL (image generation)
        if (chunk.image_url && callbacks.onImageUrl) {
          callbacks.onImageUrl(chunk.image_url as string);
        }

        // Usage
        if (chunk.usage) {
          const u = chunk.usage as Record<string, unknown>;
          callbacks.onUsage({
            prompt_tokens: (u.prompt_tokens as number) ?? 0,
            completion_tokens: (u.completion_tokens as number) ?? 0,
            total_tokens: (u.total_tokens as number) ?? 0,
            cost: u.cost as number | undefined,
            images_generated: u.images_generated as number | undefined,
            cost_usd: u.cost_usd as number | undefined,
          });
        }
      }
    }
  }
}

const IMAGE_GEN_PATTERNS = ["dall-e", "imagen", "gpt-image", "gpt-5-image", "flux", "stable-diffusion"];
const AUDIO_MODEL_PATTERNS = ["audio", "tts", "whisper"];
const IMAGE_FILE_EXTENSIONS = new Set([
  "png",
  "jpg",
  "jpeg",
  "gif",
  "webp",
  "bmp",
  "svg",
  "avif",
  "tiff",
  "tif",
]);

function isImageGenModel(modelId: string): boolean {
  const lower = modelId.toLowerCase();
  return IMAGE_GEN_PATTERNS.some((p) => lower.includes(p));
}

function isAudioModel(modelId: string): boolean {
  const lower = modelId.toLowerCase();
  return AUDIO_MODEL_PATTERNS.some((p) => lower.includes(p));
}

function normalizeUrlCandidate(value: string): string {
  return value.replace(/[),.;!?]+$/, "");
}

function isLikelyImageUrl(value: string): boolean {
  if (value.startsWith("data:image/")) return true;

  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol)) return false;

    const lastSegment = url.pathname.split("/").pop() ?? "";
    const extension = lastSegment.split(".").pop()?.toLowerCase();
    return !!extension && IMAGE_FILE_EXTENSIONS.has(extension);
  } catch {
    return false;
  }
}

function extractInlineImageUrls(text: string): { cleanText: string; imageUrls: string[] } {
  const imageUrls: string[] = [];
  const seen = new Set<string>();
  let cleanText = text;

  cleanText = cleanText.replace(/!\[[^\]]*]\(([^)\s]+)\)/g, (match, url: string) => {
    const normalized = normalizeUrlCandidate(url);
    if (!seen.has(normalized) && isLikelyImageUrl(normalized)) {
      seen.add(normalized);
      imageUrls.push(normalized);
      return "";
    }
    return match;
  });

  cleanText = cleanText.replace(/https?:\/\/[^\s<>"')]+/g, (match) => {
    const normalized = normalizeUrlCandidate(match);
    if (!seen.has(normalized) && isLikelyImageUrl(normalized)) {
      seen.add(normalized);
      imageUrls.push(normalized);
      return "";
    }
    return match;
  });

  cleanText = cleanText.replace(/\n{3,}/g, "\n\n").trim();

  return { cleanText, imageUrls };
}

function buildContentParts(text: string, attachments: Attachment[]): ContentPart[] {
  const parts: ContentPart[] = [];
  const { cleanText, imageUrls } = extractInlineImageUrls(text);

  if (cleanText) {
    parts.push({ type: "text", text: cleanText });
  }

  for (const imageUrl of imageUrls) {
    parts.push({ type: "image_url", image_url: { url: imageUrl } });
  }

  for (const attachment of attachments) {
    if (attachment.type === "image") {
      parts.push({ type: "image_url", image_url: { url: attachment.data } });
    } else if (attachment.type === "audio") {
      // Extract base64 from data URL: "data:<mime>;base64,<data>"
      const base64 = attachment.data.split(",")[1] ?? attachment.data;
      const format = attachment.mimeType.split("/")[1]?.split(";")[0] ?? "mp3";
      parts.push({ type: "input_audio", input_audio: { data: base64, format } });
    }
  }

  return parts;
}

function contentPartsToApiMessages(
  history: ChatMessage[],
  newContent: string | ContentPart[],
) {
  return [
    ...history.flatMap((msg) => {
      const userContent = typeof msg.content === "string"
        ? msg.content
        : msg.content;
      const turns: Array<{ role: "user" | "assistant"; content: unknown }> = [
        { role: "user", content: userContent },
      ];
      const firstResponse = Object.values(msg.responses).find((r) => r.content);
      if (firstResponse) {
        turns.push({ role: "assistant", content: firstResponse.content });
      }
      return turns;
    }),
    { role: "user" as const, content: newContent },
  ];
}

export function useChatStream() {
  const store = useChatStore();
  const { data: availableModels } = useModels();

  const sendMessage = useCallback(
    async (text: string, attachments: Attachment[] = [], requestAudio = false) => {
      if (store.isStreaming) return;

      const effectiveModels =
        store.selectedModelIds.length > 0
          ? store.selectedModelIds
          : availableModels && availableModels.length > 0
          ? [availableModels[0].id]
          : ["openai/gpt-4o-mini"];

      let roomId = store.activeRoomId;
      if (!roomId) roomId = store.createRoom();

      const messageParts = buildContentParts(text, attachments);
      const messageContent: string | ContentPart[] = messageParts.length === 1 && messageParts[0]?.type === "text"
        ? messageParts[0].text
        : messageParts;

      const messageId = store.addUserMessage(messageContent);
      store.setStreaming(true);

      const snapshot = useChatStore.getState();
      const activeRoom = snapshot.rooms.find((r) => r.id === roomId);
      const history: ChatMessage[] = activeRoom
        ? activeRoom.messages.filter((m) => m.id !== messageId)
        : [];

      const apiMessages = contentPartsToApiMessages(history, messageContent);

      const options: StreamChatOptions = {};
      if (requestAudio) {
        options.modalities = ["text", "audio"];
        options.audio = { voice: "alloy", format: "mp3" };
      }

      for (const modelId of effectiveModels) {
        store.initModelResponse(messageId, modelId);
      }

      const streamPromises = effectiveModels.map(async (modelId) => {
        // Build per-model options
        const modelOptions: StreamChatOptions = { ...options };
        if (isImageGenModel(modelId)) {
          modelOptions.image = { n: 1, size: "1024x1024", quality: "high", response_format: "b64_json" };
        }
        // Audio models always require modalities: ["text", "audio"]
        if (isAudioModel(modelId) && !modelOptions.modalities?.includes("audio")) {
          modelOptions.modalities = ["text", "audio"];
          if (!modelOptions.audio) modelOptions.audio = { voice: "alloy", format: "mp3" };
        }

        let usage: ResponseUsage | undefined;
        try {
          await streamChat(
            modelId,
            apiMessages,
            {
              onChunk: (delta) => store.appendModelContent(messageId, modelId, delta),
              onUsage: (u) => { usage = u; },
              onAudio: (data, format) => store.setModelAudio(messageId, modelId, data, format),
              onImageUrl: (url) => store.appendModelImageUrl(messageId, modelId, url),
            },
            modelOptions,
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
