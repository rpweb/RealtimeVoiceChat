import { Socket } from 'socket.io';
import axios from 'axios';
import { Tool, ToolRegistry } from './toolRegistry';
import { RunPodService } from './runpodService';
import { WhisperRequest, LLMRequest, TTSRequest } from '../types/runpod';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

interface Session {
  id: string;
  socket: Socket | null;
  phoneCall?: any; // Twilio call object
  messages: Message[];
  isActive: boolean;
  context: {
    [key: string]: any;
  };
  // For streaming audio processing
  audioBuffer?: {
    chunks: Float32Array[];
    sampleRate: number;
    lastProcessed: number;
    isSpeaking: boolean;
    silenceStart?: number;
  };
}

interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export class SessionManager {
  private sessions: Map<string, Session>;
  private runpod: RunPodService;
  private toolRegistry: ToolRegistry;

  constructor() {
    this.sessions = new Map();
    this.runpod = new RunPodService();
    this.toolRegistry = new ToolRegistry();
    this.initializeTools();
  }

  private initializeTools() {
    // Register available tools
    // These will be accessible to users via voice, chat, or phone
    this.toolRegistry.registerTool({
      name: 'weather',
      description: 'Get current weather information for a location',
      parameters: {
        location: { type: 'string', required: true }
      },
      execute: async (params: any) => {
        // Example implementation
        const { location } = params;
        // In a real implementation, you would call a weather API
        return `The weather in ${location} is sunny and 72°F`;
      }
    });

    // Add more tools as needed...
  }

  public createSession(sessionId: string, socket: Socket | null = null): Session {
    const session: Session = {
      id: sessionId,
      socket,
      messages: [
        {
          role: 'system',
          content: 'You are a helpful assistant that can use various tools. Be concise and helpful.',
          timestamp: new Date()
        }
      ],
      isActive: true,
      context: {}
    };

    this.sessions.set(sessionId, session);
    return session;
  }

  public getSession(sessionId: string): Session | undefined {
    return this.sessions.get(sessionId);
  }

  public endSession(sessionId: string): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.isActive = false;
      // Clean up any resources
    }
  }

  public async processAudioInput(sessionId: string, audioData: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session || !session.isActive) {
      throw new Error('Session not found or inactive');
    }

    try {
      // Step 1: Transcribe audio with Whisper
      const whisperRequest: WhisperRequest = {
        audio_base64: audioData,
        model: 'base.en',
        language: 'en'
      };
      
      const transcription = await this.runpod.transcribeAudio(whisperRequest);
      
      // Step 2: Process the transcribed text
      await this.processTextInput(sessionId, transcription);
      
    } catch (error) {
      console.error('Error processing audio input:', error);
      throw error;
    }
  }

  public async processTextInput(sessionId: string, text: string): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session || !session.isActive) {
      throw new Error('Session not found or inactive');
    }

    try {
      // Add user message to history
      session.messages.push({
        role: 'user',
        content: text,
        timestamp: new Date()
      });

      // Check if the input contains a tool request
      const toolRequest = this.parseToolRequest(text);
      
      let assistantResponse: string;
      
      if (toolRequest) {
        // Execute the tool
        const toolResult = await this.executeTool(sessionId, toolRequest.tool, toolRequest.parameters);
        assistantResponse = `I used the ${toolRequest.tool} tool: ${toolResult}`;
      } else {
        // Process with LLM if no specific tool request was detected
        const llmRequest: LLMRequest = {
          messages: session.messages.map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          temperature: 0.7,
          max_tokens: 512
        };
        
        // Call the LLM through RunPod
        assistantResponse = await this.runpod.generateResponse(llmRequest);
      }
      
      // Add assistant response to history
      session.messages.push({
        role: 'assistant',
        content: assistantResponse,
        timestamp: new Date()
      });
      
      // Synthesize speech if needed
      if (session.socket || session.phoneCall) {
        // First, send the text response immediately
        if (session.socket) {
          session.socket.emit('assistant_response', {
            text: assistantResponse,
            isComplete: false
          });
        }
        
        // Then stream the audio sentence by sentence
        const ttsRequest: TTSRequest = {
          text: assistantResponse,
          voice: 'lessac', // using the model we have
          format: 'mp3'
        };
        
        await this.runpod.streamSpeech(ttsRequest, (audioChunk: string) => {
          // Send each audio chunk as it becomes available
          if (session.socket) {
            session.socket.emit('audio_chunk', {
              audio: audioChunk,
              isLast: false
            });
          }
          
          // If this is a phone call, send audio through Twilio
          if (session.phoneCall) {
            this.sendAudioToTwilioCall(session.phoneCall, audioChunk);
          }
        });
        
        // Send completion signal
        if (session.socket) {
          session.socket.emit('assistant_response', {
            text: assistantResponse,
            isComplete: true
          });
        }
      }
      
    } catch (error) {
      console.error('Error processing text input:', error);
      throw error;
    }
  }

  private parseToolRequest(text: string): { tool: string, parameters: any } | null {
    // Simple parsing for tool requests
    // In a real implementation, you might use a more sophisticated approach or use LLM to parse
    const toolMatch = text.match(/use ([\w]+) tool (?:with|for) (.+)/i);
    if (toolMatch) {
      const toolName = toolMatch[1].toLowerCase();
      const params = toolMatch[2].trim();
      
      // Basic parameter parsing
      // For simplicity, we're just using the remaining text as a single parameter
      return {
        tool: toolName,
        parameters: { input: params }
      };
    }
    
    return null;
  }

  public async executeTool(sessionId: string, toolName: string, parameters: any): Promise<string> {
    const session = this.sessions.get(sessionId);
    if (!session || !session.isActive) {
      throw new Error('Session not found or inactive');
    }

    const tool = this.toolRegistry.getTool(toolName);
    if (!tool) {
      return `Tool '${toolName}' not found. Available tools: ${this.toolRegistry.getToolNames().join(', ')}`;
    }
    
    try {
      // Execute the tool and get result
      const result = await tool.execute(parameters);
      
      // Update session with tool usage
      session.context.lastToolUsed = {
        name: toolName,
        parameters,
        result,
        timestamp: new Date()
      };
      
      return result;
    } catch (error) {
      console.error(`Error executing tool ${toolName}:`, error);
      return `Error executing tool ${toolName}: ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  }

  public async sendAudioToTwilioCall(call: any, audioBase64: string): Promise<void> {
    // Implementation depends on how you're handling Twilio calls
    // This is just a placeholder
    console.log('Sending audio to Twilio call');
  }

  public registerPhoneCall(sessionId: string, call: any): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.phoneCall = call;
    }
  }

  public async processAudioChunk(sessionId: string, chunkData: number[], sampleRate: number): Promise<void> {
    const session = this.sessions.get(sessionId);
    if (!session || !session.isActive) {
      throw new Error('Session not found or inactive');
    }

    try {
      // Initialize audio buffer if it doesn't exist
      if (!session.audioBuffer) {
        session.audioBuffer = {
          chunks: [],
          sampleRate,
          lastProcessed: Date.now(),
          isSpeaking: false
        };
      }

      // Convert incoming number[] to Float32Array
      const float32Chunk = new Float32Array(chunkData);
      
      // Add chunk to buffer
      session.audioBuffer.chunks.push(float32Chunk);
      
      // Detect if speaking (simple energy-based VAD)
      const energy = this.calculateEnergy(float32Chunk);
      const isSpeaking = energy > 0.01; // Adjust threshold as needed
      
      if (isSpeaking && !session.audioBuffer.isSpeaking) {
        // Just started speaking
        session.audioBuffer.isSpeaking = true;
        session.audioBuffer.silenceStart = undefined;
        
        if (session.socket) {
          session.socket.emit('vad_status', { speaking: true });
        }
      } else if (!isSpeaking && session.audioBuffer.isSpeaking) {
        // Just stopped speaking
        if (!session.audioBuffer.silenceStart) {
          session.audioBuffer.silenceStart = Date.now();
        } else if (Date.now() - session.audioBuffer.silenceStart > 1000) {
          // If silence for more than 1 second, process the collected audio
          session.audioBuffer.isSpeaking = false;
          
          if (session.socket) {
            session.socket.emit('vad_status', { speaking: false });
          }
          
          // Process accumulated audio if buffer has content
          if (session.audioBuffer.chunks.length > 0) {
            await this.processAccumulatedAudio(session);
          }
        }
      } else if (!isSpeaking) {
        // Still silence
        session.audioBuffer.silenceStart = session.audioBuffer.silenceStart || Date.now();
      } else {
        // Still speaking
        session.audioBuffer.silenceStart = undefined;
      }
      
      // Process periodically even during continuous speech (every 2 seconds)
      const timeSinceLastProcess = Date.now() - session.audioBuffer.lastProcessed;
      if (session.audioBuffer.isSpeaking && timeSinceLastProcess > 2000 && session.audioBuffer.chunks.length > 20) {
        await this.processAccumulatedAudio(session, false); // Process but don't clear buffer
      }
      
    } catch (error) {
      console.error('Error processing audio chunk:', error);
      throw error;
    }
  }

  private calculateEnergy(audioChunk: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < audioChunk.length; i++) {
      sum += audioChunk[i] * audioChunk[i];
    }
    return sum / audioChunk.length;
  }

  private async processAccumulatedAudio(session: Session, clearBuffer: boolean = true): Promise<void> {
    if (!session.audioBuffer || session.audioBuffer.chunks.length === 0) return;
    
    try {
      // Concatenate all audio chunks
      const totalLength = session.audioBuffer.chunks.reduce((acc, chunk) => acc + chunk.length, 0);
      const combinedAudio = new Float32Array(totalLength);
      
      let offset = 0;
      for (const chunk of session.audioBuffer.chunks) {
        combinedAudio.set(chunk, offset);
        offset += chunk.length;
      }
      
      // Convert to WAV format
      const wavBuffer = this.float32ToWav(combinedAudio, session.audioBuffer.sampleRate);
      
      // Create a temporary WAV file
      const tempFilePath = path.join(os.tmpdir(), `audio_${session.id}_${Date.now()}.wav`);
      fs.writeFileSync(tempFilePath, wavBuffer);
      
      try {
        // Convert to base64 for sending to Whisper
        const base64Audio = wavBuffer.toString('base64');
        
        // Transcribe with Whisper
        const whisperRequest: WhisperRequest = {
          audio_base64: base64Audio,
          language: 'en'
        };
        
        // If the socket exists, send a transcribing status
        if (session.socket) {
          session.socket.emit('transcribing', { inProgress: true });
        }
        
        // Send to Whisper
        const transcription = await this.runpod.transcribeAudio(whisperRequest);
        
        // If the socket exists, send the transcribing done status
        if (session.socket) {
          session.socket.emit('transcribing', { inProgress: false });
        }
        
        // If we got text, process it
        if (transcription && transcription.trim()) {
          await this.processTextInput(session.id, transcription);
        }
        
        // Update last processed time
        session.audioBuffer.lastProcessed = Date.now();
        
        // Clean up
        fs.unlinkSync(tempFilePath);
        
        // Clear audio buffer if requested
        if (clearBuffer) {
          session.audioBuffer.chunks = [];
        } else {
          // Keep the most recent chunks (last second) to maintain context
          const samplesToDrop = Math.floor(session.audioBuffer.sampleRate * 1);
          if (totalLength > samplesToDrop) {
            const newChunk = new Float32Array(combinedAudio.subarray(combinedAudio.length - samplesToDrop));
            session.audioBuffer.chunks = [newChunk];
          }
        }
      } catch (error) {
        console.error('Error processing audio:', error);
        fs.unlinkSync(tempFilePath);
        throw error;
      }
    } catch (error) {
      console.error('Error in processAccumulatedAudio:', error);
      throw error;
    }
  }

  private float32ToWav(samples: Float32Array, sampleRate: number): Buffer {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    // Write WAV header
    // RIFF chunk descriptor
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');

    // FMT sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true); // subchunk1 size
    view.setUint16(20, 1, true); // PCM format
    view.setUint16(22, 1, true); // mono channel
    view.setUint32(24, sampleRate, true); // sample rate
    view.setUint32(28, sampleRate * 2, true); // byte rate
    view.setUint16(32, 2, true); // block align
    view.setUint16(34, 16, true); // bits per sample

    // Data sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // Write audio data
    let index = 44;
    for (let i = 0; i < samples.length; i++) {
      // Convert float to int16
      const s = Math.max(-1, Math.min(1, samples[i]));
      const val = s < 0 ? s * 0x8000 : s * 0x7FFF;
      view.setInt16(index, val, true);
      index += 2;
    }

    // Helper function to write strings
    function writeString(view: DataView, offset: number, string: string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    }

    return Buffer.from(buffer);
  }
} 