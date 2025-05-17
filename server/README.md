# RealtimeVoiceChat - Backend Server

This is the backend server for the RealtimeVoiceChat application. It handles:

- Session management for multiple users
- Integration with RunPod workers for ML tasks
- Twilio integration for phone calls
- Tool execution framework
- Socket.IO for real-time communication
- Dynamic RunPod endpoint configuration
- Secure proxy for ML model API calls

## Setup

1. Install dependencies:
   ```
   pnpm install
   ```

2. Copy the example environment file:
   ```
   cp src/.env.example .env
   ```

3. Configure your environment variables in `.env`

4. Run for development:
   ```
   pnpm dev
   ```

5. Build for production:
   ```
   pnpm build
   ```

6. Run in production:
   ```
   pnpm start
   ```

## Deployment on Railway

### Automated Deployment with GitHub Actions

This project includes a GitHub Actions workflow for automatic deployment to Railway:

1. Create a Railway project and link it to your GitHub repository
2. Get a Railway API token from the Railway dashboard
3. Add the token as a GitHub secret named `RAILWAY_TOKEN`
4. Push to the main branch to trigger deployment
5. The workflow uses `railway.Dockerfile` and `railway.toml` for configuration

### Manual Deployment

You can also deploy manually using the Railway CLI:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Deploy the project
railway up
```

## Environment Variables

- `PORT`: Server port (default: 3001)
- `NODE_ENV`: Environment (development/production)
- `CLIENT_ORIGIN`: URL of your Vercel client app (for CORS)
- `RUNPOD_API_KEY`: Your RunPod API key (used to auto-fetch endpoint IDs)
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `TWILIO_AUTH_TOKEN`: Twilio auth token
- `TWILIO_PHONE_NUMBER`: Twilio phone number

## API Endpoints

### Chat
- `POST /api/chat/session`: Create or retrieve a session
- `POST /api/chat/message`: Send a text message
- `GET /api/chat/messages/:sessionId`: Get message history
- `POST /api/chat/clear/:sessionId`: Clear conversation history
- `POST /api/chat/audio`: Process audio input

### Tools
- `GET /api/tools`: Get available tools
- `POST /api/tools/:toolName/execute`: Execute a tool
- `POST /api/tools/webhook/:sessionId`: Tool result webhook

### RunPod Configuration
- `GET /api/endpoints`: Get RunPod endpoint configuration

### ML Services Proxy
- `POST /api/ml/whisper`: Proxy for Whisper STT service
- `POST /api/ml/llm`: Proxy for LLM inference service
- `POST /api/ml/tts`: Proxy for TTS synthesis service
- `GET /api/ml/status/:endpointType/:jobId`: Check job status

### Twilio
- `POST /api/twilio/voice`: Handle incoming calls
- `POST /api/twilio/collect/:sessionId`: Process speech from user
- `POST /api/twilio/stream/:sessionId`: Stream audio from calls 