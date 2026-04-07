"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGroupedModels } from "@/hooks/useModels";
import { useChatStore } from "@/store/chatStore";
import { ProviderAvatar } from "@/components/ui/ProviderAvatar";
import type { MeshModel } from "@/lib/types";

interface Props {
  open: boolean;
  onClose: () => void;
}

type FilterType = "free" | "hide_unavailable";

export function ModelPicker({ open, onClose }: Props) {
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Set<FilterType>>(new Set(["hide_unavailable"]));
  // hoveredModel is set per-row and only cleared when cursor leaves the entire left panel
  const [hoveredModel, setHoveredModel] = useState<MeshModel | null>(null);

  const { grouped, isLoading } = useGroupedModels();
  const { selectedModelIds, toggleModel } = useChatStore();

  const toggleFilter = (f: FilterType) => {
    setFilters((prev) => {
      const next = new Set(prev);
      next.has(f) ? next.delete(f) : next.add(f);
      return next;
    });
  };

  const filteredGroups = useMemo(() => {
    return grouped
      .map((group) => {
        const models = group.models.filter((m) => {
          if (
            search &&
            !m.name.toLowerCase().includes(search.toLowerCase()) &&
            !m.id.toLowerCase().includes(search.toLowerCase())
          ) {
            return false;
          }
          if (filters.has("free") && !m.is_free) return false;
          return true;
        });
        return { ...group, models };
      })
      .filter((g) => g.models.length > 0);
  }, [grouped, search, filters]);

  if (!open) return null;

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 8 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              className="bg-white rounded-2xl shadow-2xl border border-gray-200 flex overflow-hidden relative"
              style={{ width: 720, maxHeight: "70vh" }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close button */}
              <button
                onClick={onClose}
                className="absolute top-3 right-3 z-10 flex items-center justify-center w-7 h-7 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title="Close"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>

              {/* Left: Model List — onMouseLeave here clears hovered, not on individual rows */}
              <div
                className="flex flex-col flex-1 min-w-0"
                onMouseLeave={() => setHoveredModel(null)}
              >
                {/* Search */}
                <div className="px-4 pt-4 pb-3 border-b border-gray-100">
                  <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                      autoFocus
                      type="text"
                      placeholder="Search models"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="flex-1 bg-transparent text-sm outline-none placeholder-gray-400"
                    />
                  </div>

                  {/* Filter chips */}
                  <div className="flex items-center gap-2 mt-2">
                    <FilterChip
                      label="Free"
                      active={filters.has("free")}
                      onClick={() => toggleFilter("free")}
                    />
                    <FilterChip
                      label="Hide Unavailable"
                      active={filters.has("hide_unavailable")}
                      onClick={() => toggleFilter("hide_unavailable")}
                    />
                    {(filters.size > 0 || search) && (
                      <button
                        onClick={() => {
                          setFilters(new Set());
                          setSearch("");
                        }}
                        className="px-3 py-1 text-xs text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>

                {/* Model list */}
                <div className="flex-1 overflow-y-auto">
                  {isLoading && (
                    <div className="flex items-center justify-center py-12 text-sm text-gray-400">
                      Loading models...
                    </div>
                  )}

                  {!isLoading && filteredGroups.length === 0 && (
                    <div className="flex items-center justify-center py-12 text-sm text-gray-400">
                      No models found
                    </div>
                  )}

                  {filteredGroups.map((group) => (
                    <div key={group.label}>
                      <p className="px-4 py-2 text-xs font-semibold text-gray-400 sticky top-0 bg-white border-b border-gray-50">
                        {group.label}
                      </p>
                      {group.models.map((model) => {
                        const isSelected = selectedModelIds.includes(model.id);
                        return (
                          <motion.button
                            key={model.id}
                            whileHover={{ backgroundColor: "#f9fafb" }}
                            onClick={() => toggleModel(model.id)}
                            // Only onMouseEnter per row — leave is handled by parent div
                            onMouseEnter={() => setHoveredModel(model)}
                            className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                              isSelected ? "bg-blue-50" : ""
                            }`}
                          >
                            <ProviderAvatar modelId={model.id} size={28} />
                            <span className="text-sm text-gray-800 flex-1 truncate">{model.name}</span>
                            {model.is_free && (
                              <span className="text-xs px-1.5 py-0.5 bg-green-50 text-green-600 rounded font-medium">
                                Free
                              </span>
                            )}
                            {isSelected && (
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2.5">
                                <polyline points="20 6 9 17 4 12" />
                              </svg>
                            )}
                          </motion.button>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>

              {/* Right: Description panel — always rendered as fixed-width, content swaps */}
              <div className="w-56 shrink-0 border-l border-gray-100 overflow-y-auto">
                <AnimatePresence mode="wait">
                  {hoveredModel ? (
                    <motion.div
                      key={hoveredModel.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.1 }}
                      className="p-5"
                    >
                      <div className="flex items-center gap-2 mb-3">
                        <ProviderAvatar modelId={hoveredModel.id} size={32} />
                        <span className="text-sm font-semibold text-gray-900 leading-tight">
                          {hoveredModel.name}
                        </span>
                      </div>

                      {hoveredModel.description && (
                        <p className="text-xs text-gray-500 leading-relaxed mb-4">
                          {hoveredModel.description}
                        </p>
                      )}

                      {hoveredModel.context_length && (
                        <div className="mb-3">
                          <p className="text-xs font-medium text-gray-400 mb-1">Context</p>
                          <p className="text-xs text-gray-700">
                            {(hoveredModel.context_length / 1000).toFixed(0)}K tokens
                          </p>
                        </div>
                      )}

                      {hoveredModel.pricing && (
                        <div>
                          <p className="text-xs font-medium text-gray-400 mb-1">Pricing</p>
                          {hoveredModel.is_free ? (
                            <p className="text-xs text-green-600 font-medium">Free</p>
                          ) : (
                            <div className="space-y-0.5">
                              {hoveredModel.pricing.prompt_usd_per_1k && (
                                <p className="text-xs text-gray-600">
                                  Input: ${hoveredModel.pricing.prompt_usd_per_1k}/1K
                                </p>
                              )}
                              {hoveredModel.pricing.completion_usd_per_1k && (
                                <p className="text-xs text-gray-600">
                                  Output: ${hoveredModel.pricing.completion_usd_per_1k}/1K
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </motion.div>
                  ) : (
                    <motion.div
                      key="empty"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.1 }}
                      className="p-5 flex items-center justify-center h-full"
                    >
                      <p className="text-xs text-gray-300 text-center">
                        Hover a model to see details
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors ${
        active ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
      }`}
    >
      {label}
    </button>
  );
}
