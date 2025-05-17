'use client';

import { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useChat, Message as AIMessage } from 'ai/react';
import { io, Socket } from 'socket.io-client';
import dynamic from 'next/dynamic';
import ChatMessages from '@/components/ChatMessages';
import { fetchEndpointConfig, getEndpointIds } from '@/lib/runpod';

// Dynamically import AudioRecorder with no SSR
const AudioRecorder = dynamic(() => import('@/components/AudioRecorder'), {
  ssr: false
});

// Backend service URL
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://your-railway-server.railway.app';

export default function Home() {
  // State for session management
  const [sessionId, setSessionId] = useState<string>('');
  const [socket, setSocket] = useState<Socket | null>(null);
  
  // Audio playback state
  const [currentAudio, setCurrentAudio] = useState<HTMLAudioElement | null>(null);
  
  // UI state
  const [isProcessing, setIsProcessing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [endpointsReady, setEndpointsReady] = useState(false);
  
  // Using Vercel AI SDK useChat for chat functionality
  const { messages, input, handleInputChange, handleSubmit, setMessages, isLoading } = useChat({
    api: '/api/chat',
    body: { sessionId },
    onResponse: (response) => {
      // Parse any streamed metadata like session ID
      const reader = response.body?.getReader();
      // You could handle metadata here
    },
    onFinish: async (message) => {
      // When AI is done responding, check if there's audio available
      const audioResponse = await fetch(`/api/audio?messageId=${message.id}&sessionId=${sessionId}`);
      if (audioResponse.ok) {
        const data = await audioResponse.json();
        if (data.audio_base64) {
          playAudio(`data:audio/mp3;base64,${data.audio_base64}`);
        }
      }
    }
  });
  
  // Initialize socket connection and session
  useEffect(() => {
    // Initialize endpoints first to ensure proper API communication
    const initializeApp = async () => {
      try {
        // Fetch RunPod endpoints
        await fetchEndpointConfig();
        
        // Check if endpoints were successfully fetched
        const endpoints = getEndpointIds();
        if (endpoints.WHISPER_ENDPOINT_ID && endpoints.LLM_ENDPOINT_ID && endpoints.TTS_ENDPOINT_ID) {
          setEndpointsReady(true);
          console.log('RunPod endpoints initialized successfully');
        } else {
          console.warn('Some RunPod endpoints are missing:', endpoints);
          setError('Warning: Some AI services may not be available');
        }
        
        // Continue with initialization
        initializeSession();
        initializeSocket();
      } catch (err) {
        console.error('Error initializing app:', err);
        setError('Failed to initialize application. Please reload the page.');
      }
    };
    
    initializeApp();
    
    return () => {
      // Clean up socket connection when component unmounts
      if (socket) {
        socket.disconnect();
      }
    };
  }, []);
  
  // Initialize session with backend
  const initializeSession = async () => {
    try {
      // Generate a session ID if we don't have one
      const newSessionId = sessionId || uuidv4();
      setSessionId(newSessionId);
      
      // Get existing messages for this session if any
      const response = await fetch(`/api/chat?sessionId=${newSessionId}`);
      if (response.ok) {
        const data = await response.json();
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages.map((msg: any) => ({
            id: msg.id || uuidv4(),
            role: msg.role,
            content: msg.content
          })));
        }
      }
    } catch (err) {
      console.error('Error initializing session:', err);
      setError('Failed to initialize session. Please try again.');
    }
  };
  
  // Initialize Socket.IO connection
  const initializeSocket = () => {
    const newSocket = io(BACKEND_URL);
    
    newSocket.on('connect', () => {
      setIsConnected(true);
      setError(null);
      console.log('Connected to backend server');
    });
    
    newSocket.on('disconnect', () => {
      setIsConnected(false);
      console.log('Disconnected from backend server');
    });
    
    newSocket.on('assistant_response', (data) => {
      // Create a new message
      const newMessage: AIMessage = {
        id: uuidv4(),
        role: 'assistant',
        content: data.text,
        createdAt: new Date()
      };
      
      // Update messages with the new message
      setMessages([...messages, newMessage]);
      
      // Play audio if available
      if (data.audio) {
        playAudio(`data:audio/mp3;base64,${data.audio}`);
      }
    });
    
    newSocket.on('error', (error) => {
      console.error('Socket error:', error);
      setError(error.message || 'An error occurred');
    });
    
    setSocket(newSocket);
    
    return newSocket;
  };
  
  // Function to handle the audio captured from the recorder
  const handleAudioCaptured = async (audioBlob: Blob, audioBase64: string) => {
    try {
      setIsProcessing(true);
      setError(null);
      
      // Create form data to submit
      const formData = new FormData();
      formData.append('audio', audioBlob);
      formData.append('sessionId', sessionId);
      
      // Submit audio to be processed
      const response = await fetch('/api/audio', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to process audio');
      }
      
      // Audio is processed by the backend, responses will come through socket.io
      
    } catch (err: any) {
      console.error('Error processing audio:', err);
      setError(err.message || 'An error occurred processing audio');
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Function to play audio
  const playAudio = (audioSrc: string) => {
    if (currentAudio) {
      currentAudio.pause();
    }
    
    const audio = new Audio(audioSrc);
    setCurrentAudio(audio);
    audio.play();
  };
  
  // Function to reset conversation
  const resetConversation = () => {
    if (currentAudio) {
      currentAudio.pause();
      setCurrentAudio(null);
    }
    
    setMessages([]);
    
    // Also reset on backend
    fetch(`/api/chat/clear/${sessionId}`, { method: 'POST' })
      .catch(err => console.error('Error clearing conversation:', err));
  };
  
  // Scroll to bottom when new messages arrive
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  // Submit text message handler
  const submitTextMessage = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    handleSubmit(e);
  };
  
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-4 sm:p-8">
      <div className="w-full max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-8">
          Real-Time Voice Chat
        </h1>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        
        <div className="flex justify-between items-center mb-4 px-2">
          <div className="text-sm flex items-center">
            <span className={`inline-block w-3 h-3 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
            Server: {isConnected ? 'Connected' : 'Disconnected'}
          </div>
          <div className="text-sm flex items-center">
            <span className={`inline-block w-3 h-3 rounded-full mr-2 ${endpointsReady ? 'bg-green-500' : 'bg-yellow-500'}`}></span>
            AI Services: {endpointsReady ? 'Ready' : 'Initializing...'}
          </div>
        </div>
        
        <div className="mb-8 h-[60vh] overflow-y-auto border border-gray-200 rounded-lg">
          <ChatMessages messages={messages} />
          <div ref={messagesEndRef} />
        </div>
        
        <div className="flex flex-col items-center space-y-4">
          {/* Text input form */}
          <form onSubmit={submitTextMessage} className="w-full">
            <div className="flex space-x-2">
              <input
                type="text"
                value={input}
                onChange={handleInputChange}
                placeholder="Type your message..."
                className="flex-1 p-2 border border-gray-300 rounded"
                disabled={isLoading || isProcessing}
              />
              <button
                type="submit"
                disabled={isLoading || isProcessing || !input.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors disabled:bg-gray-400"
              >
                Send
              </button>
            </div>
          </form>
          
          {/* Voice input */}
          <AudioRecorder 
            onAudioCaptured={handleAudioCaptured} 
            isProcessing={isLoading || isProcessing}
          />
          
          <button
            onClick={resetConversation}
            className="mt-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
          >
            Reset Conversation
          </button>
        </div>
      </div>
    </main>
  );
}
