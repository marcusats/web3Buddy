'use client';
import { useState, useEffect, useRef } from 'react';
import { RemoteRunnable } from '@langchain/core/runnables/remote';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import gfm from 'remark-gfm';
import InquiryComponent from './InquiryComponent';
import { Message } from '@/types/Messages';
import { cn } from '@/lib/utils';

interface ChatAreaProps {
  userId: string;
  conversationId: string;
}

const ChatArea: React.FC<ChatAreaProps> = ({ userId, conversationId }) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!userId || !conversationId) {
      setMessages([]);
      return;
    }

    setMessages([]);
    loadChatHistory();
  }, [userId, conversationId]);

  const loadChatHistory = async () => {
    if (!userId || !conversationId) return;

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
        const formattedMessages: Message[] = data.messages.map((item: any) => ({
          content: item.data.content,
          role: item.type,
          timestamp: item.timestamp,
          inquiry: false,
        }));
        setMessages(formattedMessages.reverse());
      } else {
        console.error('Error loading chat history');
      }
    } catch (error) {
      console.error('Failed to fetch messages:', error);
    }
  };

  const handleSubmit = async (messageContent: string, userMessage: boolean = true) => {
    if (!messageContent.trim()) return;
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

    if (userMessage) {
      const userMessageObject: Message = { content: messageContent, role: 'user', inquiry: false };
      setMessages([...messages, userMessageObject]);
    }

    const _input = { input: messageContent };

    try {
      const stream = await remoteRunnable.stream(_input);
      for await (const chunk of stream) {
        const typedChunk = chunk as { ending?: { generation?: string }, params_inquiry?: { generation?: string } };

        if (typedChunk.ending) {
          const assistantMessageContent = typedChunk.ending.generation || '';
          const assistantMessage: Message = {
            content: assistantMessageContent,
            role: 'assistant',
            inquiry: false,
          };
          setMessages((prevMessages) => [...prevMessages, assistantMessage]);
          setIsLoading(false);
          break;
        }

        if (typedChunk.params_inquiry) {
          const assistantMessageContent = typedChunk.params_inquiry.generation || '';
          const assistantMessage: Message = {
            content: assistantMessageContent,
            role: 'assistant',
            inquiry: true,
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

  const handleInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    handleSubmit(input);
    setInput('');
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
                className={cn('my-1', {
                  'flex justify-end': m.role === 'user',
                  'flex justify-start': m.role !== 'user',
                })}
              >
                {m.inquiry ? (
                  <InquiryComponent message={m.content} onSubmit={handleSubmit} />
                ) : (
                  <div
                    className={cn(
                      'max-w-full px-4 py-2 rounded-lg break-words whitespace-pre-wrap',
                      {
                        'bg-[#5138bb] text-[#edeaf7]': m.role === 'user',
                        'bg-[#edeaf7] text-[#0f0e24]': m.role !== 'user',
                      }
                    )}
                  >
                   <ReactMarkdown
                      remarkPlugins={[gfm]}
                      components={{
                        a: ({ node, ...props }) => (
                          <a
                            {...props}
                            style={{
                              color: 'blue',
                              wordBreak: 'break-word',
                              overflowWrap: 'break-word',  
                              padding: '2px',
                            }}
                            target="_blank"
                            rel="noopener noreferrer"
                          />
                        ),
                        code: ({ node, className, children, ...props }) => {
                          return   (
                            <pre
                              style={{
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                                overflowWrap: 'break-word',
                                backgroundColor: '#f5f5f5',
                                padding: '10px',
                                borderRadius: '5px',
                                overflowX: 'auto',
                              }}
                            >
                              <code {...props}>
                                {children}
                              </code>
                            </pre>
                          );
                        }
                      }}
                    >
                      {m.content}
                    </ReactMarkdown>

                  </div>
                )}
              </motion.div>
            ))
          : null}
        {isLoading && (
          <motion.div className="flex justify-start my-1">
            <div className="max-w-full px-4 py-2 rounded-lg bg-[#edeaf7] text-[#0f0e24] break-words">
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
      <form onSubmit={handleInputSubmit} className="">
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
