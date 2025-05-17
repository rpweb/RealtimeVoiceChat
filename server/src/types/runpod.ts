export interface RunPodJob {
  id: string;
  status: 'IN_QUEUE' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  output?: any;
}

export interface WhisperRequest {
  audio_base64: string;
  model?: string;
  language?: string;
  word_timestamps?: boolean;
}

export interface LLMRequest {
  messages: {
    role: 'system' | 'user' | 'assistant';
    content: string;
  }[];
  temperature?: number;
  max_tokens?: number;
}

export interface TTSRequest {
  text: string;
  voice?: 'jenny' | 'lessac'; // Piper TTS voices
  format?: 'mp3' | 'wav';
  speed?: number;
}

export interface ApiConfig {
  RUNPOD_WHISPER_ENDPOINT: string;
  RUNPOD_LLM_ENDPOINT: string;
  RUNPOD_TTS_ENDPOINT: string;
} 