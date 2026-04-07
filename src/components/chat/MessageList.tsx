"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { useChatStore } from "@/store/chatStore";
import { ModelResponse } from "./ModelResponse";

export function MessageList() {
  const { activeRoom, selectedModelIds } = useChatStore();
  const room = activeRoom();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [room?.messages]);

  if (!room || room.messages.length === 0) return null;

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4">
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
