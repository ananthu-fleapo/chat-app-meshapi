import { NextRequest } from "next/server";
import OpenAI from "openai";

const MESH_API_URL = process.env.MESH_API_URL ?? "http://localhost:8000/v1";
const MESH_API_KEY = process.env.MESH_API_KEY ?? "";

const meshClient = new OpenAI({
  baseURL: MESH_API_URL,
  apiKey: MESH_API_KEY,
});

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { model, messages, modalities, audio, image } = body;

  console.log("[/api/chat] POST received", { model, messageCount: messages?.length, modalities, hasImage: !!image });

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const enqueue = (data: unknown) =>
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));

      try {
        // Audio output requires non-streaming (non-PCM16 formats are blocked in SSE)
        if (modalities?.includes("audio")) {
          console.log("[/api/chat] Audio output mode — using non-streaming");

          const completion = await meshClient.chat.completions.create({
            model,
            messages,
            modalities,
            audio: audio ?? { voice: "alloy", format: "mp3" },
            stream: false,
          } as Parameters<typeof meshClient.chat.completions.create>[0]);

          const chatCompletion = completion as unknown as OpenAI.Chat.ChatCompletion;
          const choice = chatCompletion.choices?.[0];
          const message = choice?.message as unknown as Record<string, unknown> | undefined;
          const textContent = typeof message?.content === "string" ? message.content : "";
          const audioPayload = message?.audio as Record<string, unknown> | undefined;

          if (textContent) {
            enqueue({ choices: [{ delta: { content: textContent } }] });
          }
          if (audioPayload?.data) {
            enqueue({
              audio: {
                data: audioPayload.data,
                format: audio?.format ?? "mp3",
                transcript: audioPayload.transcript ?? null,
              },
            });
          }
          if (chatCompletion.usage) {
            enqueue({ usage: chatCompletion.usage });
          }
        } else if (image) {
          // Image generation — non-streaming (imagen/dall-e return a single JSON response)
          console.log("[/api/chat] Image generation mode — using non-streaming");

          const upstream = await fetch(`${MESH_API_URL}/chat/completions`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${MESH_API_KEY}`,
            },
            body: JSON.stringify({ model, messages, image, stream: false }),
          });

          if (!upstream.ok) {
            const errText = await upstream.text().catch(() => upstream.statusText);
            throw new Error(`Upstream error ${upstream.status}: ${errText}`);
          }

          const json = await upstream.json() as Record<string, unknown>;
          console.log("[/api/chat] Image response:", JSON.stringify(json).slice(0, 300));

          const choices = json.choices as Array<Record<string, unknown>> | undefined;
          const msgContent = (choices?.[0]?.message as Record<string, unknown> | undefined)?.content;

          if (Array.isArray(msgContent)) {
            for (const part of msgContent) {
              const p = part as Record<string, unknown>;
              if (p?.type === "image_url") {
                const imgUrl = (p.image_url as Record<string, unknown>)?.url as string;
                if (imgUrl) enqueue({ image_url: imgUrl });
              }
            }
          }

          if (json.usage) enqueue({ usage: json.usage });

        } else {
          // Standard streaming path — raw SSE passthrough
          const upstream = await fetch(`${MESH_API_URL}/chat/completions`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${MESH_API_KEY}`,
            },
            body: JSON.stringify({ model, messages, stream: true }),
          });

          if (!upstream.ok) {
            const errText = await upstream.text().catch(() => upstream.statusText);
            throw new Error(`Upstream error ${upstream.status}: ${errText}`);
          }

          if (!upstream.body) throw new Error("No body from upstream");

          const reader = upstream.body.getReader();
          const dec = new TextDecoder();
          let buf = "";
          let chunkCount = 0;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buf += dec.decode(value, { stream: true });
            const parts = buf.split("\n\n");
            buf = parts.pop() ?? "";

            for (const part of parts) {
              for (const line of part.split("\n")) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6).trim();
                if (payload === "[DONE]") continue;

                let parsed: Record<string, unknown>;
                try { parsed = JSON.parse(payload); } catch { continue; }

                chunkCount++;
                if (chunkCount <= 3) {
                  console.log(`[/api/chat] upstream chunk #${chunkCount}:`, JSON.stringify(parsed).slice(0, 200));
                }

                controller.enqueue(encoder.encode(`data: ${JSON.stringify(parsed)}\n\n`));
              }
            }
          }

          console.log(`[/api/chat] Stream complete. upstream chunks: ${chunkCount}`);
        }

        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      } catch (err) {
        console.error("[/api/chat] error:", err);
        enqueue({ error: err instanceof Error ? err.message : String(err) });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
