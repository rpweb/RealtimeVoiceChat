# Realtime Voice Chat - RunPod Serverless Function

This is the RunPod serverless function that handles the heavy AI processing for voice chat.

## Deployment on RunPod

### Automatic Deployment (Recommended)

The Docker image is automatically built and pushed to Docker Hub via GitHub Actions:

1. **Set up GitHub Secrets** in your repository:
   - `DOCKERHUB_USERNAME`: Your Docker Hub username
   - `DOCKERHUB_TOKEN`: Your Docker Hub access token

2. **Push changes** to trigger the build:
   ```bash
   git add .
   git commit -m "Update RunPod function"
   git push
   ```

3. **Create RunPod template**:
   - Use image: `yourusername/realtime-voice-chat-runpod:latest`
   - Set container disk size to at least 20GB
   - Choose GPU type (recommended: RTX 4090 or A100)

4. **Deploy the serverless function** and get the endpoint URL

5. **Configure the Railway server** with the RunPod endpoint

### Manual Deployment

1. **Build locally**:
   ```bash
   export DOCKERHUB_USERNAME=yourusername
   ./build.sh
   docker push yourusername/realtime-voice-chat-runpod:latest
   ```

2. **Create a new template** on RunPod using the pushed image

## Environment Variables

Set these in your RunPod template:
- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI models)
- `HF_TOKEN`: Hugging Face token (if using HF models)

## Function Handler

The main handler processes different message types:
- `audio_data`: Process incoming audio for speech-to-text
- `text_message`: Process text messages and generate responses
- `synthesize_speech`: Convert text to speech
- `ping`: Health check

## Input Format

```json
{
  "input": {
    "message": {
      "type": "text_message",
      "text": "Hello, how are you?"
    },
    "client_id": "client_123"
  }
}
```

## Output Format

```json
{
  "output": {
    "type": "text_response",
    "text": "I'm doing well, thank you!",
    "status": "success"
  }
}
```

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-openai-key"

# Run locally (for testing)
python handler.py
```

## Features

- Speech-to-text processing
- LLM-based conversation  
- Text-to-speech synthesis
- Session management per client
- GPU-accelerated inference
- Optimized container size (~2.9MB smaller after cleanup)

## Architecture

The function is designed to be stateless but maintains session data in memory for the duration of the container lifecycle. Each client gets their own session with conversation history and audio buffers.

## Included Files

**Core Components:**
- `handler.py` - Main RunPod serverless function handler
- `speech_pipeline_manager.py` - Orchestrates AI pipeline
- `audio_in.py` - Audio input processing
- `audio_module.py` - Audio output/TTS processing
- `transcribe.py` - Speech-to-text processing
- `llm_module.py` - Language model inference
- `upsample_overlap.py` - Audio upsampling utilities

**Supporting Modules:**
- `text_similarity.py` - Text similarity calculations
- `text_context.py` - Context management
- `turndetect.py` - Turn detection utilities
- `colors.py` - Console color utilities
- `system_prompt_salesman.txt` - System prompt for the AI
- `en_sample.wav` - English voice sample for TTS

**Removed Files (unused):**
- `server.py` - Original FastAPI server (replaced by Railway server)
- `system_prompt.txt` - Unused system prompt
- `pt_sample.wav`, `de_sample.wav` - Unused language samples
- `reference_audio*.wav/json` - Unused reference audio files
- `logsetup.py` - Unused logging setup 