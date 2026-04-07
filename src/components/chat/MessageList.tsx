"use client";

import { useEffect, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { useChatStore } from "@/store/chatStore";
import { ModelResponse } from "./ModelResponse";

export function MessageList() {
  const { activeRoom, selectedModelIds } = useChatStore();
  const room = activeRoom();
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const userScrolledUpRef = useRef(false);
  const lastScrollTopRef = useRef(0);

  // Detect scroll direction — stop auto-scroll the instant user scrolls up
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;

    const current = el.scrollTop;
    const scrollingUp = current < lastScrollTopRef.current;
    lastScrollTopRef.current = current;

    const distanceFromBottom = el.scrollHeight - current - el.clientHeight;

    if (scrollingUp && distanceFromBottom > 10) {
      // User intentionally scrolled up — disable auto-scroll immediately
      userScrolledUpRef.current = true;
    } else if (distanceFromBottom <= 30) {
      // User scrolled back to the bottom — re-enable
      userScrolledUpRef.current = false;
    }
  }, []);

  const scrollToBottom = useCallback((smooth = true) => {
    if (userScrolledUpRef.current) return;
    bottomRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "instant" });
  }, []);

  // Scroll when a new message is added
  useEffect(() => {
    scrollToBottom();
  }, [room?.messages, scrollToBottom]);

  // During streaming: follow the bottom at ~30fps using rAF
  useEffect(() => {
    return useChatStore.subscribe((state) => {
      if (state.isStreaming && !userScrolledUpRef.current) {
        requestAnimationFrame(() => {
          if (!userScrolledUpRef.current) {
            const el = scrollContainerRef.current;
            if (el) el.scrollTop = el.scrollHeight;
          }
        });
      }
    });
  }, []);

  if (!room || room.messages.length === 0) return null;

  return (
    <div
      ref={scrollContainerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-6 py-4"
    >
      <div className="max-w-3xl mx-auto space-y-6">
        {room.messages.map((message) => (
          <div key={message.id}>
            {/* User message */}
            {message.role === "user" && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-end mb-4"
              >
                <div className="max-w-[75%] px-4 py-3 bg-indigo-600 text-white rounded-2xl rounded-tr-sm text-sm leading-relaxed">
                  {message.content}
                </div>
              </motion.div>
            )}

            {/* Model responses */}
            {Object.keys(message.responses).length > 0 && (
              <div className="space-y-1 divide-y divide-gray-100">
                {selectedModelIds
                  .filter((id) => message.responses[id])
                  .map((modelId) => (
                    <ModelResponse
                      key={modelId}
                      messageId={message.id}
                      modelId={modelId}
                      response={message.responses[modelId]}
                    />
                  ))}
                {/* Also show responses from models no longer selected */}
                {Object.keys(message.responses)
                  .filter((id) => !selectedModelIds.includes(id))
                  .map((modelId) => (
                    <ModelResponse
                      key={modelId}
                      messageId={message.id}
                      modelId={modelId}
                      response={message.responses[modelId]}
                    />
                  ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
