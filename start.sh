#!/bin/bash

# Navigate to the project directory
cd /workspace/RealtimeVoiceChat

# Activate the virtual environment
source venv/bin/activate

# Stop any existing Ollama processes on port 11434
OLLAMA_PID=$(netstat -tulnp 2>/dev/null | grep 11434 | awk '{print $7}' | cut -d'/' -f1)
if [ ! -z "$OLLAMA_PID" ]; then
    echo "Stopping existing Ollama process (PID: $OLLAMA_PID)..."
    kill -9 $OLLAMA_PID
fi

# Stop any existing uvicorn processes on port 8000
UVICORN_PID=$(netstat -tulnp 2>/dev/null | grep 8000 | awk '{print $7}' | cut -d'/' -f1)
if [ ! -z "$UVICORN_PID" ]; then
    echo "Stopping existing uvicorn process (PID: $UVICORN_PID)..."
    kill -9 $UVICORN_PID
fi

# Start Ollama server
echo "Starting Ollama server..."
export OLLAMA_MODELS=/workspace/ollama_models
ollama serve &
sleep 10  # Wait for Ollama to start

# Verify Ollama is running (retry up to 5 times, 5 seconds each)
OLLAMA_STARTED=false
for i in {1..5}; do
    if netstat -tulnp 2>/dev/null | grep -q 11434; then
        echo "Ollama server started successfully."
        OLLAMA_STARTED=true
        break
    fi
    echo "Waiting for Ollama server to start (attempt $i/5)..."
    sleep 5
done

if [ "$OLLAMA_STARTED" != "true" ]; then
    echo "Failed to start Ollama server. Check logs for errors."
    exit 1
fi

# Start uvicorn server
echo "Starting uvicorn server..."
cd code
uvicorn server:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
UVICORN_PID=$!
echo "Uvicorn server started with PID $UVICORN_PID. Waiting for it to bind to port 8000 (this may take several minutes)..."
sleep 180  # Wait 3 minutes for uvicorn to start

# Verify uvicorn is running (retry up to 5 times, 30 seconds each)
UVICORN_STARTED=false
for i in {1..5}; do
    if netstat -tulnp 2>/dev/null | grep -q 8000; then
        echo "Uvicorn server started successfully on http://<pod-ip>:8000 (PID: $UVICORN_PID)"
        UVICORN_STARTED=true
        break
    fi
    echo "Waiting for uvicorn server to start (attempt $i/5, waiting 30 seconds)..."
    sleep 120
done

if [ "$UVICORN_STARTED" != "true" ]; then
    echo "Failed to start uvicorn server after waiting. Check logs in uvicorn.log for errors."
    cat uvicorn.log
    exit 1
fi

echo "RealtimeVoiceChat server is now running."