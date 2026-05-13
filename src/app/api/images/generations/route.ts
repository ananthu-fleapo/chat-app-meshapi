import { NextRequest } from "next/server";

const MESH_API_URL = process.env.MESH_API_URL ?? "http://localhost:8000/v1";
const MESH_API_KEY = process.env.MESH_API_KEY ?? "";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const streamRequested = !!body.stream;

  console.log("[/api/images/generations] POST received", { model: body.model, streamRequested });

  if (streamRequested) {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          console.log("[/api/images/generations] Sending request to MeshAPI:", `${MESH_API_URL}/images/generations`);
          const upstream = await fetch(`${MESH_API_URL}/images/generations`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${MESH_API_KEY}`,
            },
            body: JSON.stringify(body),
          });

          console.log("[/api/images/generations] MeshAPI response status:", upstream.status);

          if (!upstream.ok) {
            const errText = await upstream.text().catch(() => upstream.statusText);
            console.error("[/api/images/generations] MeshAPI error:", errText);
            throw new Error(`Upstream error ${upstream.status}: ${errText}`);
          }

          if (!upstream.body) {
            console.error("[/api/images/generations] No body from upstream");
            throw new Error("No body from upstream");
          }

          const reader = upstream.body.getReader();
          const dec = new TextDecoder();
          let buf = "";
          let chunkCount = 0;

          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              console.log("[/api/images/generations] Upstream stream finished");
              break;
            }

            buf += dec.decode(value, { stream: true });
            const parts = buf.split("\n\n");
            buf = parts.pop() ?? "";

            for (const part of parts) {
              for (const line of part.split("\n")) {
                if (line.startsWith(":")) {
                  // Keep-alive ping from MeshAPI
                  console.log("[/api/images/generations] Received ping");
                  controller.enqueue(encoder.encode(`${line}\n\n`));
                  continue;
                }
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6).trim();
                
                chunkCount++;
                console.log(`[/api/images/generations] Received data chunk #${chunkCount}:`, payload.slice(0, 100) + "...");

                if (payload === "[DONE]") {
                  console.log("[/api/images/generations] Received [DONE] marker");
                  controller.enqueue(encoder.encode("data: [DONE]\n\n"));
                  continue;
                }

                // Forward the data chunk
                controller.enqueue(encoder.encode(`data: ${payload}\n\n`));
              }
            }
          }
        } catch (err) {
          console.error("[/api/images/generations] error during streaming:", err);
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ error: err instanceof Error ? err.message : String(err) })}\n\n`));
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
  } else {
    // Non-streaming
    try {
      console.log("[/api/images/generations] Sending non-streaming request to MeshAPI");
      const upstream = await fetch(`${MESH_API_URL}/images/generations`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${MESH_API_KEY}`,
        },
        body: JSON.stringify(body),
      });

      console.log("[/api/images/generations] MeshAPI non-streaming status:", upstream.status);

      if (!upstream.ok) {
        const errText = await upstream.text().catch(() => upstream.statusText);
        console.error("[/api/images/generations] MeshAPI non-streaming error:", errText);
        return new Response(JSON.stringify({ error: `Upstream error ${upstream.status}: ${errText}` }), {
          status: upstream.status,
          headers: { "Content-Type": "application/json" },
        });
      }

      const data = await upstream.json();
      console.log("[/api/images/generations] Successfully received JSON response");
      return new Response(JSON.stringify(data), {
        headers: { "Content-Type": "application/json" },
      });
    } catch (err) {
      console.error("[/api/images/generations] error during non-streaming:", err);
      return new Response(JSON.stringify({ error: err instanceof Error ? err.message : String(err) }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  }
}
