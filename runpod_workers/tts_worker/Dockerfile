FROM python:3.10-slim

# Set environment variables!
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    git \
    libsndfile1 \
    espeak-ng \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install RunPod first and verify installation
RUN pip install --no-cache-dir runpod==1.6.0 && \
    python -c "import runpod; print(f'RunPod version: {runpod.__version__}')"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Piper TTS model and voice (only lessac model)
RUN mkdir -p /app/models && \
    cd /app/models && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx -O en_US-lessac-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json -O en_US-lessac-medium.onnx.json

# Copy application files
COPY handler.py predict.py schema.py start.py /app/

# Make start script executable
RUN chmod +x /app/start.py

# Expose port for API
EXPOSE 8000

# Set environment variable to force module path recognition
ENV PYTHONPATH=/app

# Use our custom start script
CMD ["python", "/app/start.py"] 