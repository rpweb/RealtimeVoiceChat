import { Socket } from 'socket.io';
import axios from 'axios';
import { Tool, ToolRegistry } from './toolRegistry';
import { RunPodService } from './runpodService';
import { WhisperRequest, LLMRequest, TTSRequest } from '../types/runpod';

interface Session {
  id: string;
  socket: Socket | null;
  phoneCall?: any; // Twilio call object
  messages: Message[];
  isActive: boolean;
  context: {
    [key: string]: any;
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
        const ttsRequest: TTSRequest = {
          text: assistantResponse,
          voice: 'jenny',
          format: 'mp3'
        };
        
        const audioBase64 = await this.runpod.synthesizeSpeech(ttsRequest);
        
        // Send response to client
        if (session.socket) {
          session.socket.emit('assistant_response', {
            text: assistantResponse,
            audio: audioBase64
          });
        }
        
        // If this is a phone call, send audio through Twilio
        if (session.phoneCall) {
          // Implementation depends on how you're handling Twilio calls
          this.sendAudioToTwilioCall(session.phoneCall, audioBase64);
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
} 