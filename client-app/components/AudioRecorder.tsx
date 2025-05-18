'use client';

import React, { useState, useEffect, useRef } from 'react';
import { FaMicrophone, FaStop } from 'react-icons/fa';

interface AudioRecorderProps {
  onAudioChunk: (audioChunk: Float32Array, sampleRate: number) => void;
  isProcessing: boolean;
  socketConnected: boolean;
}

const AudioRecorder: React.FC<AudioRecorderProps> = ({ 
  onAudioChunk, 
  isProcessing,
  socketConnected
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  // Initialize audio context and recorder when recording starts
  const startRecording = async () => {
    try {
      // Get microphone stream
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      // Create audio context
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000 // Use 16kHz for better speech recognition
      });
      audioContextRef.current = audioContext;
      
      // Create microphone source
      const microphone = audioContext.createMediaStreamSource(stream);
      
      // Create script processor for handling audio data
      // Note: ScriptProcessorNode is deprecated but has better browser support than AudioWorkletNode
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      audioProcessorRef.current = processor;
      
      // Process audio data in chunks
      processor.onaudioprocess = (e) => {
        const audioData = e.inputBuffer.getChannelData(0);
        // Clone the data since it's from a buffer that will be reused
        const audioChunk = new Float32Array(audioData);
        onAudioChunk(audioChunk, audioContext.sampleRate);
      };
      
      // Connect the audio graph: microphone -> processor -> destination
      microphone.connect(processor);
      processor.connect(audioContext.destination);
      
      setIsRecording(true);
      
      // Also create a MediaRecorder as a fallback/for preview
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };
  
  // Stop recording and clean up
  const stopRecording = () => {
    if (audioProcessorRef.current && audioContextRef.current) {
      audioProcessorRef.current.disconnect();
      audioContextRef.current.close().catch(console.error);
    }
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    setIsRecording(false);
  };
  
  // Toggle recording state
  const handleRecording = () => {
    if (!isRecording) {
      startRecording();
    } else {
      stopRecording();
    }
  };
  
  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (isRecording) {
        stopRecording();
      }
    };
  }, [isRecording]);
  
  return (
    <div className="flex flex-col items-center space-y-4 w-full max-w-md">
      <div className="flex items-center justify-center">
        <button
          onClick={handleRecording}
          disabled={isProcessing || !socketConnected}
          className={`p-4 rounded-full ${
            isRecording 
              ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
              : 'bg-blue-500 hover:bg-blue-600'
          } text-white transition-colors ${(!socketConnected || isProcessing) ? 'opacity-50' : 'opacity-100'}`}
          title={!socketConnected ? "Waiting for connection..." : isProcessing ? "Processing..." : isRecording ? "Stop recording" : "Start recording"}
        >
          {isRecording ? <FaStop /> : <FaMicrophone />}
        </button>
      </div>

      <div className="text-sm text-gray-500">
        {!socketConnected && 'Waiting for connection...'}
        {socketConnected && isRecording && 'Recording in progress... Speaking is detected in real-time.'}
        {socketConnected && !isRecording && !isProcessing && 'Click to start recording'}
        {isProcessing && 'Processing your speech...'}
      </div>
    </div>
  );
};

export default AudioRecorder; 