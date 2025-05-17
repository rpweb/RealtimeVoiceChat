# RealtimeVoiceChat

A comprehensive real-time voice chat system with AI, phone call integration, and tool capabilities.

## Architecture

This project uses a modern distributed architecture with three main components:

1. **Vercel Next.js Frontend**
   - Simple, responsive web interface
   - Vercel AI SDK for streaming responses
   - Socket.IO for real-time updates
   - Supports both text and voice input/output

2. **Railway Node.js Backend**
   - Handles session management
   - Orchestrates tool usage
   - Integrates with Twilio for phone calls
   - Socket.IO server for real-time communication
   - Provides RunPod endpoints configuration
   - Securely proxies ML model API calls

3. **RunPod ML Workers**
   - Whisper Worker: Speech-to-text using Faster Whisper
   - LLM Worker: Language model inference using vLLM
   - TTS Worker: Text-to-speech using Piper TTS

## Features

- **Multi-modal Interaction**: Chat with the AI via text, voice, or phone call
- **Real-time Streaming**: Get responses as they're generated
- **Tool Framework**: Extend functionality with custom tools
- **Session Management**: Support multiple users and conversations
- **Phone Integration**: Call the AI using regular phone calls via Twilio
- **Cost-effective**: Uses open-source ML models on RunPod serverless
- **Dynamic ML Endpoints**: Auto-fetches RunPod endpoints configuration
- **Secure Design**: RunPod API keys are never exposed to the client
- **Automated Deployment**: CI/CD for both Railway backend and RunPod workers

## Quick Start

### Prerequisites

- Node.js 18 or higher
- pnpm 8 or higher

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/RealtimeVoiceChat.git
   cd RealtimeVoiceChat
   ```

2. Run the initialization script:
   ```bash
   ./init.sh
   ```

3. Start the development servers:
   ```bash
   pnpm dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) to access the client app

## Development with pnpm Workspaces

This project uses pnpm workspaces to manage multiple packages:

```bash
# Install all dependencies
pnpm install

# Run only the client
pnpm dev:client

# Run only the server
pnpm dev:server

# Run both client and server
pnpm dev

# Build all packages
pnpm build

# Build specific packages
pnpm build:client
pnpm build:server
```

## Deployment

### RunPod Workers

The ML workers are deployed automatically to RunPod Serverless via GitHub Actions:

1. Build Docker images for each worker
2. Push to Docker Hub
3. Deploy to RunPod Serverless

### Railway Backend (Automated)

The backend server is deployed automatically to Railway via GitHub Actions:

1. Set up a Railway project and get an API token
2. Add the token as a GitHub secret: `RAILWAY_TOKEN`
3. Push to the main branch to trigger deployment
4. The workflow uses the `railway.Dockerfile` and `railway.toml` configuration

Manual deployment is also possible:
```bash
railway login
railway link # Link to your project
railway up   # Deploy the project
```

### Vercel Frontend

The client application is deployed on Vercel:

1. Push to the Vercel GitHub integration
2. Set environment variables in Vercel dashboard
3. Deploy

#### Automatic Backend URL Configuration

To automatically make your Railway backend URL available to your Vercel frontend:

1. In your Railway project, go to Settings > Integrations
2. Add the Vercel integration and connect to your Vercel account
3. Select your Vercel project (the client app)
4. Railway will automatically export your backend URL as an environment variable
5. In your Vercel project settings, map the Railway variable to `NEXT_PUBLIC_BACKEND_URL`

This eliminates the need to manually configure the backend URL in Vercel.

## Configuration

### Environment Variables

**Vercel Frontend**:
- `NEXT_PUBLIC_BACKEND_URL`: URL of the Railway backend server

**Railway Backend**:
- `RUNPOD_API_KEY`: RunPod API key (securely stored on the server only)
- `CLIENT_ORIGIN`: URL of your Vercel app (for CORS)
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `TWILIO_AUTH_TOKEN`: Twilio auth token
- `TWILIO_PHONE_NUMBER`: Twilio phone number

### GitHub Secrets for CI/CD

- `RAILWAY_TOKEN`: Railway API token for automated deployment
- `RUNPOD_API_KEY`: RunPod API key for deploying serverless workers
- `DOCKERHUB_USERNAME`: Docker Hub username for pushing images
- `DOCKERHUB_TOKEN`: Docker Hub token for authentication

## Development

This project uses pnpm as the package manager. See individual README files in each component directory:
- [Client App](./client-app/README.md)
- [Server](./server/README.md)
- [RunPod Workers](./runpod_workers/README.md)
