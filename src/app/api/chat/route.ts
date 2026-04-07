import { NextRequest } from "next/server";
import OpenAI from "openai";

const meshClient = new OpenAI({
  baseURL: process.env.MESH_API_URL ?? "http://localhost:8000/v1",
  apiKey: process.env.MESH_API_KEY ?? "",
  // server-only — no dangerouslyAllowBrowser needed
});

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { model, messages } = body;

  console.log("[/api/chat] POST received", { model, messageCount: messages?.length });
  console.log("[/api/chat] Using baseURL:", process.env.MESH_API_URL ?? "http://localhost:8000/v1");

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      try {
        console.log("[/api/chat] Opening stream to upstream for model:", model);

        const completion = meshClient.chat.completions.stream({
          model,
          messages,
          stream: true,
        });

        let chunkCount = 0;
        for await (const chunk of completion) {
          chunkCount++;
          if (chunkCount <= 3) {
            console.log(`[/api/chat] chunk #${chunkCount}:`, JSON.stringify(chunk).slice(0, 120));
          }
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`)
          );
        }

        console.log(`[/api/chat] Stream complete. Total chunks: ${chunkCount}`);
        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      } catch (err) {
        console.error("[/api/chat] Stream error:", err);
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({ error: err instanceof Error ? err.message : String(err) })}\n\n`
          )
        );
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
