import axios from 'axios';
import { WhisperRequest, LLMRequest, TTSRequest, RunPodJob } from '../types/runpod';

export interface EndpointConfig {
  whisperEndpoint: string;
  llmEndpoint: string;
  ttsEndpoint: string;
}

export class RunPodService {
  private apiKey: string;
  private apiBase: string;
  private whisperEndpointId: string;
  private llmEndpointId: string;
  private ttsEndpointId: string;
  
  constructor() {
    this.apiKey = process.env.RUNPOD_API_KEY || '';
    this.apiBase = 'https://api.runpod.ai/v2';
    this.whisperEndpointId = process.env.RUNPOD_WHISPER_ENDPOINT || '';
    this.llmEndpointId = process.env.RUNPOD_LLM_ENDPOINT || '';
    this.ttsEndpointId = process.env.RUNPOD_TTS_ENDPOINT || '';
    
    // Fetch endpoints on startup
    this.fetchEndpoints();
  }
  
  public getEndpointConfig(): EndpointConfig {
    return {
      whisperEndpoint: `${this.apiBase}/${this.whisperEndpointId}`,
      llmEndpoint: `${this.apiBase}/${this.llmEndpointId}`,
      ttsEndpoint: `${this.apiBase}/${this.ttsEndpointId}`
    };
  }
  
  private async fetchEndpoints(): Promise<void> {
    try {
      // Call RunPod API to get current endpoints
      const response = await axios.post('https://api.runpod.io/graphql', {
        query: `
          query {
            myself {
              endpoints {
                id
                name
                status
              }
            }
          }
        `
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        }
      });
      
      const endpoints = response.data.data?.myself?.endpoints || [];
      
      // Update endpoints based on their names
      for (const endpoint of endpoints) {
        if (endpoint.name === 'whisper_worker') {
          this.whisperEndpointId = endpoint.id;
        } else if (endpoint.name === 'llm_worker') {
          this.llmEndpointId = endpoint.id;
        } else if (endpoint.name === 'tts_worker') {
          this.ttsEndpointId = endpoint.id;
        }
      }
      
      console.log('RunPod endpoints initialized:', {
        whisper: this.whisperEndpointId,
        llm: this.llmEndpointId,
        tts: this.ttsEndpointId
      });
      
    } catch (error) {
      console.error('Error fetching RunPod endpoints:', error);
    }
  }
  
  private createClient(endpointId: string) {
    return axios.create({
      baseURL: `${this.apiBase}/${endpointId}`,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      }
    });
  }
  
  // New proxy methods for client-side calls
  public async callWhisperEndpoint(input: WhisperRequest): Promise<{ id: string }> {
    try {
      const client = this.createClient(this.whisperEndpointId);
      const response = await client.post('/run', { input });
      return { id: response.data.id };
    } catch (error) {
      console.error('Error calling Whisper endpoint:', error);
      throw error;
    }
  }
  
  public async callLLMEndpoint(input: LLMRequest): Promise<{ id: string }> {
    try {
      const client = this.createClient(this.llmEndpointId);
      const response = await client.post('/run', { input });
      return { id: response.data.id };
    } catch (error) {
      console.error('Error calling LLM endpoint:', error);
      throw error;
    }
  }
  
  public async callTTSEndpoint(input: TTSRequest): Promise<{ id: string }> {
    try {
      const client = this.createClient(this.ttsEndpointId);
      const response = await client.post('/run', { input });
      return { id: response.data.id };
    } catch (error) {
      console.error('Error calling TTS endpoint:', error);
      throw error;
    }
  }
  
  public async checkJobStatus(endpointType: string, jobId: string): Promise<RunPodJob> {
    try {
      let endpointId: string;
      
      // Map endpoint type to endpoint ID
      switch (endpointType) {
        case 'whisper':
          endpointId = this.whisperEndpointId;
          break;
        case 'llm':
          endpointId = this.llmEndpointId;
          break;
        case 'tts':
          endpointId = this.ttsEndpointId;
          break;
        default:
          throw new Error(`Invalid endpoint type: ${endpointType}`);
      }
      
      const client = this.createClient(endpointId);
      const response = await client.get(`/status/${jobId}`);
      return response.data;
    } catch (error) {
      console.error('Error checking job status:', error);
      throw error;
    }
  }
  
  public async transcribeAudio(input: WhisperRequest): Promise<string> {
    try {
      const client = this.createClient(this.whisperEndpointId);
      const response = await client.post('/run', { input });
      const jobId = response.data.id;
      
      // Poll for result
      const result = await this.pollForResult(this.whisperEndpointId, jobId);
      
      if (!result || !result.transcription) {
        throw new Error('Failed to transcribe audio');
      }
      
      return result.transcription;
    } catch (error) {
      console.error('Error transcribing audio:', error);
      throw error;
    }
  }
  
  public async generateResponse(input: LLMRequest): Promise<string> {
    try {
      const client = this.createClient(this.llmEndpointId);
      const response = await client.post('/run', { input });
      const jobId = response.data.id;
      
      // Poll for result
      const result = await this.pollForResult(this.llmEndpointId, jobId);
      
      if (!result || !result.response) {
        throw new Error('Failed to generate response');
      }
      
      return result.response;
    } catch (error) {
      console.error('Error generating response:', error);
      throw error;
    }
  }
  
  public async synthesizeSpeech(input: TTSRequest): Promise<string> {
    try {
      const client = this.createClient(this.ttsEndpointId);
      const response = await client.post('/run', { input });
      const jobId = response.data.id;
      
      // Poll for result
      const result = await this.pollForResult(this.ttsEndpointId, jobId);
      
      if (!result || !result.audio_base64) {
        throw new Error('Failed to synthesize speech');
      }
      
      return result.audio_base64;
    } catch (error) {
      console.error('Error synthesizing speech:', error);
      throw error;
    }
  }
  
  private async pollForResult(
    endpointId: string, 
    jobId: string, 
    timeoutMs: number = 60000,
    intervalMs: number = 1000
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const poll = async () => {
        if (Date.now() - startTime > timeoutMs) {
          return reject(new Error('Polling timeout exceeded'));
        }
        
        try {
          const job = await this._checkJobStatus(endpointId, jobId);
          
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
  }
  
  // Internal job status checker (used by pollForResult)
  private async _checkJobStatus(endpointId: string, jobId: string): Promise<RunPodJob> {
    try {
      const client = this.createClient(endpointId);
      const response = await client.get(`/status/${jobId}`);
      return response.data;
    } catch (error) {
      console.error('Error checking job status:', error);
      throw error;
    }
  }
} 