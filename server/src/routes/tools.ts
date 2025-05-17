import { Express, Request, Response } from 'express';
import { SessionManager } from '../services/sessionManager';

export function setupToolRoutes(app: Express, sessionManager: SessionManager) {
  // Get available tools
  app.get('/api/tools', (req: Request, res: Response) => {
    try {
      // Access tool registry through session manager
      const tools = sessionManager['toolRegistry'].getAllTools().map((tool) => ({
        name: tool.name,
        description: tool.description,
        parameters: tool.parameters
      }));
      
      res.status(200).json({ tools });
    } catch (error) {
      console.error('Error retrieving tools:', error);
      res.status(500).json({ error: 'Failed to retrieve tools' });
    }
  });
  
  // Execute a tool
  app.post('/api/tools/:toolName/execute', async (req: Request, res: Response) => {
    try {
      const { toolName } = req.params;
      const { sessionId, parameters } = req.body;
      
      if (!sessionId) {
        return res.status(400).json({ error: 'Session ID is required' });
      }
      
      const session = sessionManager.getSession(sessionId);
      
      if (!session) {
        return res.status(404).json({ error: 'Session not found' });
      }
      
      // Execute the tool
      const result = await sessionManager.executeTool(sessionId, toolName, parameters);
      
      res.status(200).json({ result });
    } catch (error) {
      console.error(`Error executing tool:`, error);
      res.status(500).json({ error: 'Failed to execute tool' });
    }
  });
  
  // Tool result webhook - for asynchronous tool execution
  app.post('/api/tools/webhook/:sessionId', async (req: Request, res: Response) => {
    try {
      const { sessionId } = req.params;
      const { toolName, result } = req.body;
      
      const session = sessionManager.getSession(sessionId);
      
      if (!session) {
        return res.status(404).json({ error: 'Session not found' });
      }
      
      // Update session with tool result
      session.context.lastToolResult = {
        name: toolName,
        result,
        timestamp: new Date()
      };
      
      // Process the tool result as if it were a message
      await sessionManager.processTextInput(
        sessionId,
        `Tool "${toolName}" completed with result: ${result}`
      );
      
      res.status(200).json({ success: true });
    } catch (error) {
      console.error('Error processing tool webhook:', error);
      res.status(500).json({ error: 'Failed to process tool webhook' });
    }
  });
} 