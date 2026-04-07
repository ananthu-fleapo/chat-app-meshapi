"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { CategoryCard } from "./CategoryCard";
import { PROMPT_SUGGESTIONS, type CategoryKey } from "@/lib/modelCategories";
import { useChatStore } from "@/store/chatStore";
import { useChatStream } from "@/hooks/useChatStream";
import { useModels } from "@/hooks/useModels";

export function HomeScreen() {
  const categories: CategoryKey[] = ["flagship", "roleplay", "coding", "reasoning"];
  const { selectedModelIds, createRoom, setActiveRoom } = useChatStore();
  const { sendMessage } = useChatStream();
  const { data: models } = useModels();

  // Build a set of available model IDs from the API
  const availableModelIds = useMemo(
    () => new Set(models?.map((m) => m.id) ?? []),
    [models]
  );

  const handlePrompt = async (prompt: string) => {
    let roomId = useChatStore.getState().activeRoomId;
    if (!roomId) {
      roomId = createRoom();
      setActiveRoom(roomId);
    }
    await sendMessage(prompt);
  };

  // Only show categories section when no models are selected
  const showCategories = selectedModelIds.length === 0;

  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 py-8 overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-2xl space-y-8"
      >
        {/* Category cards grid — hidden when models are selected */}
        {showCategories && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-2 gap-3"
          >
            {categories.map((key) => (
              <CategoryCard
                key={key}
                categoryKey={key}
                availableModelIds={availableModelIds}
              />
            ))}
          </motion.div>
        )}

        {/* Prompt suggestion chips */}
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          {PROMPT_SUGGESTIONS.map((suggestion) => (
            <motion.button
              key={suggestion.label}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => handlePrompt(suggestion.prompt)}
              className="flex flex-col shrink-0 px-4 py-3 bg-white border border-gray-200 rounded-xl text-left hover:border-gray-300 hover:shadow-sm transition-all max-w-[180px]"
            >
              <span className="text-xs font-semibold text-gray-700 truncate">{suggestion.label}</span>
              <span className="text-xs text-gray-400 mt-0.5 line-clamp-2">{suggestion.prompt}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
