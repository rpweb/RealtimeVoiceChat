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

# Pull a smaller LLM model to reduce latency (optional, can be changed to the recommended model)
echo "Pulling LLM model (gemma2:2b for faster inference)..."
export OLLAMA_MODELS=/workspace/ollama_models
ollama pull gemma2:2b

# Update llm_module.py to use the smaller model (optional)
echo "Configuring llm_module.py to use gemma2:2b..."
sed -i 's|model="hf.co/bartowski/huihui-ai_Mistral-Small-24B-Instruct-2501-abliterated-GGUF:Q4_K_M"|model="gemma2:2b"|' code/llm_module.py

echo "Installation complete. Use start.sh to start the server and stop.sh to stop it."