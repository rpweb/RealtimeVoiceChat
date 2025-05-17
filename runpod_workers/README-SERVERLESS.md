# Serverless Real-Time Voice Chat

This project implements a serverless architecture for real-time voice chat using RunPod workers for AI processing. It allows users to have voice conversations with an AI assistant through a web interface.

## Architecture

The system consists of four main components:

1. **Next.js Client Application**: A web interface for recording audio, displaying conversation, and managing the chat experience.

2. **Node.js Backend Server**: A server for session management, tool execution, and RunPod endpoint configuration.

3. **Whisper Worker**: A serverless endpoint running Faster Whisper for speech-to-text transcription.

4. **LLM Worker**: A serverless endpoint running vLLM for language model inference.

5. **TTS Worker**: A serverless endpoint running Piper TTS for text-to-speech synthesis.

![Architecture Diagram](https://i.imgur.com/placeholder-for-diagram.png)

## Components

### 1. Next.js Client Application

The client application is a TypeScript Next.js app with the following features:
- Audio recording and playback
- Interface for chat history display
- Vercel AI SDK integration
- Vercel deployment support
- Dynamic endpoint configuration

### 2. Node.js Backend Server

The backend server is a Node.js app with the following features:
- Session management for multiple users
- Tool execution framework
- Twilio phone call integration
- RunPod API integration for endpoint configuration
- Socket.IO for real-time communication

### 3. Whisper Worker (Speech-to-Text)

- Based on Faster Whisper
- Supports multiple models (tiny, base, small, medium, large)
- Handles audio in both URL and base64 formats
- Provides word-level timestamps (optional)

### 4. LLM Worker (Language Model)

- Based on vLLM for efficient inference
- Supports various open-source models
- Handles different conversation formats
- Configurable generation parameters

### 5. TTS Worker (Text-to-Speech)

- Uses Piper TTS for high-quality voice synthesis
- Includes multiple open-source voices (jenny, lessac)
- Configurable speed and output formats
- Returns audio in base64 format
- No additional API costs

## Deployment

### RunPod Setup

1. Create a RunPod account and obtain an API key
2. Build and push the worker Docker images using GitHub Actions:
   - Whisper Worker: `realtime-voice-whisper`
   - LLM Worker: `realtime-voice-llm`
   - TTS Worker: `realtime-voice-tts`
3. Create serverless endpoints on RunPod using these images
4. Configure your backend server with your RunPod API key

### Backend Deployment

The backend server can be deployed to Railway by following the instructions in the server README.

### Client Deployment

The client application can be deployed to Vercel by following the instructions in the client-app README.

## Cost Analysis

Here's an approximate cost breakdown for using this serverless setup:

### Whisper Worker (Speech-to-Text)
- **GPU**: NVIDIA T4 (4GB)
- **Cost per minute**: $0.0205
- **Average processing time**: ~2-3 seconds per 10-second audio clip
- **Estimated cost per transcription**: $0.0010 - $0.0015

### LLM Worker (Language Model)
- **GPU**: NVIDIA A10G (24GB)
- **Cost per minute**: $0.0484
- **Average processing time**: ~3-5 seconds per response
- **Estimated cost per response**: $0.0024 - $0.0040

### TTS Worker (Text-to-Speech)
- **CPU**: 2 vCPU
- **Cost per minute**: $0.0060
- **Average processing time**: ~1-2 seconds per response
- **Estimated cost per synthesis**: $0.0002 - $0.0003

### Total Cost Per Conversation Turn
- **Combined cost per turn**: $0.0036 - $0.0058
- **Estimated cost for 10-minute conversation (15 turns)**: $0.05 - $0.09

> Note: Costs are approximate and may vary based on actual usage patterns, model selection, and RunPod pricing changes.

## Getting Started

1. Clone this repository
2. Set up the workers on RunPod using the provided Dockerfiles
3. Deploy the backend server to Railway with your RunPod API key
4. Deploy the client application to Vercel with your backend URL

For detailed setup instructions, refer to the individual README files in each component directory.

## Future Improvements

- Add streaming support for more real-time interactions
- Implement caching to reduce costs for repeated queries
- Add support for additional language models and voice options
- Implement user authentication and conversation history storage 