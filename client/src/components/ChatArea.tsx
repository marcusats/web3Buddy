'use client';
import { useState, useEffect, useRef } from 'react';
import { RemoteRunnable } from '@langchain/core/runnables/remote';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import gfm from 'remark-gfm';

interface ChatAreaProps {
  userId: string;
  conversationId: string;
}

const ChatArea: React.FC<ChatAreaProps> = ({ userId, conversationId }) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Clear chat messages when conversationId changes
  useEffect(() => {
    if (!userId || !conversationId) {
      setMessages([]); // Clear messages immediately when IDs are not available
      return;
    }

    setMessages([]); // Clear messages before fetching new chat history
    loadChatHistory();
  }, [userId, conversationId]); // Depend on userId and conversationId changes

  // Load chat history based on userId and conversationId
  const loadChatHistory = async () => {
    if (!userId || !conversationId) return; // Ensure both IDs are set

    try {
      const response = await fetch(`http://localhost:8000/conversations/${userId}/${conversationId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          user_id: userId,
          conv_id: conversationId,
        },
      });
      if (response.ok) {
        const data = await response.json();
        const formattedMessages = data.messages.map((item: any) => ({
          content: item.data.content,
          role: item.type,
          timestamp: item.timestamp,
        }));
        setMessages(formattedMessages.reverse());
      } else {
        console.error('Error loading chat history');
      }
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  };

  // Handle sending messages
  const handleSendMessage = async () => {
    if (!input.trim()) return;
    setIsLoading(true);

    const remoteRunnable = new RemoteRunnable({
      url: 'http://localhost:8000/web3buddy_chat',
      options: {
        headers: {
          'Content-Type': 'application/json',
          'user_id': userId,
          'conv_id': conversationId,
        },
      },
    });

    const userMessage = { content: input, role: 'user' };
    setMessages([...messages, userMessage]);

    const _input = { input };

    try {
      const stream = await remoteRunnable.stream(_input);
      for await (const chunk of stream) {
        const typedChunk = chunk as { ending?: { generation?: string } };

        if (typedChunk.ending) {
          const assistantMessageContent = typedChunk.ending.generation || '';
          const assistantMessage = {
            content: assistantMessageContent,
            role: 'assistant',
          };
          setMessages((prevMessages) => [...prevMessages, assistantMessage]);
          setIsLoading(false);
          break;
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    handleSendMessage();
    setInput(''); // Clear input field after submission
  };

  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight || 0;
    }
  }, [messages]);

  return (
    <div className="h-screen w-full max-w-[calc(100%-250px)] m-5 flex flex-col justify-between">
      <div ref={containerRef} className="h-full flex flex-col overflow-y-auto overflow-x-hidden">
        {messages.length > 0
          ? messages.map((m, index) => (
              <motion.div
                key={index}
                initial={{ x: m.role === 'user' ? 100 : -100, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.3 }}
                className={`${m.role === 'user' ? 'flex justify-end' : 'flex justify-start'} my-1`}
              >
                <div
                  className={`max-w-3/4 px-4 py-2 rounded-lg ${
                    m.role === 'user' ? 'bg-[#5138bb] text-[#edeaf7]' : 'bg-[#edeaf7] text-[#0f0e24]'
                  }`}
                >
                  <ReactMarkdown
                    remarkPlugins={[gfm]}
                    components={{
                      a: ({ node, ...props }) => (
                        <a
                          {...props}
                          style={{ color: 'blue', wordWrap: 'break-word', padding: '2px' }}
                          target="_blank"
                          rel="noopener noreferrer"
                        />
                      ),
                    }}
                  >
                    {m.content}
                  </ReactMarkdown>
                </div>
              </motion.div>
            ))
          : null}
        {isLoading && (
          <motion.div
            className="flex justify-start my-1"
          >
            <div className="max-w-3/4 px-4 py-2 rounded-lg bg-[#edeaf7] text-[#0f0e24]">
              {'Loading...'.split('').map((letter, index) => (
                <motion.span
                  key={index}
                  className="inline-block"
                  initial={{ y: 0 }}
                  animate={{ y: -10 }}
                  transition={{ delay: index * 0.1, duration: 0.5, repeat: Infinity, repeatType: 'reverse' }}
                >
                  {letter}
                </motion.span>
              ))}
            </div>
          </motion.div>
        )}
      </div>
      <form onSubmit={handleSubmit} className="">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Say something..."
          disabled={isLoading}
          className="w-full p-2 border border-gray-300 rounded my-2"
        />
      </form>
    </div>
  );
};

export default ChatArea;