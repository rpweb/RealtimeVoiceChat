import axios from 'axios';

// Define types for RunPod API
export interface RunPodJob {
  id: string;
  status: 'IN_QUEUE' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  output?: any;
}

// Configuration interface
interface ApiConfig {
  whisperEndpointId: string;
  llmEndpointId: string;
  ttsEndpointId: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://your-railway-server.railway.app';

// Store the current configuration
let currentConfig: ApiConfig = {
  whisperEndpointId: '',
  llmEndpointId: '',
  ttsEndpointId: ''
};

// Function to fetch endpoint configuration
export const fetchEndpointConfig = async (): Promise<ApiConfig> => {
  try {
    // Fetch from our server API endpoint
    const response = await fetch(`${BACKEND_URL}/api/endpoints`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch API configuration');
    }
    
    const data = await response.json();
    
    if (!data.success || !data.endpoints) {
      throw new Error('Invalid endpoint data received');
    }
    
    // Update the current configuration with just the endpoint IDs
    currentConfig = {
      whisperEndpointId: data.endpoints.whisperEndpoint.split('/').pop() || '',
      llmEndpointId: data.endpoints.llmEndpoint.split('/').pop() || '',
      ttsEndpointId: data.endpoints.ttsEndpoint.split('/').pop() || ''
    };
    
    console.log('RunPod endpoints fetched:', currentConfig);
    return currentConfig;
  } catch (error) {
    console.error('Error fetching endpoint configuration:', error);
    return currentConfig;
  }
};

// Helper function to get current endpoint IDs (useful for checking status)
export const getEndpointIds = () => ({
  WHISPER_ENDPOINT_ID: currentConfig.whisperEndpointId,
  LLM_ENDPOINT_ID: currentConfig.llmEndpointId,
  TTS_ENDPOINT_ID: currentConfig.ttsEndpointId
});

// Interfaces for API requests
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

// API functions that call backend proxy endpoints
export const transcribeAudio = async (input: WhisperRequest): Promise<string> => {
  try {
    const response = await axios.post(`${BACKEND_URL}/api/ml/whisper`, { input });
    return response.data.jobId;
  } catch (error) {
    console.error('Error transcribing audio:', error);
    throw error;
  }
};

export const generateResponse = async (input: LLMRequest): Promise<string> => {
  try {
    const response = await axios.post(`${BACKEND_URL}/api/ml/llm`, { input });
    return response.data.jobId;
  } catch (error) {
    console.error('Error generating response:', error);
    throw error;
  }
};

export const synthesizeSpeech = async (input: TTSRequest): Promise<string> => {
  try {
    const response = await axios.post(`${BACKEND_URL}/api/ml/tts`, { input });
    return response.data.jobId;
  } catch (error) {
    console.error('Error synthesizing speech:', error);
    throw error;
  }
};

export const checkJobStatus = async (endpointType: 'whisper' | 'llm' | 'tts', jobId: string): Promise<RunPodJob> => {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/ml/status/${endpointType}/${jobId}`);
    return response.data;
  } catch (error) {
    console.error('Error checking job status:', error);
    throw error;
  }
};

// Poll for job results with timeout
export const pollForResult = async (
  endpointType: 'whisper' | 'llm' | 'tts',
  jobId: string, 
  timeoutMs: number = 60000,
  intervalMs: number = 1000
): Promise<any> => {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const poll = async () => {
      if (Date.now() - startTime > timeoutMs) {
        return reject(new Error('Polling timeout exceeded'));
      }
      
      try {
        const job = await checkJobStatus(endpointType, jobId);
        
        if (job.status === 'COMPLETED') {
          return resolve(job.output);
        } else if (job.status === 'FAILED') {
          return reject(new Error('Job failed'));
        }
        
        // Job still in progress, wait and check again
        setTimeout(poll, intervalMs);
      } catch (error) {
        reject(error);
      }
    };
    
    // Start polling
    poll();
  });
}; 