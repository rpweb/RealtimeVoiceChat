FROM python:3.10-slim

# Set environment variables
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

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Piper TTS model and voice (only lessac model)
RUN mkdir -p /app/models && \
    cd /app/models && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx -O en_US-lessac-medium.onnx && \
    wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json -O en_US-lessac-medium.onnx.json

# Copy application files
COPY handler.py predict.py /app/
COPY schema.py /app/

# Expose port for API
EXPOSE 8000

# Start the service
CMD ["python", "-m", "runpod.serverless.start"] 