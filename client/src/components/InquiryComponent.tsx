import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { InquiryMessage } from '@/types/Messages';

interface InquiryComponentProps {
  message: string;
  onSubmit: (messageContent: string, userMessage: boolean) => void; // Add onSubmit prop
}

const InquiryComponent: React.FC<InquiryComponentProps> = ({ message, onSubmit }) => {
  const [formData, setFormData] = useState<{ [key: string]: any }>({});
  const [parsedMessage, setParsedMessage] = useState<InquiryMessage | null>(null);

  useEffect(() => {
    try {
      const parsed = JSON.parse(message) as InquiryMessage;
      setParsedMessage(parsed);
    } catch (error) {
      console.error('Failed to parse the message:', error);
    }
  }, [message]);

  const handleInputChange = (key: string, value: string | boolean | number) => {
    setFormData({
      ...formData,
      [key]: value,
    });
  };

  const handleSend = () => {
    const paramsArray = Object.entries(formData).map(([key, value]) => `${value}`);
    const messageContent = `EXECUTE, use the EXCUTER  ${parsedMessage?.input} {params:[${paramsArray.join(',')}]}`;
    console.log('Sending message:', messageContent);
    onSubmit(messageContent, false);
  };

  if (!parsedMessage) {
    return <div>Error parsing message</div>;
  }

  return (
    <motion.div
      className="p-4 bg-gradient-to-br from-gray-700 via-gray-800 to-black text-white rounded-lg shadow-md w-1/2" 
      initial={{ opacity: 0, y: 50 }} 
      animate={{ opacity: 1, y: 0 }} 
      transition={{ duration: 0.5, ease: 'easeOut' }}
    >
      <div className="text-sm font-semibold mb-4">{parsedMessage.content}</div> {/* Smaller title text */}
      <div className="space-y-4">
        {Object.keys(parsedMessage.params).map((key, index) => (
          <motion.div
            key={index}
            className="flex flex-col"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <label htmlFor={key} className="text-xs font-medium mb-1"> {/* Smaller label text */}
              {key} ({parsedMessage.params[key]})
            </label>

            {parsedMessage.params[key] === 'boolean' ? (
              <div className="flex space-x-4">
                <label className="text-xs">
                  <input
                    type="radio"
                    name={key}
                    value="true"
                    onChange={() => handleInputChange(key, true)}
                    className="mr-1"
                  />
                  True
                </label>
                <label className="text-xs">
                  <input
                    type="radio"
                    name={key}
                    value="false"
                    onChange={() => handleInputChange(key, false)}
                    className="mr-1"
                  />
                  False
                </label>
              </div>
            ) : (
              <input
                id={key}
                type="text"
                onChange={(e) =>
                  handleInputChange(
                    key, 
                    parsedMessage.params[key] === 'number' 
                      ? parseFloat(e.target.value) 
                      : e.target.value
                  )
                }
                className="border border-gray-500 rounded p-2 text-gray-900 bg-gray-200"
              />
            )}
          </motion.div>
        ))}
      </div>
      <motion.button
        onClick={handleSend}
        className="mt-4 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded text-sm"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        Send
      </motion.button>
    </motion.div>
  );
};

export default InquiryComponent;