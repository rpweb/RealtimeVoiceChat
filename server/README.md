# Realtime Voice Chat - Railway Server

This is the Railway server component that acts as a proxy to the RunPod serverless function.

## Deployment on Railway

1. **Connect your GitHub repository** to Railway
2. **Set environment variables** in Railway dashboard:
   - `RUNPOD_ENDPOINT`: Your RunPod serverless function endpoint URL
   - `RUNPOD_API_KEY`: Your RunPod API key
   - `PORT`: Will be automatically set by Railway

3. **Deploy**: Railway will automatically detect the `railway.toml` configuration and deploy

## Environment Variables

- `RUNPOD_ENDPOINT`: The HTTP endpoint of your deployed RunPod function
- `RUNPOD_API_KEY`: Your RunPod API key for authentication
- `PORT`: Server port (automatically set by Railway)

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export RUNPOD_ENDPOINT="your-runpod-endpoint"
export RUNPOD_API_KEY="your-runpod-api-key"

# Run the server
python main.py
```

## API Endpoints

- `GET /`: Serves the main web interface
- `GET /health`: Health check endpoint
- `WebSocket /ws`: WebSocket endpoint for real-time communication
- `GET /favicon.ico`: Serves favicon

## Architecture

The server acts as a lightweight proxy that:
1. Serves the web interface
2. Manages WebSocket connections
3. Forwards requests to the RunPod serverless function
4. Returns responses to connected clients

This architecture allows for:
- Scalable compute on RunPod (GPU-enabled)
- Simple web hosting on Railway
- Cost-effective deployment (pay per use on RunPod) 