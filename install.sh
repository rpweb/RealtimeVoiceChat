#!/bin/bash

# Navigate to the project directory
cd /workspace/RealtimeVoiceChat

# Update system and install required system packages
echo "Updating system and installing system dependencies..."
apt update
apt install -y git curl libsndfile1 ffmpeg libportaudio2 portaudio19-dev net-tools alsa-utils build-essential wget

# Install cuDNN for CUDA 12.1.1
echo "Installing cuDNN..."
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
dpkg -i cuda-keyring_1.1-1_all.deb
apt update
apt install -y libcudnn9-cuda-12
ldconfig

# Set LD_LIBRARY_PATH for cuDNN
echo "Configuring cuDNN library path..."
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
echo 'export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# Set up a dummy ALSA device to suppress audio warnings
echo "Setting up dummy ALSA device..."
echo "pcm.!default { type plug; slave.pcm \"null\"; }" > ~/.asoundrc

# Make start.sh and stop.sh executable
echo "Making start.sh and stop.sh executable..."
chmod +x start.sh
chmod +x stop.sh

# Create and activate virtual environment
echo "Creating and activating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install deepspeed (required for RealtimeTTS with Coqui TTS)
echo "Installing deepspeed..."
pip install deepspeed

# Verify key dependencies
echo "Verifying installed dependencies..."
pip list | grep -E "RealtimeSTT|RealtimeTTS|fastapi|uvicorn|websockets|ollama|deepspeed"

# Install Ollama
echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server
echo "Starting Ollama server for model pulling..."
export OLLAMA_MODELS=/workspace/ollama_models
ollama serve &
sleep 5  # Wait for Ollama to start

# Verify Ollama is running
if netstat -tulnp 2>/dev/null | grep -q 11434; then
    echo "Ollama server started successfully for model pulling."
else
    echo "Failed to start Ollama server. Cannot pull models."
    exit 1
fi

# Pull a smaller LLM model to reduce latency
echo "Pulling LLM model (gemma2:2b for faster inference)..."
ollama pull gemma2:2b

# Stop Ollama server after pulling
OLLAMA_PID=$(netstat -tulnp 2>/dev/null | grep 11434 | awk '{print $7}' | cut -d'/' -f1)
if [ ! -z "$OLLAMA_PID" ]; then
    echo "Stopping Ollama server (PID: $OLLAMA_PID) after pulling model..."
    kill -9 $OLLAMA_PID
fi

echo "Installation complete. Use start.sh to start the server and stop.sh to stop it."