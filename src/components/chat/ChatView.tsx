"use client";

import { useChatStore } from "@/store/chatStore";
import { HomeScreen } from "@/components/home/HomeScreen";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";

export function ChatView() {
  const { activeRoom } = useChatStore();
  const room = activeRoom();
  const hasMessages = (room?.messages?.length ?? 0) > 0;

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-gray-50">
      {hasMessages ? <MessageList /> : <HomeScreen />}
      <MessageInput />
    </div>
  );
}
