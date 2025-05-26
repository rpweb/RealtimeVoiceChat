# RealtimeVoiceChat

A comprehensive real-time voice chat system with AI integration, featuring a distributed architecture for scalable deployment.

## Architecture

This project uses a modern distributed architecture with two main components:

1. **Railway FastAPI Server** (`/server`)
   - Lightweight FastAPI server for web interface
   - WebSocket management for real-time communication
   - Proxy to RunPod serverless function
   - Static file serving for the web UI
   - Health check endpoints for Railway

2. **RunPod Serverless Function** (`/runpod-function`)
   - GPU-accelerated AI processing
   - Speech-to-text using RealtimeSTT
   - Text-to-speech using RealtimeTTS (Coqui/Kokoro/Orpheus)
   - LLM inference with OpenAI/HuggingFace models
   - Session management and conversation history

## Features

- **Real-time Voice Chat**: Seamless voice-to-voice conversation with AI
- **Multi-modal Interaction**: Support for both text and voice input/output
- **GPU-accelerated Processing**: Fast inference using RunPod serverless
- **Session Management**: Multiple concurrent user sessions
- **Cost-effective**: Pay-per-use RunPod serverless + lightweight Railway hosting
- **Scalable Architecture**: Separate compute and web serving layers
- **Modern Tech Stack**: FastAPI, WebSockets, RealtimeSTT/TTS
- **Easy Deployment**: Simple Railway + RunPod deployment

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Docker (for RunPod deployment)
- Railway account
- RunPod account

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/RealtimeVoiceChat.git
   cd RealtimeVoiceChat
   ```

2. Start the Railway server locally:
   ```bash
   cd server
   pip install -r requirements.txt
   python main.py
   ```

3. Open [http://localhost:8000](http://localhost:8000) to access the web interface

### Deployment

See the individual README files:
- [Railway Server Deployment](./server/README.md)
- [RunPod Function Deployment](./runpod-function/README.md)

## Project Structure

```
RealtimeVoiceChat/
├── server/                 # Railway FastAPI server
│   ├── main.py            # Main server application
│   ├── requirements.txt   # Python dependencies
│   ├── railway.toml       # Railway configuration
│   ├── static/            # Web interface files
│   └── README.md          # Server deployment guide
├── runpod-function/       # RunPod serverless function
│   ├── handler.py         # Main function handler
│   ├── requirements.txt   # Python dependencies
│   ├── Dockerfile         # Container configuration
│   ├── *.py              # AI processing modules
│   └── README.md          # Function deployment guide
└── code/                  # Original monolithic code (legacy)
```

## Deployment

### 1. Set up GitHub Secrets

Add these secrets to your GitHub repository for automated deployment:
- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Your Docker Hub access token
- `RAILWAY_TOKEN`: Your Railway API token (optional, for automated Railway deployment)

### 2. Deploy RunPod Function (Automatic)

1. **Push changes** to trigger GitHub Actions:
   ```bash
   git add .
   git commit -m "Deploy RunPod function"
   git push
   ```

2. **GitHub Actions will automatically**:
   - Build the Docker image with CUDA 12.1.1
   - Push to Docker Hub as `yourusername/realtime-voice-chat-runpod:latest`

3. **Create RunPod template**:
   - Use the automatically built image
   - Set container disk size to at least 20GB
   - Choose GPU type (recommended: RTX 4090 or A100)

4. **Deploy as serverless function** and note the endpoint URL

### 3. Deploy Railway Server

1. **Connect your GitHub repository** to Railway
2. **Set environment variables** in Railway dashboard:
   - `RUNPOD_ENDPOINT`: Your RunPod function endpoint URL
   - `RUNPOD_API_KEY`: Your RunPod API key
3. **Deploy** using Railway's automatic detection of `railway.toml`

## Configuration

### Environment Variables

**Railway Server**:
- `RUNPOD_ENDPOINT`: RunPod serverless function endpoint URL
- `RUNPOD_API_KEY`: RunPod API key for authentication
- `PORT`: Server port (automatically set by Railway)

**RunPod Function**:
- `OPENAI_API_KEY`: OpenAI API key (if using OpenAI models)
- `HF_TOKEN`: Hugging Face token (if using HF models)

## Development

See individual README files for detailed instructions:
- [Railway Server](./server/README.md)
- [RunPod Function](./runpod-function/README.md)

## Migration from Original Code

The original monolithic code in the `/code` directory has been split into:
- **Server component**: Lightweight FastAPI proxy server for Railway
- **Function component**: Heavy AI processing for RunPod serverless

This architecture provides:
- **Cost efficiency**: Pay only for GPU usage when processing
- **Scalability**: Automatic scaling on both platforms
- **Simplicity**: Easier deployment and maintenance
