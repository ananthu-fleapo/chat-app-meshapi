"use client";

import { useRef, useEffect, useState } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ProviderAvatar } from "@/components/ui/ProviderAvatar";
import { useModels } from "@/hooks/useModels";
import { useChatStore } from "@/store/chatStore";
import type { ModelResponseState } from "@/lib/types";

interface Props {
  messageId: string;
  modelId: string;
  response: ModelResponseState;
}

function formatCost(cost: number): string {
  if (cost === 0) return "$0";
  if (cost < 0.000001) return `$${cost.toExponential(2)}`;
  if (cost < 0.01) return `$${cost.toFixed(7).replace(/0+$/, "")}`;
  return `$${cost.toFixed(4)}`;
}

/**
 * Smooth typewriter for LIVE streaming responses.
 *
 * Key insight: Zustand's subscribe() fires SYNCHRONOUSLY on every set() call,
 * before React has a chance to batch anything. We use this to update a ref
 * directly on each chunk arrival. A requestAnimationFrame loop then advances
 * a `displayed` string toward that ref at a fixed rate (~60fps × 3 chars =
 * ~180 chars/sec). React only re-renders when setDisplayed() is called from
 * the rAF loop — completely decoupled from chunk arrival speed.
 */
function StreamingTypewriter({
  messageId,
  modelId,
}: {
  messageId: string;
  modelId: string;
}) {
  const [displayed, setDisplayed] = useState("");
  const contentRef = useRef(""); // updated synchronously by Zustand subscribe
  const frameRef = useRef<number | null>(null);

  // Subscribe to Zustand synchronously — fires before React batches anything
  useEffect(() => {
    const unsubscribe = useChatStore.subscribe((state) => {
      const room = state.rooms.find((r) => r.id === state.activeRoomId);
      const msg = room?.messages.find((m) => m.id === messageId);
      contentRef.current = msg?.responses[modelId]?.content ?? "";
    });
    return unsubscribe;
  }, [messageId, modelId]);

  // rAF loop — show all available content each frame (~16ms delay max)
  // The 60fps cadence is the smoothing; no artificial char-per-frame throttle
  useEffect(() => {
    const tick = () => {
      const latest = contentRef.current;
      setDisplayed((prev) => (prev !== latest ? latest : prev));
      frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, []);

  return (
    <div className="prose prose-sm max-w-none text-gray-800">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>
        {displayed || " "}
      </ReactMarkdown>
    </div>
  );
}

export function ModelResponse({ messageId, modelId, response }: Props) {
  const { data: models } = useModels();
  const modelName = models?.find((m) => m.id === modelId)?.name ?? modelId;

  // Track whether done was true at mount:
  // true  → history entry (loaded from localStorage) → TypeAnimation replay
  // false → live streamed this session → StreamingTypewriter
  const wasAlreadyDoneOnMount = useRef(response.done);

  const isHistory = wasAlreadyDoneOnMount.current;
  const isLive = !isHistory; // streamed in this session

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="py-3"
    >
      {/* Model header */}
      <div className="flex items-center gap-2 mb-2">
        <ProviderAvatar modelId={modelId} size={22} />
        <span className="text-sm font-semibold text-gray-700">{modelName}</span>
        {/* Dots only while waiting for the first chunk */}
        {isLive && !response.done && !response.content && !response.error && (
          <span className="flex gap-0.5 ml-1">
            {[0, 1, 2].map((i) => (
              <motion.span
                key={i}
                className="w-1 h-1 bg-gray-400 rounded-full"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
              />
            ))}
          </span>
        )}
      </div>

      {/* Response content */}
      <div className="pl-8">
        {response.error ? (
          <div className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded-lg border border-red-100">
            {response.error}
          </div>
        ) : (
          <>
            {/* LIVE: StreamingTypewriter subscribes directly to Zustand,
                bypasses React batching → smooth character-by-character animation.
                Shown for the entire live session (streaming + after done). */}
            {isLive && (
              <StreamingTypewriter messageId={messageId} modelId={modelId} />
            )}

            {/* HISTORY: render instantly, no animation */}
            {isHistory && response.content && (
              <div className="prose prose-sm max-w-none text-gray-800">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>
                  {response.content}
                </ReactMarkdown>
              </div>
            )}

            {/* Usage footer — shown after completion */}
            {response.done && response.usage && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: 0.1 }}
                className="flex items-center gap-3 mt-3 pt-2 border-t border-gray-100"
              >
                <span className="text-xs text-gray-400 flex items-center gap-1">
                  <span className="text-gray-300">↑</span>
                  {response.usage.prompt_tokens.toLocaleString()}
                </span>
                <span className="text-xs text-gray-400 flex items-center gap-1">
                  <span className="text-gray-300">↓</span>
                  {response.usage.completion_tokens.toLocaleString()}
                </span>
                <span className="text-xs text-gray-400">
                  {response.usage.total_tokens.toLocaleString()} tokens
                </span>
                {response.usage.cost !== undefined && response.usage.cost > 0 && (
                  <>
                    <span className="text-gray-200">·</span>
                    <span className="text-xs text-gray-400">
                      {formatCost(response.usage.cost)}
                    </span>
                  </>
                )}
              </motion.div>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
}

function CodeBlock({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLElement>) {
  const match = /language-(\w+)/.exec(className ?? "");
  const isBlock = match !== null;
  return isBlock ? (
    <SyntaxHighlighter
      style={oneLight as Record<string, React.CSSProperties>}
      language={match[1]}
      PreTag="div"
      className="rounded-lg text-sm"
    >
      {String(children).replace(/\n$/, "")}
    </SyntaxHighlighter>
  ) : (
    <code className="bg-gray-100 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
      {children}
    </code>
  );
}
