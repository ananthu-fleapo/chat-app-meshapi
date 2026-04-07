"use client";

import { create } from "zustand";
import { nanoid } from "nanoid";
import type { ChatRoom, ChatMessage, ModelResponseState, ResponseUsage } from "@/lib/types";
import { loadRooms, saveRooms, loadSelectedModels, saveSelectedModels } from "@/lib/storage";

interface ChatStore {
  rooms: ChatRoom[];
  activeRoomId: string | null;
  selectedModelIds: string[];
  isStreaming: boolean;

  // Hydration
  hydrate: () => void;

  // Room actions
  createRoom: () => string;
  setActiveRoom: (id: string | null) => void;
  deleteRoom: (id: string) => void;

  // Model selection
  toggleModel: (modelId: string) => void;
  setModels: (modelIds: string[]) => void;
  clearModels: () => void;

  // Message actions
  addUserMessage: (content: string) => string;
  initModelResponse: (messageId: string, modelId: string) => void;
  appendModelContent: (messageId: string, modelId: string, chunk: string) => void;
  finalizeModelResponse: (messageId: string, modelId: string, error?: string, usage?: ResponseUsage) => void;
  setStreaming: (streaming: boolean) => void;

  // Computed
  activeRoom: () => ChatRoom | undefined;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  rooms: [],
  activeRoomId: null,
  selectedModelIds: [],
  isStreaming: false,

  hydrate: () => {
    const rooms = loadRooms();
    const selectedModelIds = loadSelectedModels();
    const activeRoomId = rooms.length > 0 ? rooms[0].id : null;
    set({ rooms, selectedModelIds, activeRoomId });
  },

  createRoom: () => {
    const id = nanoid();
    const room: ChatRoom = {
      id,
      title: "Untitled Chat",
      messages: [],
      selectedModelIds: get().selectedModelIds,
      createdAt: Date.now(),
    };
    const rooms = [room, ...get().rooms];
    saveRooms(rooms);
    set({ rooms, activeRoomId: id });
    return id;
  },

  setActiveRoom: (id) => set({ activeRoomId: id }),

  deleteRoom: (id) => {
    const rooms = get().rooms.filter((r) => r.id !== id);
    const activeRoomId = get().activeRoomId === id ? (rooms[0]?.id ?? null) : get().activeRoomId;
    saveRooms(rooms);
    set({ rooms, activeRoomId });
  },

  toggleModel: (modelId) => {
    const current = get().selectedModelIds;
    const updated = current.includes(modelId)
      ? current.filter((id) => id !== modelId)
      : [...current, modelId];
    saveSelectedModels(updated);
    set({ selectedModelIds: updated });
  },

  setModels: (modelIds) => {
    saveSelectedModels(modelIds);
    set({ selectedModelIds: modelIds });
  },

  clearModels: () => {
    saveSelectedModels([]);
    set({ selectedModelIds: [] });
  },

  addUserMessage: (content) => {
    const messageId = nanoid();
    const message: ChatMessage = {
      id: messageId,
      role: "user",
      content,
      responses: {},
      createdAt: Date.now(),
    };

    const rooms = get().rooms.map((room) => {
      if (room.id !== get().activeRoomId) return room;
      const isFirst = room.messages.length === 0;
      return {
        ...room,
        title: isFirst ? content.slice(0, 40) : room.title,
        messages: [...room.messages, message],
      };
    });

    saveRooms(rooms);
    set({ rooms });
    return messageId;
  },

  initModelResponse: (messageId, modelId) => {
    const response: ModelResponseState = { content: "", done: false };
    const rooms = get().rooms.map((room) => {
      if (room.id !== get().activeRoomId) return room;
      return {
        ...room,
        messages: room.messages.map((msg) => {
          if (msg.id !== messageId) return msg;
          return {
            ...msg,
            responses: { ...msg.responses, [modelId]: response },
          };
        }),
      };
    });
    set({ rooms });
  },

  appendModelContent: (messageId, modelId, chunk) => {
    const rooms = get().rooms.map((room) => {
      if (room.id !== get().activeRoomId) return room;
      return {
        ...room,
        messages: room.messages.map((msg) => {
          if (msg.id !== messageId) return msg;
          const existing = msg.responses[modelId] ?? { content: "", done: false };
          return {
            ...msg,
            responses: {
              ...msg.responses,
              [modelId]: { ...existing, content: existing.content + chunk },
            },
          };
        }),
      };
    });
    set({ rooms });
  },

  finalizeModelResponse: (messageId, modelId, error, usage) => {
    const rooms = get().rooms.map((room) => {
      if (room.id !== get().activeRoomId) return room;
      return {
        ...room,
        messages: room.messages.map((msg) => {
          if (msg.id !== messageId) return msg;
          const existing = msg.responses[modelId] ?? { content: "", done: false };
          return {
            ...msg,
            responses: {
              ...msg.responses,
              [modelId]: { ...existing, done: true, error, usage },
            },
          };
        }),
      };
    });
    saveRooms(rooms);
    set({ rooms });
  },

  setStreaming: (isStreaming) => set({ isStreaming }),

  activeRoom: () => get().rooms.find((r) => r.id === get().activeRoomId),
}));
