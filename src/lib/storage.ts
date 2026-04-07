import type { ChatRoom } from "./types";

const STORAGE_KEY = "ai-fiesta-chat-rooms";
const SELECTED_MODELS_KEY = "ai-fiesta-selected-models";

export function loadRooms(): ChatRoom[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveRooms(rooms: ChatRoom[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(rooms));
  } catch {
    // Storage quota exceeded or unavailable
  }
}

export function loadSelectedModels(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(SELECTED_MODELS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveSelectedModels(modelIds: string[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(SELECTED_MODELS_KEY, JSON.stringify(modelIds));
  } catch {}
}
