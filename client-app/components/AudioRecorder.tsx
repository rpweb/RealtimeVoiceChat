'use client';

import React, { useState, useEffect } from 'react';
import { useReactMediaRecorder } from 'react-media-recorder';
import { FaMicrophone, FaStop, FaRedo } from 'react-icons/fa';

interface AudioRecorderProps {
  onAudioCaptured: (audioBlob: Blob, audioBase64: string) => void;
  isProcessing: boolean;
}

const AudioRecorder: React.FC<AudioRecorderProps> = ({ onAudioCaptured, isProcessing }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioURL, setAudioURL] = useState<string | null>(null);

  const {
    status,
    startRecording,
    stopRecording,
    mediaBlobUrl,
    clearBlobUrl
  } = useReactMediaRecorder({
    audio: true,
    blobPropertyBag: {
      type: 'audio/wav'
    }
  });

  // Update audio URL when mediaBlobUrl changes
  useEffect(() => {
    if (mediaBlobUrl) {
      setAudioURL(mediaBlobUrl);
    }
  }, [mediaBlobUrl]);

  // Handle recording state
  const handleRecording = () => {
    if (!isRecording) {
      startRecording();
    } else {
      stopRecording();
    }
    setIsRecording(!isRecording);
  };

  // Handle captured audio
  const handleSendAudio = async () => {
    if (mediaBlobUrl) {
      try {
        // Fetch the audio blob from the media URL
        const response = await fetch(mediaBlobUrl);
        const audioBlob = await response.blob();
        
        // Convert blob to base64
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = () => {
          const base64data = reader.result as string;
          // Extract the base64 content (remove data URL prefix)
          const base64Audio = base64data.split(',')[1];
          
          // Send to parent component
          onAudioCaptured(audioBlob, base64Audio);
        };
      } catch (error) {
        console.error('Error processing audio:', error);
      }
    }
  };

  // Reset the recorder
  const handleReset = () => {
    clearBlobUrl();
    setAudioURL(null);
    setIsRecording(false);
  };

  return (
    <div className="flex flex-col items-center space-y-4 w-full max-w-md">
      <div className="flex items-center space-x-4">
        <button
          onClick={handleRecording}
          disabled={isProcessing}
          className={`p-4 rounded-full ${
            isRecording 
              ? 'bg-red-500 hover:bg-red-600' 
              : 'bg-blue-500 hover:bg-blue-600'
          } text-white transition-colors`}
        >
          {isRecording ? <FaStop /> : <FaMicrophone />}
        </button>

        {audioURL && !isRecording && (
          <>
            <button
              onClick={handleSendAudio}
              disabled={isProcessing}
              className="p-4 rounded-full bg-green-500 hover:bg-green-600 text-white transition-colors"
            >
              Submit
            </button>
            <button
              onClick={handleReset}
              disabled={isProcessing}
              className="p-4 rounded-full bg-gray-500 hover:bg-gray-600 text-white transition-colors"
            >
              <FaRedo />
            </button>
          </>
        )}
      </div>

      {audioURL && (
        <div className="w-full">
          <audio src={audioURL} controls className="w-full" />
        </div>
      )}

      <div className="text-sm text-gray-500">
        {status === 'recording' && 'Recording in progress...'}
        {status === 'stopped' && 'Recording stopped. Submit or re-record.'}
        {isProcessing && 'Processing your audio...'}
      </div>
    </div>
  );
};

export default AudioRecorder; 