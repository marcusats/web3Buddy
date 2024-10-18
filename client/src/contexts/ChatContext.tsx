'use client';

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface Conversation {
  userId: string;
  conversationId: string;
}

interface ChatContextProps {
  userId: string | null;
  conversationId: string | null;
  conversations: Conversation[];
  setUserId: (id: string) => void;
  setConversationId: (id: string) => void;
  addConversation: (userId: string, conversationId: string) => void;
}

const ChatContext = createContext<ChatContextProps | undefined>(undefined);

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [userId, setUserIdState] = useState<string | null>(null);
  const [conversationId, setConversationIdState] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);

  const setUserId = (id: string) => {
    setUserIdState(id);
  };

  const setConversationId = (id: string) => {
    setConversationIdState(id);
  };

  const addConversation = (userId: string, conversationId: string) => {
    setConversations((prevConversations) => [
      ...prevConversations,
      { userId, conversationId },
    ]);
  };

  return (
    <ChatContext.Provider
      value={{
        userId,
        conversationId,
        conversations,
        setUserId,
        setConversationId,
        addConversation,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChatState = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
