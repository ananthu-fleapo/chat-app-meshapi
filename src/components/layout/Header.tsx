"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "@/store/chatStore";
import { ProviderAvatar } from "@/components/ui/ProviderAvatar";
import { useModels } from "@/hooks/useModels";
import { useState } from "react";
import { ModelPicker } from "@/components/modals/ModelPicker";

export function Header() {
  const { selectedModelIds, toggleModel, clearModels } = useChatStore();
  const { data: models } = useModels();
  const [pickerOpen, setPickerOpen] = useState(false);

  const getModelName = (id: string) => {
    const found = models?.find((m) => m.id === id);
    return found?.name ?? id;
  };

  return (
    <>
      <header className="flex items-center gap-2 px-4 py-3 bg-white border-b border-gray-100 overflow-x-auto shrink-0">
        {/* New Chat button (when no models selected show standalone) */}
        {selectedModelIds.length === 0 && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPickerOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add Model
              <span className="ml-1 text-xs text-gray-400 font-mono">⌘ K</span>
            </button>
          </div>
        )}

        {/* Model tabs */}
        <AnimatePresence initial={false}>
          {selectedModelIds.map((modelId) => (
            <motion.div
              key={modelId}
              initial={{ opacity: 0, scale: 0.85, x: -8 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.85, x: -8 }}
              transition={{ duration: 0.15 }}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 shrink-0 group"
            >
              <ProviderAvatar modelId={modelId} size={18} />
              <span className="max-w-[140px] truncate">{getModelName(modelId)}</span>
              <button
                onClick={() => toggleModel(modelId)}
                className="ml-1 opacity-50 group-hover:opacity-100 hover:text-red-500 transition-colors"
                title="Remove model"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Add more button when models are already selected */}
        {selectedModelIds.length > 0 && (
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setPickerOpen(true)}
              className="flex items-center justify-center w-8 h-8 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors border border-dashed border-gray-300"
              title="Add model"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>

            {/* Clear all */}
            <button
              onClick={clearModels}
              className="flex items-center justify-center w-8 h-8 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
              title="Clear all models"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        )}
      </header>

      <ModelPicker open={pickerOpen} onClose={() => setPickerOpen(false)} />
    </>
  );
}
