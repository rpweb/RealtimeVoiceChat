#!/bin/bash

# Stop Ollama server (port 11434)
OLLAMA_PID=$(netstat -tulnp 2>/dev/null | grep 11434 | awk '{print $7}' | cut -d'/' -f1)
if [ ! -z "$OLLAMA_PID" ]; then
    echo "Stopping Ollama server (PID: $OLLAMA_PID)..."
    kill -9 $OLLAMA_PID
else
    echo "No Ollama server process found on port 11434."
fi

# Stop uvicorn server (port 8000)
UVICORN_PID=$(netstat -tulnp 2>/dev/null | grep 8000 | awk '{print $7}' | cut -d'/' -f1)
if [ ! -z "$UVICORN_PID" ]; then
    echo "Stopping uvicorn server (PID: $UVICORN_PID)..."
    kill -9 $UVICORN_PID
else
    echo "No uvicorn server process found on port 8000."
fi

echo "RealtimeVoiceChat server stopped."