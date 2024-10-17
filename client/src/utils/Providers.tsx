"use client";
import '@rainbow-me/rainbowkit/styles.css';

import {
    getDefaultConfig,
    RainbowKitProvider,
} from '@rainbow-me/rainbowkit';
import { 
    WagmiProvider 
} from 'wagmi';
import {
    mainnet,
    polygon,
    optimism,
    arbitrum,
    base,
} from 'wagmi/chains';
import {
    QueryClientProvider,
    QueryClient,
} from "@tanstack/react-query";
import React, { ReactNode } from 'react';
import { ChatProvider } from '@/contexts/ChatContext';
 

 
const walletId = process.env.WALLET_PROJECT_ID || '';
 



interface ProvidersProps {
  children: ReactNode;
}

const Providers: React.FC<ProvidersProps> = ({ children }) => {
    const queryClient = new QueryClient();

    const config = getDefaultConfig({
        appName: 'Web3Buddy',
        projectId:"770f6cefc0cfc4678db88813ffd679e1",
        chains: [mainnet, polygon, optimism, arbitrum, base],
    });
    
    return (
      <WagmiProvider config={config}>
        <QueryClientProvider client={queryClient}>
          <RainbowKitProvider>
            <ChatProvider>
              {children}
            </ChatProvider>
          </RainbowKitProvider> 
        </QueryClientProvider>
      </WagmiProvider>
    );
};
export default Providers;
