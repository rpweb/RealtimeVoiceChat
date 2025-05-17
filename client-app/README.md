# Real-Time Voice Chat Client

This is a Next.js application that provides a real-time voice chat interface using RunPod serverless workers for speech-to-text, language model inference, and text-to-speech.

## Getting Started

### Prerequisites

- Node.js (18.x or later)
- pnpm package manager
- Backend server running (Railway or local)

### Installation

1. Clone the repository and navigate to the client directory:

```bash
cd client-app
```

2. Install dependencies:

```bash
pnpm install
```

3. Configure environment variables:

   **Option 1: Manual Configuration**
   Create a `.env.local` file in the root directory with:

   ```env
   # Backend URL
   NEXT_PUBLIC_BACKEND_URL=your_backend_url_here
   ```

   **Option 2: Automatic Configuration with Railway**
   If you're using Railway for your backend, you can set up automatic integration:

   1. In your Railway project, go to Settings > Integrations
   2. Add the Vercel integration and connect to your Vercel account
   3. Select your Vercel project (the client app)
   4. Railway will automatically export your backend URL as an environment variable
   5. In your Vercel project settings, map the Railway variable to `NEXT_PUBLIC_BACKEND_URL`

4. Start the development server:

```bash
pnpm dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser.

## RunPod Workers and Endpoints

This application uses three serverless endpoints on RunPod:

### 1. Whisper Worker (Speech-to-Text)
- Creates transcriptions from audio input
- Uses OpenAI's Whisper model

### 2. LLM Worker (Language Model)
- Processes text input and generates responses
- Uses open-source LLMs

### 3. TTS Worker (Text-to-Speech)
- Converts text to natural-sounding speech
- Uses the open-source Piper TTS models

The endpoint IDs are automatically fetched from the backend server, so you don't need to configure them manually. The backend server fetches them directly from RunPod's API using your RunPod API key.

All API calls to RunPod services are made through the backend server, ensuring that:
- API keys are never exposed to the client
- All authentication happens securely on the server
- The client receives only the necessary data to function

## Deploying to Vercel

You can deploy this Next.js application to Vercel with a few simple steps:

1. Push your code to a GitHub repository.
2. Create a new project on Vercel and link it to your repository.
3. Set the environment variables in the Vercel project settings.
4. Deploy the project.

## Features

- Real-time voice recording and playback
- Speech-to-text using Whisper model
- Natural language processing with LLMs
- Text-to-speech synthesis using open-source Piper TTS
- Conversation history display
- Automatic endpoint configuration
- Secure communications with ML models via backend proxy

## Cost Efficiency

This implementation is designed to be cost-efficient:

- **Pay-as-you-go**: RunPod serverless workers only charge for the time they're active
- **No external API costs**: All models run directly on RunPod with no additional API fees
- **Resource optimization**: Each component uses the appropriate hardware (GPU/CPU) for its needs

The estimated cost per conversation turn is approximately $0.004-$0.006, making a 10-minute conversation cost around $0.05-$0.09.
