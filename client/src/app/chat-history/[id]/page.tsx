'use client';

import { Sidebar } from "@/components/Sidebar";
import ChatArea from "@/components/ChatArea";
import { useParams } from 'next/navigation';
import { useAccount } from "wagmi";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import { motion } from "framer-motion";
import { useEffect, useState } from 'react';

export default function Chat() {
  const params = useParams<{ id: string; }>();
  const { address, status } = useAccount();

  // Extract userId and conversationId from params
  const [userId, conversationId] = params.id ? params.id.split('-') : ["", ""];

  // State to track connection status
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);

  // useEffect to update connection status
  useEffect(() => {
    setIsConnected(status === "connected");
    setIsReconnecting(status === "reconnecting");
  }, [status]);

  // Show loading animation initially
  if (isReconnecting || (!isConnected && !isReconnecting)) {
    return (
      <div className="w-full h-screen flex justify-center items-center relative">
        <div className="absolute top-0 left-0 w-full h-full bg-gray-900 flex items-center justify-center z-10">
          <motion.div
            className="flex"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, repeat: Infinity, repeatType: "reverse" }}
          >
            {'Loading...'.split('').map((letter, index) => (
              <motion.span
                key={index}
                className="text-white text-4xl inline-block"
                initial={{ y: 0 }}
                animate={{ y: -10 }}
                transition={{ delay: index * 0.1, duration: 0.5, repeat: Infinity, repeatType: "reverse" }}
              >
                {letter}
              </motion.span>
            ))}
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-screen flex justify-between items-center relative">
      {!isConnected && (
        <motion.div
          className="absolute top-0 left-0 w-full h-full bg-gray-900 flex flex-col items-center justify-center z-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.8 }}
        >
          <p className="text-white text-2xl mb-4">Hey, you are not logged in. Please use the Connect Wallet button.</p>
          <ConnectButton />
        </motion.div>
      )}
      <Sidebar userId={userId} conversationId={conversationId} />
      <ChatArea userId={userId} conversationId={conversationId} />
    </div>
  );
}
