import express from 'express';
import http from 'http';
import { Server as SocketIOServer, Socket } from 'socket.io';
import cors from 'cors';
import dotenv from 'dotenv';
import { v4 as uuidv4 } from 'uuid';
import { setupTwilioRoutes } from './routes/twilio';
import { setupChatRoutes } from './routes/chat';
import { setupToolRoutes } from './routes/tools';
import { setupEndpointRoutes } from './routes/endpoints';
import { setupMLRoutes } from './routes/ml';
import { SessionManager } from './services/sessionManager';

// Load environment variables
dotenv.config();

// Initialize Express app
const app = express();
const server = http.createServer(app);

// Configure CORS
app.use(cors({
  origin: process.env.CLIENT_ORIGIN || 'https://your-vercel-app.vercel.app',
  methods: ['GET', 'POST'],
  credentials: true
}));

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Initialize Socket.IO
const io = new SocketIOServer(server, {
  cors: {
    origin: process.env.CLIENT_ORIGIN || 'https://your-vercel-app.vercel.app',
    methods: ['GET', 'POST'],
    credentials: true
  }
});

// Initialize session manager
const sessionManager = new SessionManager();

// Setup routes
setupTwilioRoutes(app, sessionManager);
setupChatRoutes(app, sessionManager);
setupToolRoutes(app, sessionManager);
setupEndpointRoutes(app, sessionManager);
setupMLRoutes(app, sessionManager);

// Socket.IO connection handler
io.on('connection', (socket: Socket) => {
  console.log('Client connected:', socket.id);
  
  // Create a new session for this connection
  const sessionId = uuidv4();
  sessionManager.createSession(sessionId, socket);
  
  // Send session ID to client
  socket.emit('session_created', { sessionId });
  
  // Handle audio stream
  socket.on('audio_data', async (data: string) => {
    try {
      await sessionManager.processAudioInput(sessionId, data);
    } catch (error) {
      console.error('Error processing audio:', error);
      socket.emit('error', { message: 'Error processing audio input' });
    }
  });
  
  // Handle streaming audio chunks
  socket.on('audio_chunk', async (data: { chunk: number[], sampleRate: number, sessionId: string }) => {
    try {
      await sessionManager.processAudioChunk(data.sessionId || sessionId, data.chunk, data.sampleRate);
    } catch (error) {
      console.error('Error processing audio chunk:', error);
      socket.emit('error', { message: 'Error processing audio chunk' });
    }
  });
  
  // Handle text messages
  socket.on('text_message', async (data: { message: string }) => {
    try {
      await sessionManager.processTextInput(sessionId, data.message);
    } catch (error) {
      console.error('Error processing text:', error);
      socket.emit('error', { message: 'Error processing text input' });
    }
  });
  
  // Handle tool execution requests
  socket.on('execute_tool', async (data: { tool: string, parameters: any }) => {
    try {
      await sessionManager.executeTool(sessionId, data.tool, data.parameters);
    } catch (error) {
      console.error('Error executing tool:', error);
      socket.emit('error', { message: 'Error executing tool' });
    }
  });
  
  // Handle disconnection
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    sessionManager.endSession(sessionId);
  });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok' });
});

// Start the server
const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
}); 