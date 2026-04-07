"use client";

import { motion } from "framer-motion";
import { ProviderAvatar } from "@/components/ui/ProviderAvatar";
import { useChatStore } from "@/store/chatStore";
import type { CategoryKey } from "@/lib/modelCategories";
import { MODEL_CATEGORIES } from "@/lib/modelCategories";

interface Props {
  categoryKey: CategoryKey;
  availableModelIds: Set<string>;
}

export function CategoryCard({ categoryKey, availableModelIds }: Props) {
  const category = MODEL_CATEGORIES[categoryKey];
  const { setModels, createRoom, setActiveRoom } = useChatStore();

  // Only use models that are available in the API
  const availableInCategory = category.modelIds.filter((id) => availableModelIds.has(id));

  // Hide card entirely if no models from this category are available
  if (availableInCategory.length === 0) return null;

  const handleClick = () => {
    setModels(availableInCategory.slice(0, 4));
    const id = createRoom();
    setActiveRoom(id);
  };

  return (
    <motion.button
      whileHover={{ y: -2, boxShadow: "0 4px 20px rgba(0,0,0,0.08)" }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.15 }}
      onClick={handleClick}
      className="flex flex-col justify-between p-5 bg-white rounded-2xl border border-gray-200 text-left cursor-pointer h-36 hover:border-gray-300 transition-colors"
    >
      <p className="text-sm font-medium text-gray-800">{category.label}</p>
      <div className="flex items-center gap-1.5 mt-auto">
        {availableInCategory.slice(0, 4).map((id) => (
          <ProviderAvatar key={id} modelId={id} size={26} />
        ))}
      </div>
    </motion.button>
  );
}
