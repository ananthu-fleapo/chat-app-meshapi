"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatStream } from "@/hooks/useChatStream";
import { useChatStore } from "@/store/chatStore";
import type { Attachment } from "@/lib/types";

function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function MessageInput() {
  const [value, setValue] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [requestAudio, setRequestAudio] = useState(false);
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);
  const { sendMessage, isStreaming } = useChatStream();
  const { selectedModelIds } = useChatStore();

  const canSend = (value.trim().length > 0 || attachments.length > 0) && !isStreaming;

  const handleSend = useCallback(async () => {
    if (!canSend) return;
    const msg = value.trim();
    setValue("");
    const currentAttachments = attachments;
    const currentRequestAudio = requestAudio;
    setAttachments([]);
    setRequestAudio(false);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    await sendMessage(msg, currentAttachments, currentRequestAudio);
  }, [canSend, value, attachments, requestAudio, sendMessage]);

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

  const handleFileSelect = useCallback(async (files: FileList | null, type: "image" | "audio") => {
    if (!files) return;
    setShowAttachMenu(false);
    const newAttachments: Attachment[] = [];
    for (const file of Array.from(files)) {
      const data = await readFileAsDataURL(file);
      newAttachments.push({ type, name: file.name, mimeType: file.type, data });
    }
    setAttachments((prev) => [...prev, ...newAttachments]);
  }, []);

  const removeAttachment = (index: number) =>
    setAttachments((prev) => prev.filter((_, i) => i !== index));

  return (
    <div className="shrink-0 px-4 pb-4 pt-2">
      <div className="max-w-3xl mx-auto">
        {/* Hidden file inputs */}
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files, "image")}
          onClick={(e) => { (e.target as HTMLInputElement).value = ""; }}
        />
        <input
          ref={audioInputRef}
          type="file"
          accept="audio/*"
          multiple
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files, "audio")}
          onClick={(e) => { (e.target as HTMLInputElement).value = ""; }}
        />

        {/* Attachment previews */}
        <AnimatePresence>
          {attachments.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="flex flex-wrap gap-2 mb-2"
            >
              {attachments.map((att, i) => (
                <div
                  key={i}
                  className="relative flex items-center gap-1.5 bg-gray-100 border border-gray-200 rounded-xl px-2 py-1.5 text-xs text-gray-700 max-w-[180px]"
                >
                  {att.type === "image" ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={att.data}
                      alt={att.name}
                      className="w-8 h-8 object-cover rounded-lg shrink-0"
                    />
                  ) : (
                    <span className="text-base">🎵</span>
                  )}
                  <span className="truncate">{att.name}</span>
                  <button
                    onClick={() => removeAttachment(i)}
                    className="ml-1 text-gray-400 hover:text-gray-600 shrink-0"
                  >
                    ×
                  </button>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-end gap-3 bg-white border border-gray-200 rounded-2xl shadow-sm px-4 py-3 focus-within:border-gray-300 focus-within:shadow-md transition-shadow">
          {/* Attach button */}
          <div className="relative shrink-0 self-end mb-0.5">
            <button
              onClick={() => setShowAttachMenu((v) => !v)}
              disabled={isStreaming}
              title="Attach file"
              className="flex items-center justify-center w-7 h-7 text-gray-400 hover:text-gray-600 disabled:opacity-40 transition-colors rounded-lg hover:bg-gray-100"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>
            <AnimatePresence>
              {showAttachMenu && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  className="absolute bottom-9 left-0 bg-white border border-gray-200 rounded-xl shadow-lg py-1 z-10 min-w-[140px]"
                >
                  <button
                    onClick={() => imageInputRef.current?.click()}
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <span>🖼️</span> Attach image
                  </button>
                  <button
                    onClick={() => audioInputRef.current?.click()}
                    className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                  >
                    <span>🎵</span> Attach audio
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

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

          {/* Audio response toggle */}
          <button
            onClick={() => setRequestAudio((v) => !v)}
            disabled={isStreaming}
            title={requestAudio ? "Audio response on" : "Audio response off"}
            className={`flex items-center justify-center w-7 h-7 shrink-0 self-end mb-0.5 rounded-lg transition-colors ${
              requestAudio
                ? "bg-indigo-100 text-indigo-600"
                : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
            } disabled:opacity-40`}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          </button>

          {/* Send button */}
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
