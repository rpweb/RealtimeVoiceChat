import { Express } from 'express';
import { SessionManager } from '../services/sessionManager';
import { RunPodService } from '../services/runpodService';

export const setupEndpointRoutes = (app: Express, sessionManager: SessionManager) => {
  const runpodService = new RunPodService();
  
  // Get RunPod endpoints
  app.get('/api/endpoints', (req, res) => {
    try {
      const config = runpodService.getEndpointConfig();
      res.json({
        success: true,
        endpoints: config
      });
    } catch (error) {
      console.error('Error getting endpoints:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to retrieve endpoint configuration'
      });
    }
  });
}; 