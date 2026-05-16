import { NextRequest } from "next/server";

const MESH_API_URL = process.env.MESH_API_URL ?? "http://localhost:8000/v1";
const MESH_API_KEY = process.env.MESH_API_KEY ?? "";
const LOG_PREVIEW_LIMIT = 500;

function logUpstreamResponse(label: string, response: Response) {
  console.log(`[/api/chat] ${label} status`, {
    status: response.status,
    statusText: response.statusText,
    contentType: response.headers.get("content-type"),
    transferEncoding: response.headers.get("transfer-encoding"),
  });
}

function previewValue(value: unknown, limit = LOG_PREVIEW_LIMIT): string {
  const raw = typeof value === "string" ? value : JSON.stringify(value);
  return raw.length > limit ? `${raw.slice(0, limit)}...` : raw;
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { model, messages, modalities, audio, image } = body;

  console.log("[/api/chat] POST received", {
    model,
    messageCount: messages?.length,
    modalities,
    hasImage: !!image,
    messagePreview: previewValue(messages, 800),
  });

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const enqueue = (data: unknown) =>
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));

      try {
        // Audio output requires non-streaming (non-PCM16 formats are blocked in SSE)
        if (modalities?.includes("audio")) {
          console.log("[/api/chat] Audio output mode — using non-streaming");

          const upstream = await fetch(`${MESH_API_URL}/chat/completions`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${MESH_API_KEY}`,
            },
            body: JSON.stringify({
              model,
              messages,
              modalities,
              audio: audio ?? { voice: "alloy", format: "mp3" },
              stream: false,
            }),
          });
          logUpstreamResponse("Audio upstream", upstream);

          if (!upstream.ok) {
            const errText = await upstream.text().catch(() => upstream.statusText);
            throw new Error(`Upstream error ${upstream.status}: ${errText}`);
          }

          const json = await upstream.json() as Record<string, unknown>;
          console.log("[/api/chat] Audio response preview:", previewValue(json));

          const choices = json.choices as Array<Record<string, unknown>> | undefined;
          const message = choices?.[0]?.message as Record<string, unknown> | undefined;
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
          if (json.usage) {
            enqueue({ usage: json.usage });
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
          logUpstreamResponse("Image upstream", upstream);

          if (!upstream.ok) {
            const errText = await upstream.text().catch(() => upstream.statusText);
            throw new Error(`Upstream error ${upstream.status}: ${errText}`);
          }

          const json = await upstream.json() as Record<string, unknown>;
          console.log("[/api/chat] Image response preview:", previewValue(json));

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
          // Standard streaming path — raw OpenAI-compatible SSE passthrough
          const upstream = await fetch(`${MESH_API_URL}/chat/completions`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${MESH_API_KEY}`,
            },
            body: JSON.stringify({ model, messages, stream: true }),
          });
          logUpstreamResponse("Streaming upstream", upstream);

          if (!upstream.ok) {
            const errText = await upstream.text().catch(() => upstream.statusText);
            
            // Fallback for audio models that require audio modalities
            if (errText.includes("This model requires that either input content or output modality contain audio.")) {
              console.log("[/api/chat] Detected audio model error in streaming path, retrying non-streaming with audio modalities");
              
              const retryUpstream = await fetch(`${MESH_API_URL}/chat/completions`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  Authorization: `Bearer ${MESH_API_KEY}`,
                },
                body: JSON.stringify({
                  model,
                  messages,
                  modalities: ["text", "audio"],
                  audio: audio ?? { voice: "alloy", format: "mp3" },
                  stream: false,
                }),
              });
              
              logUpstreamResponse("Retry Audio upstream", retryUpstream);

              if (!retryUpstream.ok) {
                const retryErrText = await retryUpstream.text().catch(() => retryUpstream.statusText);
                throw new Error(`Upstream error ${retryUpstream.status}: ${retryErrText}`);
              }

              const json = await retryUpstream.json() as Record<string, unknown>;
              console.log("[/api/chat] Retry Audio response preview:", previewValue(json));

              const choices = json.choices as Array<Record<string, unknown>> | undefined;
              const message = choices?.[0]?.message as Record<string, unknown> | undefined;
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
              if (json.usage) {
                enqueue({ usage: json.usage });
              }
              
              controller.enqueue(encoder.encode("data: [DONE]\n\n"));
              return;
            }
            
            throw new Error(`Upstream error ${upstream.status}: ${errText}`);
          }

          if (!upstream.body) throw new Error("No body from upstream");

          const reader = upstream.body.getReader();
          const dec = new TextDecoder();
          let readCount = 0;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            readCount++;

            const decodedChunk = dec.decode(value, { stream: true });
            console.log(`[/api/chat] upstream read #${readCount}:`, previewValue(decodedChunk));
            controller.enqueue(value);
          }

          console.log(`[/api/chat] Stream complete. upstream reads: ${readCount}`);
          return;
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
