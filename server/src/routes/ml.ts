import { Express } from 'express';
import { SessionManager } from '../services/sessionManager';
import { RunPodService } from '../services/runpodService';

export const setupMLRoutes = (app: Express, sessionManager: SessionManager) => {
  const runpodService = new RunPodService();
  
  // Whisper API proxy
  app.post('/api/ml/whisper', async (req, res) => {
    try {
      const { input } = req.body;
      
      if (!input || !input.audio_base64) {
        return res.status(400).json({
          success: false,
          error: 'Missing required audio input'
        });
      }
      
      const result = await runpodService.callWhisperEndpoint(input);
      
      res.json({
        success: true,
        jobId: result.id
      });
    } catch (error) {
      console.error('Error processing whisper request:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to process audio'
      });
    }
  });
  
  // LLM API proxy
  app.post('/api/ml/llm', async (req, res) => {
    try {
      const { input } = req.body;
      
      if (!input || !input.messages || !Array.isArray(input.messages) || input.messages.length === 0) {
        return res.status(400).json({
          success: false,
          error: 'Missing required message input'
        });
      }
      
      const result = await runpodService.callLLMEndpoint(input);
      
      res.json({
        success: true,
        jobId: result.id
      });
    } catch (error) {
      console.error('Error processing LLM request:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to generate response'
      });
    }
  });
  
  // TTS API proxy
  app.post('/api/ml/tts', async (req, res) => {
    try {
      const { input } = req.body;
      
      if (!input || !input.text) {
        return res.status(400).json({
          success: false,
          error: 'Missing required text input'
        });
      }
      
      const result = await runpodService.callTTSEndpoint(input);
      
      res.json({
        success: true,
        jobId: result.id
      });
    } catch (error) {
      console.error('Error processing TTS request:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to synthesize speech'
      });
    }
  });
  
  // Job status endpoint
  app.get('/api/ml/status/:endpointType/:jobId', async (req, res) => {
    try {
      const { endpointType, jobId } = req.params;
      
      if (!['whisper', 'llm', 'tts'].includes(endpointType)) {
        return res.status(400).json({
          success: false,
          error: 'Invalid endpoint type'
        });
      }
      
      const result = await runpodService.checkJobStatus(endpointType, jobId);
      
      res.json(result);
    } catch (error) {
      console.error('Error checking job status:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to check job status'
      });
    }
  });
}; 