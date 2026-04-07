"use client";

import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { useChatStream } from "@/hooks/useChatStream";
import { useChatStore } from "@/store/chatStore";

export function MessageInput() {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage, isStreaming } = useChatStream();
  const { selectedModelIds } = useChatStore();

  const canSend = value.trim().length > 0 && !isStreaming;

  const handleSend = useCallback(async () => {
    if (!canSend) return;
    const msg = value.trim();
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    await sendMessage(msg);
  }, [canSend, value, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <div className="shrink-0 px-4 pb-4 pt-2">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-3 bg-white border border-gray-200 rounded-2xl shadow-sm px-4 py-3 focus-within:border-gray-300 focus-within:shadow-md transition-shadow">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedModelIds.length === 0
                ? "Start a new message... (using default model)"
                : "Start a new message..."
            }
            disabled={isStreaming}
            rows={1}
            className="flex-1 text-sm text-gray-800 placeholder-gray-400 resize-none outline-none bg-transparent disabled:cursor-not-allowed leading-relaxed"
            style={{ minHeight: 24, maxHeight: 200 }}
          />

          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={handleSend}
            disabled={!canSend}
            className="flex items-center justify-center w-8 h-8 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-200 text-white disabled:text-gray-400 rounded-lg transition-colors shrink-0"
          >
            {isStreaming ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
              />
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            )}
          </motion.button>
        </div>
      </div>
    </div>
  );
}
