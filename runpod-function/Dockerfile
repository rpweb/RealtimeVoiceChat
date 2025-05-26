# Use the official RunPod Python base image with CUDA 12.1.1 support
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    python3-pyaudio \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (though not strictly necessary for serverless)
EXPOSE 8000

# Command to run the handler
CMD ["python", "handler.py"] 