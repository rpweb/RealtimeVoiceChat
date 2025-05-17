import { Express, Request, Response } from 'express';
import { SessionManager } from '../services/sessionManager';

export function setupChatRoutes(app: Express, sessionManager: SessionManager) {
  // Get active session or create a new one
  app.post('/api/chat/session', (req: Request, res: Response) => {
    try {
      const { sessionId } = req.body;
      
      let session;
      
      if (sessionId && sessionManager.getSession(sessionId)) {
        // Use existing session
        session = sessionManager.getSession(sessionId);
      } else {
        // Create new session
        const newSessionId = req.body.sessionId || `session-${Date.now()}`;
        session = sessionManager.createSession(newSessionId);
      }
      
      res.status(200).json({
        sessionId: session?.id,
        messages: session?.messages.filter(msg => msg.role !== 'system')
      });
    } catch (error) {
      console.error('Error creating/retrieving session:', error);
      res.status(500).json({ error: 'Failed to create or retrieve session' });
    }
  });
  
  // Send a text message
  app.post('/api/chat/message', async (req: Request, res: Response) => {
    try {
      const { sessionId, message } = req.body;
      
      if (!sessionId || !message) {
        return res.status(400).json({ error: 'Session ID and message are required' });
      }
      
      const session = sessionManager.getSession(sessionId);
      
      if (!session) {
        return res.status(404).json({ error: 'Session not found' });
      }
      
      // Process the message
      await sessionManager.processTextInput(sessionId, message);
      
      // Return updated messages
      res.status(200).json({
        messages: session.messages.filter(msg => msg.role !== 'system')
      });
    } catch (error) {
      console.error('Error processing message:', error);
      res.status(500).json({ error: 'Failed to process message' });
    }
  });
  
  // Get message history for a session
  app.get('/api/chat/messages/:sessionId', (req: Request, res: Response) => {
    try {
      const { sessionId } = req.params;
      
      const session = sessionManager.getSession(sessionId);
      
      if (!session) {
        return res.status(404).json({ error: 'Session not found' });
      }
      
      res.status(200).json({
        messages: session.messages.filter(msg => msg.role !== 'system')
      });
    } catch (error) {
      console.error('Error retrieving messages:', error);
      res.status(500).json({ error: 'Failed to retrieve messages' });
    }
  });
  
  // Clear conversation history
  app.post('/api/chat/clear/:sessionId', (req: Request, res: Response) => {
    try {
      const { sessionId } = req.params;
      
      // End the current session
      sessionManager.endSession(sessionId);
      
      // Create a new session with the same ID
      const session = sessionManager.createSession(sessionId);
      
      res.status(200).json({
        sessionId: session.id,
        messages: []
      });
    } catch (error) {
      console.error('Error clearing conversation:', error);
      res.status(500).json({ error: 'Failed to clear conversation' });
    }
  });
} 