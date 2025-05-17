FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set environment variables!
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install necessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    wget \
    git \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -sf /usr/bin/python3 /usr/bin/python
RUN ln -sf /usr/bin/pip3 /usr/bin/pip

# Set working directory
WORKDIR /app

# Install RunPod first and verify installation
RUN pip install --no-cache-dir runpod==1.6.0 && \
    python -c "import runpod; print(f'RunPod version: {runpod.__version__}')"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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