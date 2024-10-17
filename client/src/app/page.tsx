"use client";

import { useRouter } from "next/navigation";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import { useAccount } from "wagmi";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useChatState } from "@/contexts/ChatContext";
 

interface MousePosition {
  x: number;
  y: number;
}

export default function HomePage() {
  const router = useRouter();
  const { address, status } = useAccount();
  const { setUserId, setConversationId } = useChatState();
  const [mousePosition, setMousePosition] = useState<MousePosition>({ x: 0, y: 0 });

  const handleConnect = () => {
    if (status === "connected" && address) {
      const timestamp = Math.round(new Date().getTime());
      setUserId(address);
      setConversationId(`${address}-${timestamp}`);
      router.push(`/chat-history/${address}-${timestamp}`);
    }
  };

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      setMousePosition({ x: event.clientX, y: event.clientY });
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return (
    <>
      <div className="relative min-h-screen flex flex-col items-center justify-center bg-gray-900 p-4 overflow-hidden">
        <motion.div
          className="absolute top-0 left-0 w-full h-full pointer-events-none z-50"
          style={{
            background: `radial-gradient(circle at ${mousePosition.x}px ${mousePosition.y}px, transparent 250px, rgba(17, 24, 39, 0.6) 250px)`,
          }}
        />
        <motion.header
          className="text-center mb-8"
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 1 }}
        >
          <motion.h1
            className="text-5xl font-bold text-web3BuddyPurple mb-2"
            whileHover={{ scale: 1.02, transition: { duration: 0.3 } }}
          >
            Web3Buddy
          </motion.h1>
          <p className="text-lg text-white">
            Web3Buddy is a Chat AI agent that helps you navigate the Web3 space.
          </p>
        </motion.header>

        {/* Connect Button Animation */}
        <motion.div
          className="flex flex-col items-center"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1, duration: 0.5, ease: "easeOut" }}
        >
          {status === "connected" ? (
            <motion.button
              onClick={handleConnect}
              className="bg-web3BuddyPurple text-black px-4 py-2 rounded mb-4"
              whileHover={{ scale: 1.05, boxShadow: "0px 4px 10px rgba(81, 56, 187, 0.4)" }}
              whileTap={{ scale: 0.95 }}
              transition={{ duration: 0.3 }}
            >
              Start Chatting
            </motion.button>
          ) : (
            <motion.div whileHover={{ scale: 1.05 }}>
              <ConnectButton
                label="Connect Wallet"
                accountStatus={{
                  smallScreen: "avatar",
                  largeScreen: "full",
                }}
                chainStatus={{
                  smallScreen: "icon",
                  largeScreen: "full",
                }}
                showBalance={{
                  smallScreen: false,
                  largeScreen: true,
                }}
              />
            </motion.div>
          )}
        </motion.div>

        {/* Footer Animation */}
        <motion.footer
          className="mt-8 text-center"
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.5, duration: 1 }}
        >
          <p className="text-sm text-white">Created by Marcos Salazar</p>
          <div className="flex justify-center space-x-4 mt-2">
            {["GitHub Repo", "Website", "LinkedIn"].map((link, index) => (
              <motion.a
                key={index}
                href="#"
                className="text-web3BuddyPurple hover:underline"
                target="_blank"
                rel="noopener noreferrer"
                whileHover={{ scale: 1.1, transition: { duration: 0.3 } }}
              >
                {link}
              </motion.a>
            ))}
          </div>
        </motion.footer>
      </div>
    </>
  );
}