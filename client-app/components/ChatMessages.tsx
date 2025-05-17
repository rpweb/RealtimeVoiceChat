'use client';

import React from 'react';
import { FaUser, FaRobot } from 'react-icons/fa';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'function' | 'data' | 'tool';
  content: string;
  audioUrl?: string;
}

interface ChatMessagesProps {
  messages: Message[];
}

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages }) => {
  return (
    <div className="flex flex-col space-y-4 p-4 w-full max-w-4xl mx-auto">
      {messages.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p>No messages yet. Start a conversation!</p>
        </div>
      ) : (
        messages.map((message) => {
          // Skip system messages
          if (message.role === 'system') return null;
          
          const isUser = message.role === 'user';
          
          return (
            <div 
              key={message.id} 
              className={`flex items-start space-x-2 ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              {!isUser && (
                <div className="flex-shrink-0 w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center text-white">
                  <FaRobot />
                </div>
              )}
              
              <div className="flex flex-col">
                <div 
                  className={`p-3 rounded-lg max-w-md break-words ${
                    isUser 
                      ? 'bg-blue-500 text-white rounded-br-none' 
                      : 'bg-gray-200 text-gray-800 rounded-bl-none'
                  }`}
                >
                  {message.content}
                </div>
                
                {message.audioUrl && (
                  <audio 
                    src={message.audioUrl} 
                    controls 
                    className="mt-2 max-w-md"
                  />
                )}
              </div>
              
              {isUser && (
                <div className="flex-shrink-0 w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white">
                  <FaUser />
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
};

export default ChatMessages; 