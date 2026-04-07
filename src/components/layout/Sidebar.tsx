"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "@/store/chatStore";

const COLLAPSED_KEY = "ai-fiesta-sidebar-collapsed";

export function Sidebar() {
  const { rooms, activeRoomId, setActiveRoom, deleteRoom, createRoom } = useChatStore();
  const [collapsed, setCollapsed] = useState(false);

  // Restore collapse state from localStorage
  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(COLLAPSED_KEY) === "true");
    } catch {}
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem(COLLAPSED_KEY, String(next)); } catch {}
      return next;
    });
  };

  const handleNewChat = () => {
    const id = createRoom();
    setActiveRoom(id);
  };

  const todayStart = new Date().setHours(0, 0, 0, 0);
  const todayRooms = rooms.filter((r) => r.createdAt >= todayStart);
  const olderRooms = rooms.filter((r) => r.createdAt < todayStart);

  return (
    <motion.aside
      animate={{ width: collapsed ? 48 : 256 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="flex flex-col shrink-0 h-screen bg-white border-r border-gray-100 overflow-hidden"
    >
      {/* Top bar — always visible */}
      <div className="flex items-center px-3 pt-4 pb-3 border-b border-gray-100 shrink-0">
        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.1 }}
              onClick={handleNewChat}
              className="flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors flex-1 min-w-0"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
              <span className="truncate">New Chat</span>
            </motion.button>
          )}
        </AnimatePresence>

        {/* Collapse toggle */}
        <button
          onClick={toggleCollapsed}
          className={`flex items-center justify-center w-7 h-7 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors shrink-0 ${collapsed ? "mx-auto" : "ml-1"}`}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <motion.svg
            animate={{ rotate: collapsed ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
          >
            <polyline points="15 18 9 12 15 6" />
          </motion.svg>
        </button>
      </div>

      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex flex-col flex-1 min-h-0"
          >
            {/* Search */}
            <div className="px-3 py-2 shrink-0">
              <input
                type="text"
                placeholder="Search rooms..."
                className="w-full px-3 py-1.5 text-sm bg-gray-50 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-gray-200 placeholder-gray-400"
              />
            </div>

            {/* Room list */}
            <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-4">
              {rooms.length === 0 && (
                <p className="text-xs text-gray-400 px-2 pt-2">No chats yet. Start a new one!</p>
              )}

              {todayRooms.length > 0 && (
                <div>
                  <p className="px-2 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Today</p>
                  <RoomList rooms={todayRooms} activeRoomId={activeRoomId} onSelect={setActiveRoom} onDelete={deleteRoom} />
                </div>
              )}

              {olderRooms.length > 0 && (
                <div>
                  <p className="px-2 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">Earlier</p>
                  <RoomList rooms={olderRooms} activeRoomId={activeRoomId} onSelect={setActiveRoom} onDelete={deleteRoom} />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapsed: new chat icon at bottom */}
      <AnimatePresence initial={false}>
        {collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="flex flex-col items-center gap-2 px-2 py-3"
          >
            <button
              onClick={handleNewChat}
              className="flex items-center justify-center w-8 h-8 text-gray-500 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="New Chat"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  );
}

function RoomList({
  rooms,
  activeRoomId,
  onSelect,
  onDelete,
}: {
  rooms: ReturnType<typeof useChatStore.getState>["rooms"];
  activeRoomId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <AnimatePresence initial={false}>
      {rooms.map((room) => (
        <motion.div
          key={room.id}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -10 }}
          transition={{ duration: 0.15 }}
          className={`group relative flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors text-sm ${
            activeRoomId === room.id
              ? "bg-gray-100 text-gray-900 font-medium"
              : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          }`}
          onClick={() => onSelect(room.id)}
        >
          <span className="truncate flex-1">{room.title}</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(room.id);
            }}
            className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-gray-200 transition-opacity"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </motion.div>
      ))}
    </AnimatePresence>
  );
}
