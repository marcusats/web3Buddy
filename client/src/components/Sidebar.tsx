'use client';
import { useState, useEffect, use } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { SidebarNav } from "@/components/ui/sidebar-nav";
import { useRouter } from "next/navigation";
import { useChatState } from "@/contexts/ChatContext";
import { useAccount } from "wagmi";

interface SidebarProps {
  userId: string;
  conversationId: string;
}

interface Item {
  href: string;
  title: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ userId, conversationId }) => {
  const params = useParams();
  const [items, setItems] = useState<Item[]>([]);
  const router = useRouter();
  const { address, status } = useAccount();
 
  const handleRetrieveSidebar = async () => {
    if (!address) {
      return;
    }
    try {
      console.log("User ID:", address);
      const response = await fetch(`http://localhost:8000/conversations/${address}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "user_id": address,  
        },
      });

      if (response.ok) {
        const data = await response.json();
        const conversationKeys = data.conversation_keys;

        const dbChatHistory = conversationKeys.map((key: string) => {
          const [user, conversationId] = key.split(":");
          return {
            href: `/chat-history/${user}-${conversationId}`,
            title: conversationId,
          };
        });

        setItems(dbChatHistory.reverse());
      } else {
        console.error("Error retrieving conversation keys");
      }
    } catch (error) {
      console.error("Fetch error:", error);
    }
  };

  const handleUpdateSidebar = async () => {
    const chatId = Date.now().toString();
    
    router.push(`/chat-history/${address}-${chatId}`);
  };

  useEffect(() => {
    handleRetrieveSidebar();
  }, []);

  return (
    <div className="w-64 h-full top-0 overflow-y-auto bg-[#1e122a] flex flex-col justify-top px-2">
      <div className="ml-auto w-full">
        <Button className="w-full my-2 bg-[#6c6c74]" onClick={handleUpdateSidebar}>
          New Chat
        </Button>
      </div>
      <SidebarNav items={items} className="flex-col" />
    </div>
  );
};