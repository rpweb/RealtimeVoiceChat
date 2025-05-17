import { Express, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import twilio from 'twilio';
import { SessionManager } from '../services/sessionManager';

// Initialize Twilio VoiceResponse
const VoiceResponse = twilio.twiml.VoiceResponse;

export function setupTwilioRoutes(app: Express, sessionManager: SessionManager) {
  // Webhook for incoming calls
  app.post('/api/twilio/voice', (req: Request, res: Response) => {
    const twiml = new VoiceResponse();
    
    // Create a new session for this call
    const sessionId = uuidv4();
    sessionManager.createSession(sessionId);
    
    // Use <Gather> to collect user speech
    const gather = twiml.gather({
      input: 'speech',
      speechTimeout: 'auto',
      speechModel: 'phone_call',
      language: 'en-US',
      action: `/api/twilio/collect/${sessionId}`,
      method: 'POST',
    });
    
    gather.say('Hello! I am your AI assistant. How can I help you today?');
    
    // If the user doesn't say anything, loop back
    twiml.redirect('/api/twilio/voice');
    
    res.type('text/xml');
    res.send(twiml.toString());
  });
  
  // Webhook for collected speech from user
  app.post('/api/twilio/collect/:sessionId', async (req: Request, res: Response) => {
    const sessionId = req.params.sessionId;
    const speechResult = req.body.SpeechResult; // The transcribed speech from Twilio
    
    try {
      // Process the user's speech input
      await sessionManager.processTextInput(sessionId, speechResult);
      
      // Get the session to access the response
      const session = sessionManager.getSession(sessionId);
      
      if (!session) {
        throw new Error('Session not found');
      }
      
      // Get the last assistant message
      const lastMessage = session.messages
        .filter(msg => msg.role === 'assistant')
        .pop();
      
      // Create TwiML response
      const twiml = new VoiceResponse();
      
      // Play the response audio or say the text
      if (lastMessage) {
        // Here you'd typically have a URL to an audio file
        // For simplicity, we'll just use say()
        twiml.say(lastMessage.content);
        
        // Continue the conversation
        const gather = twiml.gather({
          input: 'speech',
          speechTimeout: 'auto',
          speechModel: 'phone_call',
          language: 'en-US',
          action: `/api/twilio/collect/${sessionId}`,
          method: 'POST',
        });
        
        gather.say('Is there anything else you would like to know?');
      } else {
        twiml.say('I apologize, but I encountered an issue processing your request.');
        twiml.hangup();
      }
      
      res.type('text/xml');
      res.send(twiml.toString());
    } catch (error) {
      console.error('Error processing Twilio voice input:', error);
      
      const twiml = new VoiceResponse();
      twiml.say('I apologize, but I encountered an error. Please try again later.');
      twiml.hangup();
      
      res.type('text/xml');
      res.send(twiml.toString());
    }
  });
  
  // Endpoint to stream audio from Twilio
  app.post('/api/twilio/stream/:sessionId', (req: Request, res: Response) => {
    // Implementation for streaming audio from Twilio Media Streams
    // This is more advanced and requires Twilio Media Streams API
    res.status(200).send('Streaming endpoint');
  });
} 